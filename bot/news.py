"""RSS aggregation with concurrency, caching and deduplication."""
from __future__ import annotations

import asyncio
import calendar
import logging
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Sequence

import feedparser
import httpx

from .catalog import Catalog, Feed
from .utils import canonical_url, clean_html, normalize_fa, safe_http_url, title_key

logger = logging.getLogger(__name__)
USER_AGENT = "SmartNewsBot/1.0 (Persian Telegram news digest bot)"


@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    link: str
    source: str
    category: str
    published: datetime | None
    description: str = ""
    tags: tuple[str, ...] = ()


def _entry_datetime(entry: dict) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
    return None


def _entry_source(entry: dict, fallback: str) -> str:
    source = entry.get("source")
    if isinstance(source, dict) and source.get("title"):
        return clean_html(str(source["title"]))
    if hasattr(source, "title"):
        return clean_html(str(source.title))
    return fallback


def _entry_tags(entry: dict) -> tuple[str, ...]:
    tags: list[str] = []
    for tag in entry.get("tags", []) or []:
        term = tag.get("term") if isinstance(tag, dict) else getattr(tag, "term", None)
        if term:
            tags.append(str(term))
    return tuple(tags)


def _matches_feed(item: NewsItem, feed: Feed) -> bool:
    if not feed.tags_any and not feed.keywords_any:
        return True
    tags = [normalize_fa(t) for t in item.tags]
    if feed.tags_any and any(normalize_fa(want) in tag for want in feed.tags_any for tag in tags):
        return True
    if feed.keywords_any:
        # Title-only matching keeps category precision high (avoids incidental words in long summaries).
        text = normalize_fa(item.title)
        if any(normalize_fa(word) in text for word in feed.keywords_any):
            return True
    return False


class NewsAggregator:
    def __init__(self, catalog: Catalog, timeout: float = 12.0, cache_ttl: int = 300, limit: int = 8) -> None:
        self.catalog = catalog
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.limit = limit
        self._cache: dict[str, tuple[float, list[NewsItem]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def fetch(self, categories: Sequence[str] | None = None, limit: int | None = None) -> list[NewsItem]:
        ids = self.catalog.resolve(categories)
        size = limit or self.limit
        key = f"{','.join(ids)}:{size}"
        now = time.monotonic()
        if self.cache_ttl > 0 and key in self._cache:
            stamp, items = self._cache[key]
            if now - stamp < self.cache_ttl:
                return list(items)

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            if self.cache_ttl > 0 and key in self._cache:
                stamp, items = self._cache[key]
                if now - stamp < self.cache_ttl:
                    return list(items)

            # Fetch each unique URL once, even if it belongs to several categories.
            feed_map: dict[str, str] = {}
            for cid in ids:
                for feed in self.catalog.by_id[cid].feeds:
                    feed_map.setdefault(feed.url, feed.name)

            semaphore = asyncio.Semaphore(6)
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                tasks = [self._fetch_feed(client, semaphore, url, name) for url, name in feed_map.items()]
                results = await asyncio.gather(*tasks, return_exceptions=True)

            raw_by_url: dict[str, list[NewsItem]] = {}
            for url, result in zip(feed_map.keys(), results):
                if isinstance(result, Exception):
                    logger.warning("feed failed: %s", result)
                    continue
                raw_by_url[url] = result

            items: list[NewsItem] = []
            for cid in ids:
                for feed in self.catalog.by_id[cid].feeds:
                    for item in raw_by_url.get(feed.url, []):
                        if _matches_feed(item, feed):
                            items.append(replace(item, category=cid))

            selected = self._dedupe_sort(items)[:size]
            if self.cache_ttl > 0:
                self._cache[key] = (time.monotonic(), list(selected))
            return selected

    async def _fetch_feed(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        url: str,
        name: str,
    ) -> list[NewsItem]:
        async with semaphore:
            response = await client.get(url)
            response.raise_for_status()
            parsed = await asyncio.to_thread(feedparser.parse, response.content)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            raise ValueError(f"invalid feed: {url}")
        is_google = "news.google.com" in url
        items: list[NewsItem] = []
        for entry in parsed.entries[:40]:
            title = clean_html(str(entry.get("title", "")))
            link = str(entry.get("link", ""))
            if not title or not safe_http_url(link):
                continue
            description = ""
            if not is_google:
                description = clean_html(str(entry.get("summary", "")))[:500]
            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    source=_entry_source(entry, name),
                    category="",
                    published=_entry_datetime(entry),
                    description=description,
                    tags=_entry_tags(entry),
                )
            )
        return items

    @staticmethod
    def _dedupe_sort(items: list[NewsItem]) -> list[NewsItem]:
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        unique: list[NewsItem] = []
        for item in items:
            curl = canonical_url(item.link)
            tkey = title_key(item.title)
            if curl in seen_urls or (tkey and tkey in seen_titles):
                continue
            seen_urls.add(curl)
            if tkey:
                seen_titles.add(tkey)
            unique.append(item)
        unique.sort(key=lambda it: it.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return unique
