from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class NewsEvent:
    title: str
    source: str
    url: str | None = None
    published_at: datetime | None = None
    summary: str | None = None
    sentiment: str = "neutral"
    impact_score: float = 0.0
    related_instruments: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class CalendarEvent:
    event_name: str
    country: str | None
    currency: str | None
    impact: str | None
    event_time_utc: datetime | None
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None
    provider: str = "unknown"

    def to_dict(self) -> dict:
        return asdict(self)
