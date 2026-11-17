"""Telegram update handlers."""
from __future__ import annotations

import logging
import time
from typing import Any

from telegram import BotCommand, Update
from telegram.error import BadRequest, Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import keyboards, texts
from .admin import AdminPanel
from .catalog import Catalog
from .config import Settings
from .db import Database, is_unique_phone_error
from .digest import _user_selection, build_digest, send_chunks, send_custom_news, send_single_custom
from .news import NewsAggregator
from .utils import mask_phone, normalize_phone

logger = logging.getLogger(__name__)
NEWS_COOLDOWN_SECONDS = 20


class BotHandlers:
    def __init__(self, settings: Settings, catalog: Catalog, db: Database, aggregator: NewsAggregator) -> None:
        self.settings = settings
        self.catalog = catalog
        self.db = db
        self.aggregator = aggregator
        self.admin = AdminPanel(settings, catalog, db)

    # ── lifecycle ────────────────────────────────────────
    async def post_init(self, app: Application) -> None:
        await self.db.init()
        await app.bot.set_my_commands(
            [
                BotCommand("start", "شروع و منوی اصلی"),
                BotCommand("register", "ثبت‌نام و احراز هویت"),
                BotCommand("news", "دریافت آخرین اخبار"),
                BotCommand("times", "زمان‌بندی ارسال اخبار"),
                BotCommand("settings", "تنظیمات کاربری"),
                BotCommand("account", "اطلاعات حساب کاربری"),
                BotCommand("privacy", "حریم خصوصی"),
                BotCommand("admin", "پنل ادمین"),
                BotCommand("help", "راهنما"),
            ]
        )
        try:
            await app.bot.set_my_short_description("دریافت هوشمند اخبار فارسی 🗞")
            await app.bot.set_my_description(
                "ربات اخبار هوشمند: دریافت آخرین اخبار فارسی به‌صورت خلاصه هوشمند یا با توضیحات، "
                "دسته‌بندی‌شده و زمان‌بندی‌شده. برای شروع /start را بزنید."
            )
        except Exception:  # noqa: BLE001
            logger.warning("could not set bot description")

    def register(self, app: Application) -> None:
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_cmd))
        app.add_handler(CommandHandler("privacy", self.privacy_cmd))
        app.add_handler(CommandHandler("register", self.register_cmd))
        app.add_handler(CommandHandler("news", self.latest_news))
        app.add_handler(CommandHandler("times", self.show_times))
        app.add_handler(CommandHandler("settings", self.show_settings))
        app.add_handler(CommandHandler("account", self.account_info))
        app.add_handler(CommandHandler("stats", self.stats_cmd))
        app.add_handler(CommandHandler("admin", self.admin_entry))
        app.add_handler(CommandHandler("ping", self.ping))
        app.add_handler(CallbackQueryHandler(self.on_callback))
        app.add_handler(MessageHandler(filters.CONTACT, self.on_contact))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))
        app.add_error_handler(self.on_error)

    # ── helpers ──────────────────────────────────────────
    async def _require_user(self, update: Update) -> dict[str, Any] | None:
        user = await self.db.get_user(update.effective_user.id)
        if not user:
            await update.effective_message.reply_text(
                texts.AUTH_REQUIRED, reply_markup=keyboards.home_inline(False)
            )
        return user

    async def _edit(self, query, text: str, markup=None) -> None:
        try:
            await query.edit_message_text(text, reply_markup=markup)
        except BadRequest as exc:
            if "not modified" in str(exc).lower():
                return
            try:
                await query.message.reply_text(text, reply_markup=markup)
            except Exception:  # noqa: BLE001
                logger.exception("edit fallback failed")

    # ── commands / panels ────────────────────────────────
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        tg_user = update.effective_user
        user = await self.db.get_user(tg_user.id)
        if user:
            await self.db.touch_profile(tg_user.id, tg_user.first_name or "", tg_user.username or "")
            welcome = texts.welcome_back(tg_user.first_name or "")
        else:
            welcome = texts.WELCOME
        await update.effective_message.reply_text(welcome, reply_markup=keyboards.main_reply())
        user = await self.db.get_user(tg_user.id)
        await update.effective_message.reply_text(
            texts.settings_panel(user, self.settings, self.catalog),
            reply_markup=keyboards.home_inline(bool(user)),
        )

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(texts.HELP, reply_markup=keyboards.main_reply())

    async def privacy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(texts.PRIVACY, reply_markup=keyboards.main_reply())

    async def ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text("🏓 ربات فعال است.")

    async def register_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.db.get_user(update.effective_user.id)
        if user:
            await update.effective_message.reply_text(texts.ALREADY_REGISTERED, reply_markup=keyboards.main_reply())
            return
        await update.effective_message.reply_text(texts.ASK_CONTACT, reply_markup=keyboards.contact_reply())

    async def on_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        contact = message.contact
        tg_user = update.effective_user
        if not contact:
            return
        if await self.admin.handle_contact(update, context):
            return
        if contact.user_id != tg_user.id:
            await message.reply_text(texts.CONTACT_REJECT, reply_markup=keyboards.main_reply())
            return
        try:
            phone = normalize_phone(contact.phone_number)
        except ValueError:
            await message.reply_text(texts.CONTACT_REJECT, reply_markup=keyboards.main_reply())
            return
        owner = await self.db.phone_owner(phone)
        if owner and owner != tg_user.id:
            await message.reply_text(texts.PHONE_TAKEN, reply_markup=keyboards.main_reply())
            return
        try:
            await self.db.register(tg_user.id, phone, tg_user.first_name or "", tg_user.username or "")
        except Exception as exc:  # noqa: BLE001
            if is_unique_phone_error(exc):
                await message.reply_text(texts.PHONE_TAKEN, reply_markup=keyboards.main_reply())
                return
            raise
        await message.reply_text(
            texts.REGISTER_SUCCESS.format(phone=mask_phone(phone)), reply_markup=keyboards.main_reply()
        )
        user = await self.db.get_user(tg_user.id)
        await message.reply_text(
            texts.settings_panel(user, self.settings, self.catalog),
            reply_markup=keyboards.home_inline(True),
        )

    async def latest_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self._require_user(update)
        if not user:
            return
        now = time.monotonic()
        last = context.user_data.get("last_news", 0)
        if now - last < NEWS_COOLDOWN_SECONDS:
            await update.effective_message.reply_text(texts.COOLDOWN)
            return
        context.user_data["last_news"] = now
        loading = await update.effective_message.reply_text(texts.LOADING_NEWS)
        try:
            custom_count = await send_custom_news(
                context.bot, update.effective_chat.id, self.db, self.settings, self.catalog, user
            )
            chunks = await build_digest(user, self.settings, self.catalog, self.aggregator)
        except Exception:  # noqa: BLE001
            logger.exception("news build failed")
            await loading.edit_text(texts.ERROR)
            return
        try:
            await loading.delete()
        except Exception:  # noqa: BLE001
            pass
        if chunks == [texts.NO_NEWS] and custom_count:
            return
        await send_chunks(context.bot, update.effective_chat.id, chunks)

    async def show_times(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.db.get_user(update.effective_user.id)
        await update.effective_message.reply_text(texts.schedule_panel(self.settings, user))

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.db.get_user(update.effective_user.id)
        await update.effective_message.reply_text(
            texts.settings_panel(user, self.settings, self.catalog),
            reply_markup=keyboards.settings_inline(user),
        )

    async def account_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self._require_user(update)
        if not user:
            return
        await update.effective_message.reply_text(
            texts.account_panel(user, self.settings, self.catalog),
            reply_markup=keyboards.account_inline(),
        )

    async def stats_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self.admin.is_admin(update.effective_user.id):
            await update.effective_message.reply_text(texts.NOT_ADMIN)
            return
        await update.effective_message.reply_text(texts.stats_panel(await self.db.stats()))

    async def admin_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.admin.entry(update, context)

    async def start_contact_us(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.db.get_user(update.effective_user.id)
        if not user:
            context.user_data["contact_us_flow"] = {"step": "name"}
            await update.effective_message.reply_text(
                "📞 **ارتباط با ما**\n\nلطفاً **نام و نام خانوادگی** خود را ارسال کنید:\n(برای انصراف «🔙 بازگشت» را ارسال کنید)",
                parse_mode="Markdown"
            )
        else:
            name = f"{user.get('first_name', '')}".strip() or update.effective_user.full_name
            context.user_data["contact_us_flow"] = {
                "step": "message",
                "name": name,
                "phone": user.get("phone", "")
            }
            await update.effective_message.reply_text(
                f"📞 **ارتباط با ما**\n\nکاربر گرامی **{name}**، لطفاً پیام، انتقاد یا پیشنهاد خود را ارسال کنید:\n(برای انصراف «🔙 بازگشت» را ارسال کنید)",
                parse_mode="Markdown"
            )

    async def handle_contact_us_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        flow = context.user_data.get("contact_us_flow")
        if not flow:
            return False
        text = (update.effective_message.text or "").strip()
        if text in {texts.BTN_CANCEL, "لغو", "انصراف"}:
            context.user_data.pop("contact_us_flow", None)
            await update.effective_message.reply_text("ارتباط با ما لغو شد.", reply_markup=keyboards.main_reply())
            return True
        main_buttons = {
            texts.BTN_NEWS, texts.BTN_TIMES, texts.BTN_SETTINGS,
            texts.BTN_ACCOUNT, texts.BTN_ADMIN, texts.BTN_CONTACT, texts.BTN_CONTACT_US
        }
        if text in main_buttons:
            context.user_data.pop("contact_us_flow", None)
            return False

        step = flow.get("step")
        if step == "name":
            flow["name"] = text
            flow["step"] = "message"
            await update.effective_message.reply_text(
                f"متشکرم **{text}** عزیز.\nحالا لطفاً پیام خود را بنویسید و ارسال کنید:",
                parse_mode="Markdown"
            )
            return True

        if step == "message":
            name = flow.get("name", update.effective_user.full_name)
            phone = flow.get("phone", "")
            username = update.effective_user.username or ""
            uid = update.effective_user.id
            context.user_data.pop("contact_us_flow", None)

            await self.db.add_contact_message(
                user_id=uid,
                full_name=name,
                username=username,
                phone=phone,
                message=text
            )

            await update.effective_message.reply_text(
                "✅ پیام شما با موفقیت ثبت شد و برای ادمین در پنل وب ارسال گردید.\nبه زودی پاسخ مدیریت را دریافت خواهید کرد.",
                reply_markup=keyboards.main_reply()
            )
            return True

        return False

    # ── text router ──────────────────────────────────────
    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = (update.effective_message.text or "").strip()
        if await self.handle_contact_us_text(update, context):
            return
        if await self.admin.handle_text(update, context):
            return
        if text == texts.BTN_CANCEL and context.user_data.pop("admin_auth_pending", None):
            await update.effective_message.reply_text(texts.ADMIN_FLOW_CANCELLED, reply_markup=keyboards.main_reply())
            return
        routes = {
            texts.BTN_NEWS: self.latest_news,
            texts.BTN_TIMES: self.show_times,
            texts.BTN_SETTINGS: self.show_settings,
            texts.BTN_ACCOUNT: self.account_info,
            texts.BTN_REGISTER: self.register_cmd,
            texts.BTN_ADMIN: self.admin_entry,
            texts.BTN_CONTACT_US: self.start_contact_us,
        }
        handler = routes.get(text)
        if handler:
            await handler(update, context)
            return
        if text == texts.BTN_CONTACT:
            await update.effective_message.reply_text(texts.ASK_CONTACT, reply_markup=keyboards.contact_reply())
            return
        await update.effective_message.reply_text(texts.UNKNOWN_TEXT, reply_markup=keyboards.main_reply())

    # ── callbacks ────────────────────────────────────────
    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        data = query.data or ""
        uid = query.from_user.id

        if await self.admin.handle_callback(update, context):
            return

        if data.startswith("cn:"):
            try:
                news_id = int(data.split(":", 1)[1])
            except ValueError:
                await query.answer()
                return
            item = await self.db.get_news(news_id)
            if not item:
                await query.answer("خبر یافت نشد.", show_alert=True)
                return
            await self.db.record_view(news_id, uid)
            await query.answer()
            await send_single_custom(context.bot, query.message.chat_id, item, self.settings, self.catalog)
            return

        user = await self.db.get_user(uid)

        if data == "set:lang":
            await query.answer(texts.LANG_INFO, show_alert=True)
            return

        needs_auth = data in {
            "set:mode", "set:notif", "set:cats", "account",
            "account:logout", "account:logout:yes", "account:logout:no",
        } or data.startswith("cat:")
        if needs_auth and not user:
            await query.answer("ابتدا ثبت‌نام و احراز هویت کنید 🔐", show_alert=True)
            await query.message.reply_text(texts.AUTH_REQUIRED, reply_markup=keyboards.home_inline(False))
            return

        if data == "reg":
            if user:
                await query.answer(texts.ALREADY_REGISTERED, show_alert=True)
                return
            await query.answer()
            await query.message.reply_text(texts.ASK_CONTACT, reply_markup=keyboards.contact_reply())
            return

        if data == "times":
            await query.answer()
            await self._edit(query, texts.schedule_panel(self.settings, user), keyboards.back_inline("home"))
            return

        if data in {"settings", "home"}:
            await query.answer()
            markup = keyboards.settings_inline(user) if data == "settings" else keyboards.home_inline(bool(user))
            await self._edit(query, texts.settings_panel(user, self.settings, self.catalog), markup)
            return

        if data == "set:mode":
            new_mode = "full" if user["delivery_mode"] == "ai" else "ai"
            await self.db.set_delivery_mode(uid, new_mode)
            user = await self.db.get_user(uid)
            await query.answer("نحوه دریافت تغییر کرد ✅")
            await self._edit(query, texts.settings_panel(user, self.settings, self.catalog), keyboards.settings_inline(user))
            return

        if data == "set:notif":
            await self.db.set_notifications(uid, not bool(user["notifications"]))
            user = await self.db.get_user(uid)
            await query.answer("وضعیت اعلان‌ها تغییر کرد ✅")
            await self._edit(query, texts.settings_panel(user, self.settings, self.catalog), keyboards.settings_inline(user))
            return

        if data == "set:cats":
            await query.answer()
            selected = self.catalog.resolve(_user_selection(user))
            await self._edit(query, texts.categories_panel(self.catalog), keyboards.categories_inline(selected, self.catalog))
            return

        if data.startswith("cat:"):
            key = data.split(":", 1)[1]
            current = set(self.catalog.resolve(_user_selection(user)))
            if key == "all":
                new = set(self.catalog.ids)
            else:
                if key not in self.catalog.by_id:
                    await query.answer()
                    return
                current.discard(key) if key in current else current.add(key)
                if not current:
                    await query.answer(texts.MIN_CATEGORY, show_alert=True)
                    return
                new = current
            if new >= set(self.catalog.ids):
                await self.db.set_categories(uid, ["all"])
            else:
                await self.db.set_categories(uid, sorted(new))
            user = await self.db.get_user(uid)
            await query.answer("دسته‌بندی‌ها به‌روزرسانی شد ✅")
            selected = self.catalog.resolve(_user_selection(user))
            await self._edit(query, texts.categories_panel(self.catalog), keyboards.categories_inline(selected, self.catalog))
            return

        if data == "account":
            await query.answer()
            await self._edit(query, texts.account_panel(user, self.settings, self.catalog), keyboards.account_inline())
            return

        if data == "account:logout":
            await query.answer()
            await self._edit(
                query,
                "🚪 آیا مطمئن هستید که می‌خواهید از حساب خارج شوید؟ اطلاعات ثبت‌نام شما حذف خواهد شد.",
                keyboards.logout_confirm_inline(),
            )
            return

        if data == "account:logout:yes":
            await self.db.delete_user(uid)
            await query.answer("خارج شدید")
            await self._edit(query, texts.LOGOUT_DONE)
            await query.message.reply_text(texts.UNKNOWN_TEXT, reply_markup=keyboards.main_reply())
            return

        if data == "account:logout:no":
            await query.answer()
            await self._edit(query, texts.account_panel(user, self.settings, self.catalog), keyboards.account_inline())
            return

        await query.answer()

    # ── errors ───────────────────────────────────────────
    async def on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("update %s caused error %s", update, context.error, exc_info=context.error)
        if isinstance(context.error, Conflict):
            logger.critical("Another instance is polling with this token. Stop it or revoke the token in BotFather.")
