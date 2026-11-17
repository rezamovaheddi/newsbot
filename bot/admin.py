"""Admin panel: phone authentication, custom news CRUD, users list, view stats."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import ContextTypes

from . import keyboards, texts
from .catalog import Catalog
from .config import Settings
from .db import Database
from .digest import send_single_custom
from .utils import normalize_phone

logger = logging.getLogger(__name__)

NEWS_PAGE = 5
USERS_PAGE = 5


class AdminPanel:
    def __init__(self, settings: Settings, catalog: Catalog, db: Database) -> None:
        self.settings = settings
        self.catalog = catalog
        self.db = db

    # ── access ───────────────────────────────────────────
    async def is_admin(self, user_id: int) -> bool:
        return user_id in self.settings.admin_ids or await self.db.is_admin(user_id)

    def _phone_allowed(self, phone: str) -> bool:
        return not self.settings.admin_phones or phone in self.settings.admin_phones

    # ── entry & auth ─────────────────────────────────────
    async def entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        uid = update.effective_user.id
        if await self.is_admin(uid):
            await self.show_panel(update.effective_chat.id, context)
            return
        context.user_data["admin_auth_pending"] = True
        await update.effective_message.reply_text(texts.ADMIN_ASK_CONTACT, reply_markup=keyboards.contact_reply())

    async def handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if not context.user_data.get("admin_auth_pending"):
            return False
        context.user_data.pop("admin_auth_pending", None)
        message = update.effective_message
        contact = message.contact
        tg_user = update.effective_user
        if not contact or contact.user_id != tg_user.id:
            await message.reply_text(texts.CONTACT_REJECT, reply_markup=keyboards.main_reply())
            return True
        try:
            phone = normalize_phone(contact.phone_number)
        except ValueError:
            await message.reply_text(texts.CONTACT_REJECT, reply_markup=keyboards.main_reply())
            return True
        if not self._phone_allowed(phone):
            await message.reply_text(texts.ADMIN_DENIED, reply_markup=keyboards.main_reply())
            return True
        await self.db.add_admin(tg_user.id, phone)
        await message.reply_text(texts.ADMIN_GRANTED, reply_markup=keyboards.main_reply())
        await self.show_panel(tg_user.id, context)
        return True

    async def show_panel(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        web_url = getattr(self.settings, "web_admin_url", "http://localhost:8000")
        msg = (
            f"🛠 **پنل مدیریت ربات**\n\n"
            f"🌐 **آدرس پنل تحت وب:**\n`{web_url}`\n\n"
            f"💡 می‌توانید لینک بالا را در مرورگر سیستم خود باز کنید."
        )
        await context.bot.send_message(
            chat_id, 
            msg, 
            reply_markup=keyboards.admin_panel_inline(web_url=web_url),
            parse_mode="Markdown"
        )

    # ── add-news text flow ───────────────────────────────
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        flow = context.user_data.get("admin_flow")
        if not flow:
            return False
        uid = update.effective_user.id
        if not await self.is_admin(uid):
            context.user_data.pop("admin_flow", None)
            return False
        text = (update.effective_message.text or "").strip()
        if text in {"لغو", "❌ لغو", texts.BTN_CANCEL}:
            context.user_data.pop("admin_flow", None)
            await update.effective_message.reply_text(texts.ADMIN_FLOW_CANCELLED, reply_markup=keyboards.main_reply())
            return True
        main_buttons = {
            texts.BTN_NEWS, texts.BTN_TIMES, texts.BTN_SETTINGS,
            texts.BTN_ACCOUNT, texts.BTN_ADMIN, texts.BTN_CONTACT,
        }
        if text in main_buttons:
            context.user_data.pop("admin_flow", None)
            return False
        step = flow.get("step")
        if step == "category":
            await update.effective_message.reply_text(
                texts.ADMIN_ADD_CATEGORY, reply_markup=keyboards.admin_category_inline(self.catalog)
            )
            return True
        if step == "title":
            if not text:
                return True
            flow["title"] = text[:200]
            flow["step"] = "body"
            await update.effective_message.reply_text(texts.ADMIN_ADD_BODY, reply_markup=self._cancel_inline())
            return True
        if step == "body":
            flow["body"] = text[:3500]
            flow["step"] = "link"
            await update.effective_message.reply_text(texts.ADMIN_ADD_LINK, reply_markup=keyboards.admin_skip_link_inline())
            return True
        if step == "link":
            flow["link"] = text if text.startswith(("http://", "https://")) else ""
            flow["step"] = "category"
            await update.effective_message.reply_text(
                texts.ADMIN_ADD_CATEGORY, reply_markup=keyboards.admin_category_inline(self.catalog)
            )
            return True
        return True

    @staticmethod
    def _cancel_inline() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لغو", callback_data="adm:add:cancel")]])

    # ── callbacks ────────────────────────────────────────
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        query = update.callback_query
        data = query.data or ""
        if not data.startswith("adm:"):
            return False
        uid = query.from_user.id
        if not await self.is_admin(uid):
            await query.answer(texts.ADMIN_REQUIRED, show_alert=True)
            return True
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""

        if action == "panel":
            await query.answer()
            await self._edit(query, texts.ADMIN_PANEL_TITLE, keyboards.admin_panel_inline())
            return True

        if action == "add" and len(parts) == 2:
            await query.answer()
            context.user_data["admin_flow"] = {"step": "title"}
            await self._edit(query, texts.ADMIN_ADD_TITLE, self._cancel_inline())
            return True

        if action == "add" and len(parts) > 2 and parts[2] == "nolink":
            await query.answer()
            flow = context.user_data.get("admin_flow") or {}
            flow["link"] = ""
            flow["step"] = "category"
            context.user_data["admin_flow"] = flow
            await self._edit(query, texts.ADMIN_ADD_CATEGORY, keyboards.admin_category_inline(self.catalog))
            return True

        if action == "add" and len(parts) > 2 and parts[2] == "cancel":
            await query.answer()
            context.user_data.pop("admin_flow", None)
            await self._edit(query, texts.ADMIN_ADD_CANCELLED, keyboards.admin_panel_inline())
            return True

        if action == "add" and len(parts) > 3 and parts[2] == "cat":
            await query.answer()
            flow = context.user_data.get("admin_flow") or {}
            category = parts[3]
            if category not in self.catalog.by_id:
                category = "general"
            news_id = await self.db.add_news(
                title=flow.get("title", "بدون عنوان"),
                body=flow.get("body", ""),
                link=flow.get("link", ""),
                category=category,
                created_by=uid,
            )
            context.user_data.pop("admin_flow", None)
            await self._edit(
                query,
                texts.ADMIN_ADD_SAVED.format(id=news_id),
                keyboards.admin_news_detail_inline(news_id, 0),
            )
            return True

        if action == "news":
            await query.answer()
            page = self._page(parts, 2)
            await self._show_news_list(query, page)
            return True

        if action == "nv":
            await query.answer()
            news_id = self._int(parts, 2)
            page = self._page(parts, 3)
            item = await self.db.get_news(news_id)
            if not item:
                await self._edit(query, texts.ADMIN_NO_NEWS, keyboards.admin_panel_inline())
                return True
            views = await self.db.view_count(news_id)
            await self._edit(query, texts.admin_news_detail_panel(item, views), keyboards.admin_news_detail_inline(news_id, page))
            return True

        if action == "nd":
            await query.answer()
            news_id = self._int(parts, 2)
            page = self._page(parts, 3)
            await self._edit(query, texts.ADMIN_DELETE_CONFIRM.format(id=news_id), keyboards.admin_news_delete_inline(news_id, page))
            return True

        if action == "ndy":
            await query.answer()
            news_id = self._int(parts, 2)
            page = self._page(parts, 3)
            await self.db.delete_news(news_id)
            await self._show_news_list(query, page)
            return True

        if action == "bc":
            await query.answer()
            news_id = self._int(parts, 2)
            page = self._page(parts, 3)
            markup = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📣 بله، ارسال شود", callback_data=f"adm:bcy:{news_id}:{page}")],
                    [InlineKeyboardButton("خیر", callback_data=f"adm:nv:{news_id}:{page}")],
                ]
            )
            await self._edit(query, f"📣 خبر #{news_id} برای همه کاربران ارسال شود؟", markup)
            return True

        if action == "bcy":
            await query.answer("در حال ارسال…")
            news_id = self._int(parts, 2)
            page = self._page(parts, 3)
            sent, failed = await self.broadcast(news_id, context)
            await self._edit(
                query,
                f"📣 ارسال همگانی انجام شد.\n✅ موفق: {sent}\n⚠️ ناموفق: {failed}",
                keyboards.admin_news_detail_inline(news_id, page),
            )
            return True

        if action == "users":
            await query.answer()
            page = self._page(parts, 2)
            await self._show_users(query, page)
            return True

        if action == "stats":
            await query.answer()
            stats = await self.db.stats()
            news_count = await self.db.count_news()
            total_views = await self.db.total_views()
            top = await self.db.top_news(5)
            await self._edit(query, texts.admin_stats_panel(stats, news_count, total_views, top), keyboards.admin_stats_inline())
            return True

        if action == "logout":
            await query.answer()
            await self.db.remove_admin(uid)
            await self._edit(query, texts.ADMIN_LOGOUT)
            await context.bot.send_message(uid, texts.UNKNOWN_TEXT, reply_markup=keyboards.main_reply())
            return True

        await query.answer()
        return True

    # ── broadcast ────────────────────────────────────────
    async def broadcast(self, news_id: int, context: ContextTypes.DEFAULT_TYPE) -> tuple[int, int]:
        item = await self.db.get_news(news_id)
        if not item:
            return 0, 0
        sent = failed = 0
        for user in await self.db.all_users():
            uid = user["user_id"]
            try:
                await send_single_custom(context.bot, uid, item, self.settings)
                await self.db.record_view(news_id, uid)
                sent += 1
            except RetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 1)
                try:
                    await send_single_custom(context.bot, uid, item, self.settings)
                    await self.db.record_view(news_id, uid)
                    sent += 1
                except TelegramError:
                    failed += 1
            except Forbidden:
                await self.db.set_notifications(uid, False)
                failed += 1
            except TelegramError:
                failed += 1
            await asyncio.sleep(0.04)
        return sent, failed

    # ── helpers ──────────────────────────────────────────
    async def _show_news_list(self, query, page: int) -> None:
        total = await self.db.count_news()
        items = await self.db.news_page(page * NEWS_PAGE, NEWS_PAGE)
        has_next = (page + 1) * NEWS_PAGE < total
        await self._edit(query, texts.admin_news_list_panel(items, page, total), keyboards.admin_news_list_inline(items, page, has_next))

    async def _show_users(self, query, page: int) -> None:
        stats = await self.db.stats()
        total = stats["total"]
        users = await self.db.users_page(page * USERS_PAGE, USERS_PAGE)
        has_next = (page + 1) * USERS_PAGE < total
        await self._edit(query, texts.admin_users_panel(users, page, total), keyboards.admin_users_inline(page, has_next))

    @staticmethod
    def _int(parts: list[str], index: int) -> int:
        try:
            return int(parts[index])
        except (IndexError, ValueError):
            return 0

    @staticmethod
    def _page(parts: list[str], index: int) -> int:
        try:
            return max(0, int(parts[index]))
        except (IndexError, ValueError):
            return 0

    async def _edit(self, query, text: str, markup=None) -> None:
        from telegram.error import BadRequest

        try:
            await query.edit_message_text(text, reply_markup=markup)
        except BadRequest as exc:
            if "not modified" in str(exc).lower():
                return
            try:
                await query.message.reply_text(text, reply_markup=markup)
            except Exception:  # noqa: BLE001
                logger.exception("admin edit fallback failed")
