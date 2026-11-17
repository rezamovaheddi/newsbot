"""All Persian UI strings and panel builders."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .catalog import Catalog
from .config import Settings
from .utils import escape, fa_digits, jalali_date, local_time, mask_phone, schedule_label

BTN_NEWS = "📰 دریافت آخرین اخبار"
BTN_TIMES = "⏰ دریافت زمان اخبار"
BTN_SETTINGS = "⚙️ تنظیمات"
BTN_ACCOUNT = "📋 اطلاعات حساب کاربری"
BTN_REGISTER = "🔐 ثبت‌نام و احراز هویت"
BTN_CONTACT = "📱 ارسال شماره تلفن"
BTN_CANCEL = "🔙 بازگشت"
BTN_ADMIN = "🛠 پنل ادمین"
BTN_CONTACT_US = "📞 ارتباط با ما"

WELCOME = (
    "👋 به ربات «اخبار هوشمند» خوش آمدید!\n\n"
    "🤖 خبرهای فارسی را دسته‌بندی‌شده و در زمان‌های مشخص دریافت کنید.\n"
    "🔐 برای دریافت اخبار و استفاده از امکانات حساب، ابتدا ثبت‌نام و احراز هویت کنید."
)
AUTH_REQUIRED = (
    "⚠️ شما احراز هویت نکرده‌اید!\n"
    "برای استفاده از این بخش، ابتدا ثبت‌نام و احراز هویت را انجام دهید."
)
ASK_CONTACT = (
    "🔐 ثبت‌نام و احراز هویت\n\n"
    "برای تأیید هویت، دکمهٔ «ارسال شماره تلفن» را بزنید تا شمارهٔ خودتان با تلگرام به اشتراک گذاشته شود.\n\n"
    "🔒 شماره فقط برای احراز هویت و نمایش در حساب کاربری استفاده می‌شود و در پیام‌های خبری ارسال نمی‌شود."
)
CONTACT_REJECT = "⚠️ فقط شمارهٔ متعلق به خودتان را با دکمهٔ ارسال شماره به اشتراک بگذارید."
PHONE_TAKEN = "⚠️ این شماره قبلاً به حساب تلگرام دیگری متصل شده است. اگر اشتباه است با پشتیبانی تماس بگیرید."
REGISTER_SUCCESS = "✅ ثبت‌نام و احراز هویت با موفقیت انجام شد.\n\n📱 شماره: {phone}\nاز این پس می‌توانید اخبار را دریافت کنید."
ALREADY_REGISTERED = "✅ شما قبلاً احراز هویت کرده‌اید."
LOGOUT_DONE = "🚪 از حساب کاربری خارج شدید و اطلاعات ثبت‌نام شما حذف شد."
NO_NEWS = "⚠️ در حال حاضر خبر قابل نمایشی از منابع دریافت نشد. کمی بعد دوباره تلاش کنید."
LOADING_NEWS = "⏳ در حال دریافت آخرین اخبار..."
UNKNOWN_TEXT = "برای استفاده از ربات، یکی از دکمه‌های منو را انتخاب کنید."
COOLDOWN = "⏳ کمی صبر کنید و دوباره تلاش کنید."
LANG_INFO = "در حال حاضر زبان سامانه فارسی است 🇮🇷"
MIN_CATEGORY = "حداقل یک دسته‌بندی باید فعال باشد."
NOT_ADMIN = "این دستور فقط برای مدیر ربات است."
ERROR = "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید."

ADMIN_ASK_CONTACT = (
    "🛠 پنل ادمین\n\n"
    "برای ورود به پنل مدیریت، شماره تلفن خود را با دکمه زیر ارسال کنید.\n\n"
    "⚠️ در پیکربندی پیش‌فرض، احراز هویت ادمین با هر شماره‌ای امکان‌پذیر است. "
    "برای محدودسازی به شماره‌های مشخص، ADMIN_PHONES را در .env تنظیم کنید."
)
ADMIN_GRANTED = "✅ احراز هویت ادمین انجام شد. به پنل مدیریت خوش آمدید."
ADMIN_DENIED = "⛔ این شماره مجاز به ورود به پنل ادمین نیست."
ADMIN_REQUIRED = "⛔ شما دسترسی ادمین ندارید."
ADMIN_LOGOUT = "🚪 از پنل ادمین خارج شدید."
ADMIN_PANEL_TITLE = "🛠 پنل مدیریت\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
ADMIN_ADD_TITLE = "➕ افزودن خبر\n\n۱/۴ — عنوان خبر را ارسال کنید:"
ADMIN_ADD_BODY = "۲/۴ — متن خبر را ارسال کنید:"
ADMIN_ADD_LINK = "۳/۴ — لینک خبر را ارسال کنید یا «بدون لینک» را بزنید:"
ADMIN_ADD_CATEGORY = "۴/۴ — دسته‌بندی خبر را انتخاب کنید:"
ADMIN_ADD_SAVED = "✅ خبر با شناسه {id} ذخیره شد و در اخبار ربات اصلی نمایش داده می‌شود."
ADMIN_ADD_CANCELLED = "❌ افزودن خبر لغو شد."
ADMIN_NO_NEWS = "هنوز خبری اضافه نشده است."
ADMIN_NO_USERS = "هنوز کاربری ثبت‌نام نکرده است."
ADMIN_DELETE_CONFIRM = "🗑 خبر #{id} حذف شود؟ این عمل قابل بازگشت نیست."
ADMIN_DELETED = "🗑 خبر حذف شد."
ADMIN_FLOW_CANCELLED = "❌ عملیات لغو شد."

HELP = (
    "📖 راهنمای ربات اخبار هوشمند\n\n"
    "/start — شروع و منوی اصلی\n"
    "/register — ثبت‌نام و احراز هویت با شماره تلفن\n"
    "/news — دریافت آخرین اخبار\n"
    "/times — زمان‌بندی ارسال اخبار\n"
    "/settings — تنظیمات کاربری\n"
    "/account — اطلاعات حساب کاربری\n"
    "/privacy — حریم خصوصی\n"
    "/help — راهنما\n\n"
    "🔐 دریافت اخبار و امکانات حساب نیاز به احراز هویت دارد."
)
PRIVACY = (
    "🔒 حریم خصوصی\n\n"
    "• شماره تلفن فقط هنگام احراز هویت و با دکمهٔ رسمی تلگرام دریافت می‌شود.\n"
    "• شماره در پایگاه دادهٔ محلی ربات ذخیره می‌شود و در پیام‌های خبری یا خلاصه‌های AI ارسال نمی‌شود.\n"
    "• در حساب کاربری، شماره به‌صورت ماسک‌شده نمایش داده می‌شود.\n"
    "• با «خروج از حساب» اطلاعات ثبت‌نام شما حذف می‌شود.\n"
    "• منابع خبری عمومی هستند و ربات به کانال‌های خصوصی تلگرام دسترسی ندارد."
)


def welcome_back(name: str) -> str:
    return f"👋 {name or 'کاربر'} عزیز، خوش آمدید!\n\n✅ احراز هویت شما فعال است."


def delivery_label(mode: str) -> str:
    return "خلاصه هوشمند (AI Summary)" if mode == "ai" else "توضیح بیشتر خبرها"


def delivery_short(mode: str) -> str:
    return "خلاصه هوشمند" if mode == "ai" else "توضیح بیشتر"


def notif_label(enabled: bool | int) -> str:
    return "فعال 🔔" if enabled else "غیرفعال 🔕"


def _user_categories(user: dict[str, Any] | None, catalog: Catalog) -> list[str]:
    if not user:
        return ["all"]
    import json

    try:
        value = json.loads(user.get("categories", '["all"]'))
        return value if isinstance(value, list) else ["all"]
    except (TypeError, ValueError):
        return ["all"]


def settings_panel(user: dict[str, Any] | None, settings: Settings, catalog: Catalog) -> str:
    mode = user.get("delivery_mode", "ai") if user else "ai"
    notifications = user.get("notifications", 1) if user else 1
    categories = _user_categories(user, catalog)
    lines = [
        "⚙️ تنظیمات کاربری ربات:",
        "",
        "🔷 زبان سامانه: فارسی 🇮🇷",
        f"🔷 نحوه دریافت اخبار: {delivery_label(mode)}",
        f"🔷 وضعیت اعلان‌ها: {notif_label(notifications)}",
        f"🔷 دسته‌بندی‌های فعال: {catalog.label(categories)}",
        "",
    ]
    if mode == "ai" and not settings.ai_enabled:
        lines.append("ℹ️ کلید AI تنظیم نشده است؛ فعلاً گزیدهٔ متنی خبرها ارسال می‌شود.")
    if user:
        lines.append("ℹ️ با دکمه‌های زیر می‌توانید تنظیمات را تغییر دهید.")
    else:
        lines.append("🔐 برای تغییر و ذخیرهٔ تنظیمات، ابتدا ثبت‌نام و احراز هویت کنید.")
    return "\n".join(lines)


def schedule_panel(settings: Settings, user: dict[str, Any] | None = None) -> str:
    lines = ["⏰ زمان‌بندی ارسال اخبار:", ""]
    for hour, minute in settings.schedule:
        lines.append(f"🔷 نوبت {schedule_label(hour)}: ساعت {fa_digits(f'{hour:02d}:{minute:02d}')}")
    lines.extend(["", f"🕐 زمان‌ها بر اساس منطقهٔ زمانی {settings.timezone} است."])
    if user and not user.get("notifications", 1):
        lines.append("🔕 اعلان‌های شما غیرفعال است؛ ارسال خودکار انجام نمی‌شود.")
    elif user is None:
        lines.append("🔐 برای دریافت خودکار، ثبت‌نام کنید و اعلان‌ها را فعال نگه دارید.")
    return "\n".join(lines)


def account_panel(user: dict[str, Any], settings: Settings, catalog: Catalog) -> str:
    created = user.get("created_at", "")
    try:
        created_dt = datetime.fromisoformat(created)
        created_text = f"{jalali_date(created_dt, settings.timezone)} ساعت {local_time(created_dt, settings.timezone)}"
    except ValueError:
        created_text = fa_digits(created)
    username = user.get("username") or "—"
    if username != "—":
        username = "@" + username
    categories = _user_categories(user, catalog)
    return (
        "📋 اطلاعات حساب کاربری\n\n"
        f"👤 نام: {user.get('first_name') or '—'}\n"
        f"🔗 نام کاربری: {username}\n"
        f"📱 شماره: {mask_phone(user.get('phone', ''))}\n"
        f"🆔 شناسه کاربری: {fa_digits(user.get('user_id'))}\n"
        f"📅 تاریخ عضویت: {created_text}\n\n"
        f"📰 نحوه دریافت: {delivery_label(user.get('delivery_mode', 'ai'))}\n"
        f"🔔 اعلان‌ها: {notif_label(user.get('notifications', 1))}\n"
        f"🗂 دسته‌بندی‌ها: {catalog.label(categories)}"
    )


def categories_panel(catalog: Catalog) -> str:
    return "🗂 دسته‌بندی‌های خبری\n\nدسته‌های موردعلاقهٔ خود را انتخاب کنید. حداقل یک دسته باید فعال باشد."


def stats_panel(stats: dict[str, int]) -> str:
    return (
        "📊 آمار ربات\n\n"
        f"👥 کاربران ثبت‌نام‌شده: {fa_digits(stats['total'])}\n"
        f"🔔 اعلان فعال: {fa_digits(stats['active'])}\n"
        f"🤖 حالت خلاصه هوشمند: {fa_digits(stats['ai_mode'])}"
    )


def admin_news_list_panel(items: list[dict[str, Any]], page: int, total: int) -> str:
    lines = [f"📰 لیست اخبار (صفحه {fa_digits(page + 1)}) — مجموع: {fa_digits(total)}", ""]
    if not items:
        lines.append(ADMIN_NO_NEWS)
    for item in items:
        status = "🟢" if item.get("published") else "⚪"
        lines.append(
            f"{status} #{fa_digits(item['id'])} — {_short(item['title'], 40)}\n"
            f"   👁 بازدید: {fa_digits(item.get('views', 0))} • 🗂 {item.get('category', '')}"
        )
    return "\n".join(lines)


def admin_news_detail_panel(item: dict[str, Any], views: int) -> str:
    lines = [
        f"📰 خبر #{fa_digits(item['id'])}",
        "",
        f"عنوان: {item['title']}",
        f"متن: {item.get('body') or '—'}",
        f"لینک: {item.get('link') or '—'}",
        f"دسته: {item.get('category', '')}",
        f"وضعیت: {'منتشرشده' if item.get('published') else 'پیش‌نویس'}",
        f"👁 بازدید یکتا: {fa_digits(views)}",
        f"📅 ایجاد: {item.get('created_at', '')}",
    ]
    return "\n".join(lines)


def admin_users_panel(users: list[dict[str, Any]], page: int, total: int) -> str:
    lines = [f"👥 لیست کاربران (صفحه {fa_digits(page + 1)}) — مجموع: {fa_digits(total)}", ""]
    if not users:
        lines.append(ADMIN_NO_USERS)
    for u in users:
        username = ("@" + u["username"]) if u.get("username") else "—"
        notif = "🔔" if u.get("notifications") else "🔕"
        lines.append(
            f"• {u.get('first_name') or '—'} ({username})\n"
            f"   📱 {mask_phone(u.get('phone', ''))} • 🆔 {fa_digits(u['user_id'])} • {notif}\n"
            f"   📅 {u.get('created_at', '')}"
        )
    return "\n".join(lines)


def admin_stats_panel(stats: dict[str, int], news_count: int, total_views: int, top: list[dict[str, Any]]) -> str:
    lines = [
        "📊 آمار کلی",
        "",
        f"👥 کاربران: {fa_digits(stats['total'])}",
        f"🔔 اعلان فعال: {fa_digits(stats['active'])}",
        f"📰 اخبار: {fa_digits(news_count)}",
        f"👁 مجموع بازدید یکتا: {fa_digits(total_views)}",
        "",
        "🏆 پربازدیدترین اخبار:",
    ]
    if not top:
        lines.append("—")
    for item in top:
        lines.append(f"• #{fa_digits(item['id'])} {_short(item['title'], 30)} — 👁 {fa_digits(item.get('views', 0))}")
    return "\n".join(lines)


def _short(value: str, size: int) -> str:
    value = (value or "").strip()
    return value if len(value) <= size else value[: size - 1] + "…"


def digest_header(settings: Settings, catalog: Catalog, categories: list[str], mode: str, ai_used: bool) -> str:
    now = datetime.now().astimezone()
    title = "🤖 خلاصه هوشمند" if ai_used else ("🧾 گزیدهٔ خبری" if mode == "ai" else "📄 خبرها با توضیحات")
    return (
        f"🗞 <b>{escape(settings.bot_name)}</b>\n"
        f"📅 {jalali_date(now, settings.timezone)} • 🕐 {local_time(now, settings.timezone)}\n"
        f"🗂 {escape(catalog.label(categories))}\n"
        f"{title}"
    )

FALLBACK_NOTE = "ℹ️ این گزیده از عنوان و توضیح منابع ساخته شده است. برای خلاصهٔ AI، کلید OPENAI_API_KEY را در .env تنظیم کنید."
