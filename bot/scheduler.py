"""Daily scheduled news delivery."""
from __future__ import annotations

import asyncio
import logging
from datetime import time as dtime
from zoneinfo import ZoneInfo

from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import Application, ContextTypes

from . import texts
from .catalog import Catalog
from .config import Settings
from .db import Database
from .digest import _user_selection, build_digest, send_chunks, send_custom_news
from .news import NewsAggregator

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, settings: Settings, catalog: Catalog, db: Database, aggregator: NewsAggregator) -> None:
        self.settings = settings
        self.catalog = catalog
        self.db = db
        self.aggregator = aggregator

    def setup(self, app: Application) -> None:
        tz = ZoneInfo(self.settings.timezone)
        for hour, minute in self.settings.schedule:
            app.job_queue.run_daily(
                self._job,
                time=dtime(hour, minute, tzinfo=tz),
                name=f"digest-{hour:02d}:{minute:02d}",
            )
        logger.info("scheduled daily digests at %s (%s)", self.settings.schedule, self.settings.timezone)

    async def _job(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        users = await self.db.active_users()
        logger.info("scheduled digest: %d active users", len(users))
        if not users:
            return

        # Group users by (mode, categories) so each unique digest is built once.
        groups: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
        for user in users:
            key = (user["delivery_mode"], tuple(sorted(self.catalog.resolve(_user_selection(user)))))
            groups.setdefault(key, []).append(user)

        for members in groups.values():
            try:
                chunks = await build_digest(members[0], self.settings, self.catalog, self.aggregator)
            except Exception:  # noqa: BLE001
                logger.exception("scheduled digest build failed")
                continue
            for user in members:
                await self._deliver(context, user, chunks)
                await asyncio.sleep(0.05)

    async def _deliver(self, context: ContextTypes.DEFAULT_TYPE, user: dict, chunks: list[str]) -> None:
        chat_id = user["user_id"]
        try:
            custom_count = await send_custom_news(context.bot, chat_id, self.db, self.settings, self.catalog, user)
            if chunks == [texts.NO_NEWS] and custom_count:
                return
            await send_chunks(context.bot, chat_id, chunks)
        except RetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
            try:
                await send_chunks(context.bot, chat_id, chunks)
            except TelegramError as retry_exc:
                logger.warning("delivery to %s failed after retry: %s", chat_id, retry_exc)
        except Forbidden:
            await self.db.set_notifications(chat_id, False)
            logger.info("user %s blocked the bot; notifications disabled", chat_id)
        except TelegramError as exc:
            logger.warning("delivery to %s failed: %s", chat_id, exc)
