"""Build Telegram-safe HTML digests."""
from __future__ import annotations

import json
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.constants import ParseMode

from . import texts
from .ai import summarize
from .catalog import Catalog
from .config import Settings
from .db import Database
from .news import NewsAggregator, NewsItem
from .utils import escape, fa_digits, jalali_date, local_time, split_plain_text

MAX_MESSAGE = 3500


def _shorten(value: str, size: int) -> str:
    value = value.strip()
    return value if len(value) <= size else value[: size - 1].rstrip() + "…"


def _user_selection(user: dict[str, Any] | None) -> list[str]:
    if not user:
        return ["all"]
    try:
        value = json.loads(user.get("categories", '["all"]'))
        return value if isinstance(value, list) and value else ["all"]
    except (TypeError, ValueError):
        return ["all"]


def _item_block(item: NewsItem, index: int, settings: Settings, full: bool) -> str:
    lines = [f"{fa_digits(index)}. <b>{escape(_shorten(item.title, 220))}</b>"]
    meta = f"📌 {escape(item.source)}"
    if item.published:
        meta += f" • 🕐 {local_time(item.published, settings.timezone)}"
    lines.append(meta)
    if item.description:
        lines.append(escape(_shorten(item.description, 320 if full else 160)))
    lines.append(f'🔗 <a href="{escape(item.link)}">مشاهده خبر</a>')
    return "\n".join(lines)


def _pack(header: str, blocks: list[str], footer: str | None = None) -> list[str]:
    messages: list[str] = []
    current = header
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > MAX_MESSAGE and current:
            messages.append(current)
            current = block
        else:
            current = candidate
    if footer:
        candidate = f"{current}\n\n{footer}" if current else footer
        if len(candidate) > MAX_MESSAGE and current:
            messages.append(current)
            current = footer
        else:
            current = candidate
    if current:
        messages.append(current)
    return messages


async def build_digest(
    user: dict[str, Any] | None,
    settings: Settings,
    catalog: Catalog,
    aggregator: NewsAggregator,
) -> list[str]:
    selection = _user_selection(user)
    mode = user.get("delivery_mode", "ai") if user else "ai"
    items = await aggregator.fetch(selection, settings.news_per_digest)
    if not items:
        return [texts.NO_NEWS]

    ai_text = await summarize(items, settings) if mode == "ai" else None
    header = texts.digest_header(settings, catalog, selection, mode, ai_used=bool(ai_text))

    if ai_text:
        chunks = split_plain_text(ai_text, MAX_MESSAGE - len(header) - 4)
        messages = [header + "\n\n" + escape(chunk) for chunk in chunks] or [header]
        source_blocks = [
            f'{fa_digits(i)}. <a href="{escape(item.link)}">{escape(_shorten(item.title, 80))}</a> — {escape(item.source)}'
            for i, item in enumerate(items, start=1)
        ]
        messages.extend(_pack("🔗 <b>منابع</b>", source_blocks))
        return messages

    blocks = [_item_block(item, i, settings, full=(mode == "full")) for i, item in enumerate(items, start=1)]
    footer = texts.FALLBACK_NOTE if mode == "ai" else None
    return _pack(header, blocks, footer)


async def send_chunks(bot: Bot, chat_id: int, chunks: list[str]) -> None:
    for chunk in chunks:
        await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


# ── admin-authored custom news ───────────────────────────
def custom_news_block(item: dict[str, Any], settings: Settings, catalog: Catalog | None = None, full: bool = True) -> str:
    category = item.get("category", "general")
    label = catalog.by_id[category].label if catalog and category in catalog.by_id else category
    lines = [
        f"📌 <b>خبر اختصاصی #{fa_digits(item['id'])}</b>",
        f"<b>{escape(_shorten(item.get('title', ''), 220))}</b>",
        f"🗂 {escape(label)}",
    ]
    body = item.get("body") or ""
    if body:
        lines.append(escape(body if full else _shorten(body, 220)))
    if item.get("link"):
        lines.append(f'🔗 <a href="{escape(item["link"])}">مشاهده خبر</a>')
    created = item.get("created_at") or ""
    try:
        from datetime import datetime

        dt = datetime.fromisoformat(created)
        lines.append(f"🕐 {jalali_date(dt, settings.timezone)} • {local_time(dt, settings.timezone)}")
    except (ValueError, TypeError):
        pass
    return "\n".join(lines)


async def send_single_custom(
    bot: Bot,
    chat_id: int,
    item: dict[str, Any],
    settings: Settings,
    catalog: Catalog | None = None,
    with_button: bool = False,
) -> None:
    markup = None
    if with_button:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👁 مشاهده کامل خبر", callback_data=f"cn:{item['id']}")]]
        )
    await bot.send_message(
        chat_id=chat_id,
        text=custom_news_block(item, settings, catalog, full=True),
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=markup,
    )


async def send_custom_news(
    bot: Bot,
    chat_id: int,
    db: Database,
    settings: Settings,
    catalog: Catalog,
    user: dict[str, Any] | None,
) -> int:
    """Deliver admin-authored news to a user and count a unique view per user."""
    selection = set(catalog.resolve(_user_selection(user)))
    items = await db.published_news(settings.custom_news_limit)
    delivered = 0
    for item in items:
        if item.get("category") not in selection:
            continue
        await send_single_custom(bot, chat_id, item, settings, catalog, with_button=True)
        await db.record_view(item["id"], chat_id)
        delivered += 1
    return delivered
