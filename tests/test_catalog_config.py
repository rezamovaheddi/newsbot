from pathlib import Path

from bot.catalog import Catalog
from bot.config import ConfigError, parse_schedule

import pytest

SOURCES = Path(__file__).resolve().parent.parent / "sources.json"


def test_catalog():
    catalog = Catalog.from_file(SOURCES)
    assert "general" in catalog.ids
    assert "ai" in catalog.ids
    assert catalog.by_id["ai"].title == "هوش مصنوعی"
    assert catalog.resolve(["ai"]) == ("ai",)
    assert catalog.resolve(None) == catalog.ids
    assert catalog.resolve(["all"]) == catalog.ids
    assert catalog.resolve(["sports"]) == ("sports",)
    assert catalog.is_all(["all"])
    assert catalog.label(["all"]) == "همه کانال‌های خبری"


def test_ai_category_sources():
    catalog = Catalog.from_file(SOURCES)
    ai = catalog.by_id["ai"]
    assert ai.label == "🤖 هوش مصنوعی"
    assert any("1itnevis.com" in feed.url for feed in ai.feeds)
    assert any(feed.tags_any for feed in ai.feeds)
    assert all(feed.keywords_any or feed.tags_any for feed in ai.feeds)


def test_parse_schedule():
    assert parse_schedule("08:00,13:30,20:00") == ((8, 0), (13, 30), (20, 0))
    assert parse_schedule("8:00") == ((8, 0),)


def test_parse_schedule_invalid():
    with pytest.raises(ConfigError):
        parse_schedule("25:00")
    with pytest.raises(ConfigError):
        parse_schedule("abc")
