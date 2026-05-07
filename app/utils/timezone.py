from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_now(tz: str = "Asia/Tashkent") -> datetime:
    return datetime.now(ZoneInfo(tz))


def today_key(tz: str = "Asia/Tashkent") -> str:
    return local_now(tz).date().isoformat()
