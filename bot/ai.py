"""Optional OpenAI-compatible Persian summarization."""
from __future__ import annotations

import logging

import httpx

from .config import Settings
from .news import NewsItem

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "تو یک سردبیر خبری فارسی‌زبان هستی. خبرهای ارائه‌شده را به یک بولتن خبری کوتاه، دقیق و بی‌طرف "
    "به فارسی خلاصه کن. فقط از اطلاعات داده‌شده استفاده کن و چیزی اضافه نکن. "
    "برای هر خبر یک بولت کوتاه با ایموجی مناسب بنویس و نام منبع را در انتهای بولت داخل پرانتز بیاور. "
    "از مارک‌داون، تیترهای طولانی و مقدمه‌چینی استفاده نکن. متن خروجی باید ساده و قابل ارسال در تلگرام باشد."
)


async def summarize(items: list[NewsItem], settings: Settings) -> str | None:
    if not settings.ai_enabled or not items:
        return None
    parts = []
    for index, item in enumerate(items, start=1):
        parts.append(
            f"{index}. عنوان: {item.title}\n"
            f"منبع: {item.source}\n"
            f"توضیح: {item.description or '—'}"
        )
    payload = {
        "model": settings.openai_model,
        "temperature": 0.2,
        "max_tokens": 900,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(parts)},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception as exc:  # noqa: BLE001 - never break news delivery because of AI
        logger.warning("AI summarization failed: %s", exc)
    return None
