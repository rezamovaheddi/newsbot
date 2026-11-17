import asyncio
import json

from bot.db import Database


def test_db_roundtrip(tmp_path):
    db = Database(tmp_path / "t.db")

    async def run():
        await db.init()
        assert await db.get_user(1) is None
        await db.register(1, "+989123456789", "Ali", "ali")
        user = await db.get_user(1)
        assert user["phone"] == "+989123456789"
        assert user["notifications"] == 1
        assert user["delivery_mode"] == "ai"

        await db.set_delivery_mode(1, "full")
        assert (await db.get_user(1))["delivery_mode"] == "full"

        await db.set_notifications(1, False)
        assert (await db.get_user(1))["notifications"] == 0
        assert await db.active_users() == []

        await db.set_categories(1, ["sports", "technology"])
        assert json.loads((await db.get_user(1))["categories"]) == ["sports", "technology"]
        await db.set_categories(1, ["all"])
        assert json.loads((await db.get_user(1))["categories"]) == ["all"]

        stats = await db.stats()
        assert stats["total"] == 1

        await db.delete_user(1)
        assert await db.get_user(1) is None

    asyncio.run(run())
