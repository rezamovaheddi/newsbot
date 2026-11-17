"""News source catalog loaded from sources.json."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .utils import safe_http_url

ID_RE = re.compile(r"^[a-z0-9_]{2,32}$")


@dataclass(frozen=True, slots=True)
class Feed:
    name: str
    url: str
    tags_any: tuple[str, ...] = ()
    keywords_any: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Category:
    id: str
    title: str
    emoji: str
    feeds: tuple[Feed, ...]

    @property
    def label(self) -> str:
        return f"{self.emoji} {self.title}".strip()


class Catalog:
    def __init__(self, categories: Sequence[Category]) -> None:
        if not categories:
            raise ValueError("sources.json must contain at least one category")
        ids = [c.id for c in categories]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate category id in sources.json")
        self.categories = tuple(categories)
        self.by_id = {c.id: c for c in self.categories}
        self.ids = tuple(ids)

    @classmethod
    def from_file(cls, path: Path | str) -> "Catalog":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        raw_categories = data.get("categories")
        if not isinstance(raw_categories, list):
            raise ValueError("sources.json: 'categories' must be a list")
        categories: list[Category] = []
        for raw in raw_categories:
            cid = str(raw.get("id", "")).strip()
            title = str(raw.get("title", "")).strip()
            if not ID_RE.fullmatch(cid):
                raise ValueError(f"sources.json: invalid category id {cid!r}")
            if not title:
                raise ValueError(f"sources.json: category {cid} needs a title")
            feeds: list[Feed] = []
            for feed in raw.get("feeds", []):
                url = str(feed.get("url", "")).strip()
                name = str(feed.get("name", "")).strip() or url
                if not safe_http_url(url):
                    raise ValueError(f"sources.json: invalid feed url in {cid}: {url!r}")
                tags_any = tuple(str(x).strip() for x in feed.get("tags_any", []) if str(x).strip())
                keywords_any = tuple(str(x).strip() for x in feed.get("keywords_any", []) if str(x).strip())
                feeds.append(Feed(name=name, url=url, tags_any=tags_any, keywords_any=keywords_any))
            if not feeds:
                raise ValueError(f"sources.json: category {cid} has no feeds")
            categories.append(Category(id=cid, title=title, emoji=str(raw.get("emoji", "")).strip(), feeds=tuple(feeds)))
        return cls(categories)

    def resolve(self, selection: Iterable[str] | str | None) -> tuple[str, ...]:
        """Return concrete category ids. 'all', None or empty means every category."""
        if selection is None:
            return self.ids
        if isinstance(selection, str):
            selection = [selection]
        selected = {s for s in selection if s in self.by_id}
        if not selected or "all" in selection:
            return self.ids
        return tuple(cid for cid in self.ids if cid in selected)

    def is_all(self, selection: Iterable[str] | str | None) -> bool:
        if isinstance(selection, str):
            selection = [selection]
        if selection is None:
            return True
        selection = list(selection)
        if not selection or "all" in selection:
            return True
        return set(selection) >= set(self.ids)

    def label(self, selection: Iterable[str] | str | None) -> str:
        if self.is_all(selection):
            return "همه کانال‌های خبری"
        ids = self.resolve(selection)
        return "، ".join(self.by_id[cid].title for cid in ids)

    def selected_ids(self, selection: Iterable[str] | str | None) -> tuple[str, ...]:
        return self.resolve(selection)
