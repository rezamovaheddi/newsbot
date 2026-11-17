"""Telegram keyboards."""
from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from . import texts
from .catalog import Catalog


def main_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(texts.BTN_NEWS)],
            [KeyboardButton(texts.BTN_TIMES), KeyboardButton(texts.BTN_SETTINGS)],
            [KeyboardButton(texts.BTN_ACCOUNT), KeyboardButton(texts.BTN_CONTACT_US)],
            [KeyboardButton(texts.BTN_ADMIN)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="یک گزینه را انتخاب کنید…",
    )


def contact_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(texts.BTN_CONTACT, request_contact=True)], [KeyboardButton(texts.BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="شمارهٔ خودتان را ارسال کنید…",
    )


def home_inline(authenticated: bool) -> InlineKeyboardMarkup:
    rows = []
    if authenticated:
        rows.append([InlineKeyboardButton(texts.BTN_ACCOUNT, callback_data="account")])
    else:
        rows.append([InlineKeyboardButton(texts.BTN_REGISTER, callback_data="reg")])
    rows.append([InlineKeyboardButton(texts.BTN_TIMES, callback_data="times")])
    rows.append([InlineKeyboardButton(texts.BTN_SETTINGS, callback_data="settings")])
    return InlineKeyboardMarkup(rows)


def back_inline(target: str = "home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(texts.BTN_CANCEL, callback_data=target)]])


def settings_inline(user: dict[str, Any] | None) -> InlineKeyboardMarkup:
    mode = user.get("delivery_mode", "ai") if user else "ai"
    notifications = bool(user.get("notifications", 1)) if user else True
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"📰 نحوه دریافت: {texts.delivery_short(mode)}", callback_data="set:mode")],
            [InlineKeyboardButton(f"🔔 اعلان‌ها: {texts.notif_label(notifications)}", callback_data="set:notif")],
            [InlineKeyboardButton("🗂 انتخاب دسته‌بندی‌ها", callback_data="set:cats")],
            [InlineKeyboardButton("🌐 زبان: فارسی 🇮🇷", callback_data="set:lang")],
            [InlineKeyboardButton(texts.BTN_CANCEL, callback_data="home")],
        ]
    )


def categories_inline(selected: tuple[str, ...], catalog: Catalog) -> InlineKeyboardMarkup:
    rows = []
    all_selected = set(selected) >= set(catalog.ids)
    all_label = ("✅ " if all_selected else "") + "همه کانال‌های خبری"
    rows.append([InlineKeyboardButton(all_label, callback_data="cat:all")])
    for category in catalog.categories:
        mark = "✅" if category.id in selected else "▫️"
        rows.append([InlineKeyboardButton(f"{mark} {category.label}", callback_data=f"cat:{category.id}")])
    rows.append([InlineKeyboardButton(texts.BTN_CANCEL, callback_data="settings")])
    return InlineKeyboardMarkup(rows)


def account_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🚪 خروج از حساب", callback_data="account:logout")],
            [InlineKeyboardButton(texts.BTN_CANCEL, callback_data="home")],
        ]
    )


def logout_confirm_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("بله، خارج شو", callback_data="account:logout:yes")],
            [InlineKeyboardButton("خیر", callback_data="account:logout:no")],
        ]
    )


# ── admin ────────────────────────────────────────────────
def admin_panel_inline(web_url: str = "") -> InlineKeyboardMarkup:
    rows = []
    # Telegram only accepts HTTP/HTTPS URLs with valid domain or IP in inline buttons, rejects localhost
    if web_url and not ("localhost" in web_url or "127.0.0.1" in web_url):
        rows.append([InlineKeyboardButton("🌐 باز کردن پنل وب ادمین", url=web_url)])
    rows.extend([
        [InlineKeyboardButton("➕ افزودن خبر", callback_data="adm:add")],
        [InlineKeyboardButton("📰 لیست اخبار", callback_data="adm:news:0")],
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="adm:users:0")],
        [InlineKeyboardButton("📊 آمار و بازدیدها", callback_data="adm:stats")],
        [InlineKeyboardButton("🚪 خروج از پنل ادمین", callback_data="adm:logout")],
    ])
    return InlineKeyboardMarkup(rows)


def admin_news_list_inline(items: list[dict], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        title = item["title"][:28] + ("…" if len(item["title"]) > 28 else "")
        rows.append(
            [InlineKeyboardButton(f"#{item['id']} {title} • 👁 {item.get('views', 0)}", callback_data=f"adm:nv:{item['id']}:{page}")]
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"adm:news:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"adm:news:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="adm:panel")])
    return InlineKeyboardMarkup(rows)


def admin_news_detail_inline(news_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📣 ارسال همگانی", callback_data=f"adm:bc:{news_id}:{page}")],
            [InlineKeyboardButton("🗑 حذف خبر", callback_data=f"adm:nd:{news_id}:{page}")],
            [InlineKeyboardButton("🔙 لیست اخبار", callback_data=f"adm:news:{page}")],
        ]
    )


def admin_news_delete_inline(news_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("بله، حذف شود", callback_data=f"adm:ndy:{news_id}:{page}")],
            [InlineKeyboardButton("خیر", callback_data=f"adm:nv:{news_id}:{page}")],
        ]
    )


def admin_users_inline(page: int, has_next: bool) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"adm:users:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"adm:users:{page + 1}"))
    rows = [nav] if nav else []
    rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="adm:panel")])
    return InlineKeyboardMarkup(rows)


def admin_stats_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="adm:panel")]])


def admin_skip_link_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("بدون لینک ➡️", callback_data="adm:add:nolink")],
            [InlineKeyboardButton("❌ لغو", callback_data="adm:add:cancel")],
        ]
    )


def admin_category_inline(catalog: Catalog) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(cat.label, callback_data=f"adm:add:cat:{cat.id}")] for cat in catalog.categories]
    rows.append([InlineKeyboardButton("❌ لغو", callback_data="adm:add:cancel")])
    return InlineKeyboardMarkup(rows)
