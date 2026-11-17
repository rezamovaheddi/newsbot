"""FastAPI web server for the admin panel and contact-us API."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import Database

logger = logging.getLogger(__name__)

DIST_DIR = Path(__file__).resolve().parent.parent / "web-admin" / "dist"


class ReplyPayload(BaseModel):
    reply: str


def create_app(db: Database, bot=None) -> FastAPI:
    app = FastAPI(title="NewsBot Web Admin")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/stats")
    async def get_stats():
        stats_dict = await db.stats()
        async with db.connect() as conn:
            async with conn.execute("SELECT COUNT(*) FROM contact_messages") as cur:
                (msg_count,) = await cur.fetchone()
        stats_dict["total_messages"] = msg_count
        return stats_dict

    @app.get("/api/messages")
    async def get_messages():
        async with db.connect() as conn:
            async with conn.execute(
                "SELECT id, user_id, full_name, username, phone, message, created_at, status FROM contact_messages ORDER BY id DESC"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    @app.delete("/api/messages/{msg_id}")
    async def delete_message(msg_id: int):
        async with db.connect() as conn:
            await conn.execute("DELETE FROM contact_messages WHERE id = ?", (msg_id,))
            await conn.commit()
        return {"ok": True}

    @app.post("/api/messages/{msg_id}/reply")
    async def reply_message(msg_id: int, payload: ReplyPayload):
        async with db.connect() as conn:
            async with conn.execute("SELECT user_id, full_name FROM contact_messages WHERE id = ?", (msg_id,)) as cur:
                row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Message not found")
        user_id = row["user_id"]
        if bot:
            try:
                reply_text = (
                    f"📩 **پاسخ پشتیبانی به پیام شما:**\n\n"
                    f"{payload.reply}\n\n"
                    f"با تشکر از ارتباط شما با ربات اخبار هوشمند."
                )
                await bot.send_message(chat_id=user_id, text=reply_text)
            except Exception as e:
                logger.error("Failed to send telegram reply: %s", e)
                raise HTTPException(status_code=500, detail=str(e))
        return {"ok": True}

    @app.get("/api/users")
    async def get_users():
        async with db.connect() as conn:
            async with conn.execute(
                "SELECT user_id, first_name, username, phone, created_at FROM users ORDER BY created_at DESC LIMIT 100"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    @app.get("/api/news")
    async def get_news():
        async with db.connect() as conn:
            async with conn.execute(
                """
                SELECT cn.id, cn.title, cn.body, cn.link, cn.category, cn.published, cn.created_at,
                       COUNT(nv.user_id) as views
                FROM custom_news cn
                LEFT JOIN news_views nv ON nv.news_id = cn.id
                GROUP BY cn.id
                ORDER BY cn.id DESC
                LIMIT 50
                """
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    if DIST_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = DIST_DIR / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(DIST_DIR / "index.html")

    return app
