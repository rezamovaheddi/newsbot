from datetime import datetime, timezone

from bot.catalog import Feed
from bot.news import NewsItem, _matches_feed


def item(tags=(), title="خبر نمونه", description=""):
    return NewsItem(
        title=title,
        link="https://example.com/a",
        source="منبع",
        category="",
        published=datetime.now(timezone.utc),
        description=description,
        tags=tags,
    )


def test_matches_feed_no_filter():
    assert _matches_feed(item(), Feed(name="x", url="https://example.com/rss"))


def test_matches_feed_tags():
    feed = Feed(name="x", url="https://example.com/rss", tags_any=("ورزش",))
    assert _matches_feed(item(tags=("جهان ورزش",)), feed)
    assert not _matches_feed(item(tags=("اقتصاد",)), feed)


def test_matches_feed_keywords():
    feed = Feed(name="x", url="https://example.com/rss", keywords_any=("هوش مصنوعی",))
    assert _matches_feed(item(title="پیشرفت هوش مصنوعی"), feed)
    assert not _matches_feed(item(title="خبر ورزشی"), feed)
    assert not _matches_feed(item(title="خبر عمومی", description="هوش مصنوعی"), feed)


def test_matches_feed_ai_keywords_and_tags():
    feed = Feed(
        name="x",
        url="https://example.com/rss",
        keywords_any=("هوش مصنوعی", "chatgpt", "openai", "یادگیری ماشین", "اوپن ای آی"),
        tags_any=("هوش مصنوعی",),
    )
    assert _matches_feed(item(title="پیشرفت هوش\u200cمصنوعی در ایران"), feed)
    assert _matches_feed(item(title="ChatGPT gets a new feature"), feed)
    assert _matches_feed(item(title="اوپن\u200cای\u200cآی مدل جدید داد"), feed)
    assert _matches_feed(item(title="آیا آگاهی شکل دیگری دارد؟", tags=("هوش مصنوعی", "علم")), feed)
    assert not _matches_feed(item(title="خبر ورزشی", description="هوش مصنوعی و ChatGPT"), feed)
    assert not _matches_feed(item(title="خبر اقتصادی", tags=("اقتصاد",)), feed)
