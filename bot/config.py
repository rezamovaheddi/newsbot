"""Configuration loaded from environment variables / .env."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEDULE = ((8, 0), (13, 30), (20, 0))
TOKEN_RE = re.compile(r"\d{5,12}:[A-Za-z0-9_-]{20,}")


class ConfigError(ValueError):
    """A human-readable configuration error."""


def parse_schedule(raw: str) -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    for part in raw.split(","):
        part = part.strip()
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", part)
        if not match:
            raise ConfigError(f"زمان نامعتبر در SCHEDULE_TIMES: {part!r}")
        hour, minute = int(match[1]), int(match[2])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ConfigError(f"زمان نامعتبر در SCHEDULE_TIMES: {part!r}")
        result.append((hour, minute))
    if not result:
        raise ConfigError("SCHEDULE_TIMES باید حداقل یک زمان داشته باشد.")
    return tuple(sorted(set(result)))


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} باید عدد صحیح باشد.") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} باید بین {minimum} و {maximum} باشد.")
    return value


def _float_env(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} باید عدد باشد.") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} باید بین {minimum} و {maximum} باشد.")
    return value


def _path_env(name: str, default: str) -> Path:
    path = Path(os.getenv(name, default)).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = field(repr=False)
    bot_name: str = "اخبار هوشمند"
    db_path: Path = BASE_DIR / "data" / "bot.db"
    sources_path: Path = BASE_DIR / "sources.json"
    timezone: str = "Asia/Tehran"
    schedule: tuple[tuple[int, int], ...] = DEFAULT_SCHEDULE
    admin_ids: frozenset[int] = frozenset()
    admin_phones: frozenset[str] = frozenset()
    news_per_digest: int = 8
    custom_news_limit: int = 5
    feed_timeout: float = 12.0
    cache_ttl: int = 300
    openai_api_key: str = field(default="", repr=False)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    web_admin_url: str = "http://localhost:8000"
    web_admin_port: int = 8000

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(BASE_DIR / ".env", override=False)
        token = os.getenv("BOT_TOKEN", "").strip()
        if not TOKEN_RE.fullmatch(token):
            raise ConfigError("BOT_TOKEN تنظیم نشده یا معتبر نیست. فایل .env را بررسی کنید.")

        timezone = os.getenv("TIMEZONE", "Asia/Tehran").strip()
        try:
            ZoneInfo(timezone)
        except Exception as exc:
            raise ConfigError(f"TIMEZONE نامعتبر است: {timezone}") from exc

        admins: set[int] = set()
        for part in os.getenv("ADMIN_IDS", "").split(","):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit() or int(part) <= 0:
                raise ConfigError("ADMIN_IDS باید شناسه‌های عددی مثبت جداشده با کاما باشد.")
            admins.add(int(part))

        admin_phones: set[str] = set()
        for part in os.getenv("ADMIN_PHONES", "").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                from .utils import normalize_phone

                admin_phones.add(normalize_phone(part))
            except ValueError:
                raise ConfigError(f"ADMIN_PHONES contains an invalid phone number: {part}")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
        if not base_url.startswith(("https://", "http://")):
            raise ConfigError("OPENAI_BASE_URL باید با http:// یا https:// شروع شود.")

        return cls(
            bot_token=token,
            bot_name=os.getenv("BOT_NAME", "اخبار هوشمند").strip() or "اخبار هوشمند",
            db_path=_path_env("DB_PATH", "data/bot.db"),
            sources_path=_path_env("SOURCES_FILE", "sources.json"),
            timezone=timezone,
            schedule=parse_schedule(os.getenv("SCHEDULE_TIMES", "08:00,13:30,20:00")),
            admin_ids=frozenset(admins),
            admin_phones=frozenset(admin_phones),
            news_per_digest=_int_env("NEWS_PER_DIGEST", 8, 1, 15),
            custom_news_limit=_int_env("CUSTOM_NEWS_LIMIT", 5, 1, 10),
            feed_timeout=_float_env("FEED_TIMEOUT", 12, 3, 60),
            cache_ttl=_int_env("CACHE_TTL", 300, 0, 3600),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=base_url,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            web_admin_url=os.getenv("WEB_ADMIN_URL", "http://localhost:8000").strip(),
            web_admin_port=_int_env("WEB_ADMIN_PORT", 8000, 80, 65535),
        )
