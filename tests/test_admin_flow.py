"""End-to-end simulation of the admin panel flow with fake Telegram objects."""
import asyncio
from pathlib import Path
from types import SimpleNamespace

from bot.admin import AdminPanel
from bot.catalog import Catalog
from bot.config import Settings
from bot.db import Database

SOURCES = Path(__file__).resolve().parent.parent / "sources.json"


class FakeMessage:
    def __init__(self):
        self.sent = []
        self.chat_id = 555
        self.text = ""
        self.contact = None

    async def reply_text(self, text, reply_markup=None, **kw):
        self.sent.append(text)
        return self


class FakeQuery:
    def __init__(self, data, message):
        self.data = data
        self.message = message
        self.from_user = SimpleNamespace(id=555)
        self.edits = []
        self.answers = []

    async def answer(self, text=None, show_alert=False):
        self.answers.append(text)

    async def edit_message_text(self, text, reply_markup=None, **kw):
        self.edits.append(text)
        self.message.sent.append(text)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        self.sent.append(text)


def make_update(message=None, query=None):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=555, first_name="Admin", username="admin"),
        effective_chat=SimpleNamespace(id=555),
        effective_message=message,
        callback_query=query,
    )


def test_admin_full_flow(tmp_path):
    db = Database(tmp_path / "flow.db")
    settings = Settings(bot_token="123456:ABC-DEF")
    catalog = Catalog.from_file(SOURCES)
    panel = AdminPanel(settings, catalog, db)
    bot = FakeBot()
    context = SimpleNamespace(user_data={}, bot=bot)

    async def run():
        await db.init()
        msg = FakeMessage()

        # 1) entry -> asks for contact (any phone allowed by default)
        await panel.entry(make_update(message=msg), context)
        assert context.user_data.get("admin_auth_pending") is True
        assert any("پنل ادمین" in t for t in msg.sent)

        # 2) share own contact -> becomes admin
        msg.contact = SimpleNamespace(user_id=555, phone_number="+989121234567")
        handled = await panel.handle_contact(make_update(message=msg), context)
        assert handled is True
        assert await db.is_admin(555) is True
        assert "admin_auth_pending" not in context.user_data

        # 3) open add-news flow
        q = FakeQuery("adm:add", msg)
        assert await panel.handle_callback(make_update(query=q), context) is True
        assert context.user_data["admin_flow"]["step"] == "title"

        # 4) title -> body -> link -> category
        msg.text = "خبر فوری آزمایشی"
        assert await panel.handle_text(make_update(message=msg), context) is True
        assert context.user_data["admin_flow"]["step"] == "body"

        msg.text = "این متن خبر اختصاصی است که توسط ادمین نوشته شده."
        assert await panel.handle_text(make_update(message=msg), context) is True
        assert context.user_data["admin_flow"]["step"] == "link"

        q = FakeQuery("adm:add:nolink", msg)
        assert await panel.handle_callback(make_update(query=q), context) is True
        assert context.user_data["admin_flow"]["step"] == "category"

        q = FakeQuery("adm:add:cat:technology", msg)
        assert await panel.handle_callback(make_update(query=q), context) is True
        assert "admin_flow" not in context.user_data
        assert await db.count_news() == 1
        item = (await db.news_page(0, 5))[0]
        assert item["title"] == "خبر فوری آزمایشی"
        assert item["category"] == "technology"
        assert "متن خبر اختصاصی" in item["body"]

        news_id = item["id"]

        # 5) news list shows the item with view counter
        q = FakeQuery("adm:news:0", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert any("لیست اخبار" in t for t in q.edits)

        # 6) detail + view counting
        await db.record_view(news_id, 1)
        await db.record_view(news_id, 2)
        await db.record_view(news_id, 1)  # duplicate, still unique
        q = FakeQuery(f"adm:nv:{news_id}:0", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert any("بازدید یکتا: ۲" in t for t in q.edits)

        # 7) users list read from DB
        await db.register(900, "+989120000001", "User One", "userone")
        q = FakeQuery("adm:users:0", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert any("لیست کاربران" in t and "User One" in t for t in q.edits)

        # 8) stats
        q = FakeQuery("adm:stats", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert any("آمار کلی" in t and "۲" in t for t in q.edits)

        # 9) delete news
        q = FakeQuery(f"adm:ndy:{news_id}:0", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert await db.count_news() == 0

        # 10) non-admin is rejected
        q = FakeQuery("adm:panel", msg)
        q.from_user = SimpleNamespace(id=999)
        await panel.handle_callback(make_update(query=q), context)
        assert q.answers and "دسترسی ادمین ندارید" in (q.answers[0] or "")

        # 11) logout removes admin
        q = FakeQuery("adm:logout", msg)
        await panel.handle_callback(make_update(query=q), context)
        assert await db.is_admin(555) is False

    asyncio.run(run())
