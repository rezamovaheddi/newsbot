"""Async SQLite persistence. Phone numbers stay in the local database only."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from .utils import utc_now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY,
    phone         TEXT NOT NULL UNIQUE,
    first_name    TEXT NOT NULL DEFAULT '',
    username      TEXT NOT NULL DEFAULT '',
    language      TEXT NOT NULL DEFAULT 'fa',
    delivery_mode TEXT NOT NULL DEFAULT 'ai' CHECK (delivery_mode IN ('ai', 'full')),
    notifications INTEGER NOT NULL DEFAULT 1 CHECK (notifications IN (0, 1)),
    categories    TEXT NOT NULL DEFAULT '["all"]',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_users_notifications ON users(notifications);

CREATE TABLE IF NOT EXISTS admins (
    user_id    INTEGER PRIMARY KEY,
    phone      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_news (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    link       TEXT NOT NULL DEFAULT '',
    category   TEXT NOT NULL DEFAULT 'general',
    published  INTEGER NOT NULL DEFAULT 1 CHECK (published IN (0, 1)),
    created_by INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_custom_news_published ON custom_news(published, id);

CREATE TABLE IF NOT EXISTS news_views (
    news_id   INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    viewed_at TEXT NOT NULL,
    PRIMARY KEY (news_id, user_id)
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    full_name  TEXT NOT NULL,
    username   TEXT NOT NULL DEFAULT '',
    phone      TEXT NOT NULL DEFAULT '',
    message    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);
"""

