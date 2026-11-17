import asyncio

from bot.catalog import Catalog
from bot.config import Settings
from bot.db import Database
from bot.digest import custom_news_block, send_custom_news

from pathlib import Path

SOURCES = Path(__file__).resolve().parent.parent / "sources.json"


def test_admin_and_custom_news_roundtrip(tmp_path):
    db = Database(tmp_path / "admin.db")

    async def run():
        await db.init()
        assert await db.is_admin(10) is False
        await db.add_admin(10, "+989120000000")
        assert await db.is_admin(10) is True
        assert len(await db.list_admins()) == 1
        await db.remove_admin(10)
        assert await db.is_admin(10) is False

        news_id = await db.add_news("عنوان آزمایشی", "متن خبر", "https://example.com", "general", 10)
        assert news_id >= 1
        item = await db.get_news(news_id)
        assert item["title"] == "عنوان آزمایشی"
        assert item["published"] == 1

        assert await db.count_news() == 1
        page = await db.news_page(0, 5)
        assert page[0]["views"] == 0

        assert await db.record_view(news_id, 1) is True
        assert await db.record_view(news_id, 1) is False  # unique per user
        assert await db.record_view(news_id, 2) is True
        assert await db.view_count(news_id) == 2
        assert await db.total_views() == 2
        assert (await db.news_page(0, 5))[0]["views"] == 2
        assert (await db.top_news(1))[0]["views"] == 2

        await db.delete_news(news_id)
        assert await db.get_news(news_id) is None
        assert await db.view_count(news_id) == 0

    asyncio.run(run())


def test_custom_news_block_and_delivery_filter(tmp_path):
    db = Database(tmp_path / "custom.db")
    settings = Settings(bot_token="123456:ABC-DEF")
    catalog = Catalog.from_file(SOURCES)

    async def run():
        await db.init()
        await db.register(1, "+989121111111", "Ali", "ali")
        sports_id = await db.add_news("خبر ورزشی", "متن ورزشی", "", "sports", 99)
        tech_id = await db.add_news("خبر فناوری", "متن فناوری", "", "technology", 99)

        block = custom_news_block(await db.get_news(sports_id), settings, catalog)
        assert "خبر ورزشی" in block
        assert "ورزشی" in block

        sent = []

        class FakeBot:
            async def send_message(self, **kwargs):
                sent.append(kwargs)

        user = await db.get_user(1)
        await db.set_categories(1, ["sports"])
        user = await db.get_user(1)
        delivered = await send_custom_news(FakeBot(), 1, db, settings, catalog, user)
        assert delivered == 1
        assert len(sent) == 1
        assert "خبر ورزشی" in sent[0]["text"]
        assert await db.view_count(sports_id) == 1
        assert await db.view_count(tech_id) == 0

    asyncio.run(run())


def test_admin_phone_allowlist():
    from bot.admin import AdminPanel

    settings = Settings(bot_token="123456:ABC-DEF", admin_phones=frozenset({"+989120000000"}))
    catalog = Catalog.from_file(SOURCES)
    panel = AdminPanel(settings, catalog, Database(":memory:"))
    assert panel._phone_allowed("+989120000000") is True
    assert panel._phone_allowed("+989999999999") is False

    open_settings = Settings(bot_token="123456:ABC-DEF")
    open_panel = AdminPanel(open_settings, catalog, Database(":memory:"))
    assert open_panel._phone_allowed("+989999999999") is True
