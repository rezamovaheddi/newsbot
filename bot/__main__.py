"""Entry point: python -m bot."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application

from .catalog import Catalog
from .config import ConfigError, Settings
from .db import Database
from .handlers import BotHandlers
from .news import NewsAggregator
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        raise SystemExit(f"❌ {exc}")

    catalog = Catalog.from_file(settings.sources_path)
    db = Database(settings.db_path)
    aggregator = NewsAggregator(
        catalog,
        timeout=settings.feed_timeout,
        cache_ttl=settings.cache_ttl,
        limit=settings.news_per_digest,
    )
    handlers = BotHandlers(settings, catalog, db, aggregator)
    scheduler = Scheduler(settings, catalog, db, aggregator)

    app = Application.builder().token(settings.bot_token).post_init(handlers.post_init).build()
    handlers.register(app)
    scheduler.setup(app)

    # Start FastAPI Web Admin Server in background thread
    from .server import create_app
    import uvicorn
    import threading

    web_app = create_app(db, bot=app.bot)

    def run_web():
        uvicorn.run(web_app, host="0.0.0.0", port=settings.web_admin_port, log_level="warning")

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    logger.info("web admin server started on port %d", settings.web_admin_port)

    logger.info(
        "starting %s | categories=%d | schedule=%s | ai=%s",
        settings.bot_name, len(catalog.ids), settings.schedule, settings.ai_enabled,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
