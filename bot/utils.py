"""Small, dependency-light helpers."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import jdatetime

FA_TRANS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def fa_digits(value: object) -> str:
    return str(value).translate(FA_TRANS)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_phone(raw: str) -> str:
    """Normalize Telegram contact numbers to E.164; Iranian local format is also accepted."""
    value = re.sub(r"[\s()\-]", "", raw or "")
    if value.startswith("00"):
        value = "+" + value[2:]
    elif value.startswith("98") and len(value) == 12:
        value = "+" + value
    elif value.startswith("0") and len(value) == 11:
        value = "+98" + value[1:]
    elif not value.startswith("+"):
        value = "+" + value
    if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
        raise ValueError("شماره تلفن معتبر نیست.")
    return value


def mask_phone(phone: str) -> str:
    if len(phone) <= 5:
        return "****"
    return fa_digits(phone[:3] + " **** **" + phone[-2:])


def clean_html(raw: str) -> str:
    class Extractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []
            self.skip = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag in {"script", "style"}:
                self.skip += 1
            if tag in {"br", "p", "div", "li", "tr"}:
                self.parts.append("\n")

        def handle_endtag(self, tag: str) -> None:
            if tag in {"script", "style"} and self.skip:
                self.skip -= 1

        def handle_data(self, data: str) -> None:
            if not self.skip:
                self.parts.append(data)

    parser = Extractor()
    try:
        parser.feed(raw or "")
        parser.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def canonical_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))
    except ValueError:
        return url


def safe_http_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return parts.scheme in {"http", "https"} and bool(parts.netloc)
    except ValueError:
        return False


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def split_plain_text(text: str, limit: int = 3500) -> list[str]:
    """Split plain text before HTML escaping, so tags are never cut in half."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n"):
        while len(paragraph) > limit:
            cut = paragraph.rfind(" ", 0, limit)
            if cut < limit // 2:
                cut = limit
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        candidate = f"{current}\n{paragraph}" if current else paragraph
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [c for c in chunks if c]


def jalali_date(dt: datetime, tz_name: str = "Asia/Tehran") -> str:
    local = dt.astimezone(ZoneInfo(tz_name))
    return fa_digits(jdatetime.date.fromgregorian(date=local.date()).strftime("%Y/%m/%d"))


def local_time(dt: datetime, tz_name: str = "Asia/Tehran") -> str:
    return fa_digits(dt.astimezone(ZoneInfo(tz_name)).strftime("%H:%M"))


def schedule_label(hour: int) -> str:
    if hour < 12:
        return "صبح"
    if hour < 17:
        return "ظهر"
    return "شب"


def normalize_fa(text: str) -> str:
    return (
        text.replace("ي", "ی")
        .replace("ك", "ک")
        .replace("\u200c", " ")
        .replace("\u200f", "")
        .replace("\u200e", "")
        .lower()
    )


def title_key(title: str) -> str:
    return re.sub(r"[^\w\s]", "", normalize_fa(title)).strip().lower()
