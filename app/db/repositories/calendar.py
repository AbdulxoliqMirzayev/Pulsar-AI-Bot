from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EconomicEvent


class CalendarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_many(self, events: list[dict]) -> None:
        for event in events:
            payload = _json_ready(event)
            self.session.add(
                EconomicEvent(
                    provider=event.get("provider"),
                    event_name=event.get("event_name", "USD event"),
                    country=event.get("country"),
                    currency=event.get("currency"),
                    impact=event.get("impact"),
                    forecast=event.get("forecast"),
                    previous=event.get("previous"),
                    actual=event.get("actual"),
                    event_time_utc=event.get("event_time_utc"),
                    raw_payload=payload,
                    related_instruments=event.get("related_instruments", ["BTCUSDT", "XAUUSD"]),
                )
            )
        await self.session.commit()


def _json_ready(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value