UPDATABLE_FIELDS = {"delivery_mode", "notifications", "categories", "first_name", "username"}


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)
        async with self.connect() as conn:
            await conn.executescript(SCHEMA)
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA user_version=1")
            await conn.commit()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[aiosqlite.Connection]:
        async with aiosqlite.connect(self.path, timeout=10) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA busy_timeout=5000")
            await conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
            finally:
                for suffix in ("", "-wal", "-shm"):
                    sidecar = Path(str(self.path) + suffix)
                    if sidecar.exists():
                        os.chmod(sidecar, 0o600)

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def register(self, user_id: int, phone: str, first_name: str, username: str) -> dict[str, Any]:
        now = utc_now_iso()
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, phone, first_name, username, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    phone = excluded.phone,
                    first_name = excluded.first_name,
                    username = excluded.username,
                    updated_at = excluded.updated_at
                """,
                (user_id, phone, first_name or "", username or "", now, now),
            )
            await conn.commit()
        user = await self.get_user(user_id)
        assert user is not None
        return user

    async def touch_profile(self, user_id: int, first_name: str, username: str) -> None:
        async with self.connect() as conn:
            await conn.execute(
                "UPDATE users SET first_name = ?, username = ?, updated_at = ? WHERE user_id = ?",
                (first_name or "", username or "", utc_now_iso(), user_id),
            )
            await conn.commit()

    async def _set(self, user_id: int, field: str, value: Any) -> None:
        if field not in UPDATABLE_FIELDS:
            raise ValueError(f"field is not updatable: {field}")
        async with self.connect() as conn:
            await conn.execute(
                f"UPDATE users SET {field} = ?, updated_at = ? WHERE user_id = ?",
                (value, utc_now_iso(), user_id),
            )
            await conn.commit()

    async def set_delivery_mode(self, user_id: int, mode: str) -> None:
        if mode not in {"ai", "full"}:
            raise ValueError("invalid delivery mode")
        await self._set(user_id, "delivery_mode", mode)

    async def set_notifications(self, user_id: int, enabled: bool) -> None:
        await self._set(user_id, "notifications", int(enabled))

    async def set_categories(self, user_id: int, categories: list[str] | tuple[str, ...]) -> None:
        if categories and categories[0] == "all":
            payload = '["all"]'
        else:
            payload = json.dumps(sorted(set(categories)), ensure_ascii=False)
        await self._set(user_id, "categories", payload)

    async def delete_user(self, user_id: int) -> None:
        async with self.connect() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await conn.commit()

    async def active_users(self) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM users WHERE notifications = 1 ORDER BY user_id") as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def stats(self) -> dict[str, int]:
        async with self.connect() as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(notifications), 0) AS active,
                       COALESCE(SUM(delivery_mode = 'ai'), 0) AS ai_mode
                FROM users
                """
            ) as cur:
                row = await cur.fetchone()
                return {k: int(row[k]) for k in ("total", "active", "ai_mode")}

    async def phone_owner(self, phone: str) -> int | None:
        async with self.connect() as conn:
            async with conn.execute("SELECT user_id FROM users WHERE phone = ?", (phone,)) as cur:
                row = await cur.fetchone()
                return int(row["user_id"]) if row else None

    async def users_page(self, offset: int, limit: int) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC, user_id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def all_users(self) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM users ORDER BY user_id") as cur:
                return [dict(row) for row in await cur.fetchall()]

    # ── admins ───────────────────────────────────────────
    async def add_admin(self, user_id: int, phone: str) -> None:
        async with self.connect() as conn:
            await conn.execute(
                """
                INSERT INTO admins (user_id, phone, created_at) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET phone = excluded.phone
                """,
                (user_id, phone, utc_now_iso()),
            )
            await conn.commit()

    async def is_admin(self, user_id: int) -> bool:
        async with self.connect() as conn:
            async with conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cur:
                return await cur.fetchone() is not None

    async def remove_admin(self, user_id: int) -> None:
        async with self.connect() as conn:
            await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await conn.commit()

    async def list_admins(self) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM admins ORDER BY created_at") as cur:
                return [dict(row) for row in await cur.fetchall()]

    # ── custom news ──────────────────────────────────────
    async def add_news(self, title: str, body: str, link: str, category: str, created_by: int) -> int:
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO custom_news (title, body, link, category, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, body, link, category, created_by, utc_now_iso()),
            )
            await conn.commit()
            return int(cur.lastrowid)

    async def get_news(self, news_id: int) -> dict[str, Any] | None:
        async with self.connect() as conn:
            async with conn.execute("SELECT * FROM custom_news WHERE id = ?", (news_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def delete_news(self, news_id: int) -> None:
        async with self.connect() as conn:
            await conn.execute("DELETE FROM custom_news WHERE id = ?", (news_id,))
            await conn.execute("DELETE FROM news_views WHERE news_id = ?", (news_id,))
            await conn.commit()

    async def count_news(self) -> int:
        async with self.connect() as conn:
            async with conn.execute("SELECT COUNT(*) AS c FROM custom_news") as cur:
                row = await cur.fetchone()
                return int(row["c"])

    async def news_page(self, offset: int, limit: int) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute(
                """
                SELECT n.*, (SELECT COUNT(*) FROM news_views v WHERE v.news_id = n.id) AS views
                FROM custom_news n ORDER BY n.id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def published_news(self, limit: int = 5) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute(
                "SELECT * FROM custom_news WHERE published = 1 ORDER BY id DESC LIMIT ?",
                (limit,),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def top_news(self, limit: int = 5) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute(
                """
                SELECT n.*, (SELECT COUNT(*) FROM news_views v WHERE v.news_id = n.id) AS views
                FROM custom_news n ORDER BY views DESC, n.id DESC LIMIT ?
                """,
                (limit,),
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]

    async def total_views(self) -> int:
        async with self.connect() as conn:
            async with conn.execute("SELECT COUNT(*) AS c FROM news_views") as cur:
                row = await cur.fetchone()
                return int(row["c"])

    # ── views ────────────────────────────────────────────
    async def record_view(self, news_id: int, user_id: int) -> bool:
        async with self.connect() as conn:
            cur = await conn.execute(
                "INSERT OR IGNORE INTO news_views (news_id, user_id, viewed_at) VALUES (?, ?, ?)",
                (news_id, user_id, utc_now_iso()),
            )
            await conn.commit()
            return cur.rowcount > 0

    async def view_count(self, news_id: int) -> int:
        async with self.connect() as conn:
            async with conn.execute("SELECT COUNT(*) AS c FROM news_views WHERE news_id = ?", (news_id,)) as cur:
                row = await cur.fetchone()
                return int(row["c"])


    async def add_contact_message(
        self, user_id: int, full_name: str, username: str, phone: str, message: str
    ) -> int:
        now = utc_now_iso()
        async with self.connect() as conn:
            cur = await conn.execute(
                """
                INSERT INTO contact_messages (user_id, full_name, username, phone, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, full_name, username, phone, message, now),
            )
            await conn.commit()
            return cur.lastrowid

    async def list_contact_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self.connect() as conn:
            async with conn.execute(
                "SELECT * FROM contact_messages ORDER BY id DESC LIMIT ?", (limit,)
            ) as cur:
                return [dict(row) for row in await cur.fetchall()]


def is_unique_phone_error(exc: Exception) -> bool:
    return isinstance(exc, sqlite3.IntegrityError) and "users.phone" in str(exc)
