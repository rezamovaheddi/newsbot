import asyncio
from datetime import datetime, timezone
from pathlib import Path

from bot.catalog import Catalog
from bot.config import Settings
from bot.digest import _pack, _shorten, build_digest
from bot.news import NewsItem

SOURCES = Path(__file__).resolve().parent.parent / "sources.json"


def test_shorten():
    assert _shorten("abcdef", 4) == "abc…"
    assert _shorten("ab", 4) == "ab"


def test_pack():
    messages = _pack("H", ["a" * 1000, "b" * 1000, "c" * 1000, "d" * 1000])
    assert all(len(m) <= 3500 for m in messages)
    assert len(messages) >= 2


class FakeAggregator:
    async def fetch(self, categories=None, limit=None):
        return [
            NewsItem(
                title="خبر آزمایشی",
                link="https://example.com/1",
                source="منبع آزمایشی",
                category="general",
                published=datetime.now(timezone.utc),
                description="این یک توضیح آزمایشی است.",
            )
        ]


def test_build_digest_fallback():
    settings = Settings(bot_token="123456:ABC-DEF")
    catalog = Catalog.from_file(SOURCES)
    chunks = asyncio.run(build_digest(None, settings, catalog, FakeAggregator()))
    assert chunks
    assert "خبر آزمایشی" in chunks[0]
    assert "example.com" in chunks[0]
