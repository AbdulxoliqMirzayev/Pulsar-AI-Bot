from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings
from app.services.fundamental.models import CalendarEvent


class EconomicCalendarClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def upcoming_usd_events(self, days: int = 7) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        if self.settings.trading_economics_enable:
            events.extend(await self._trading_economics(days=days))
        if self.settings.forexfactory_rss_enable:
            events.extend(await self._forex_factory_xml())
        return sorted(events, key=lambda event: event.event_time_utc or datetime.max.replace(tzinfo=UTC))

    async def _trading_economics(self, days: int = 7) -> list[CalendarEvent]:
        start = datetime.now(UTC).date().isoformat()
        end = (datetime.now(UTC) + timedelta(days=days)).date().isoformat()
        key = self.settings.trading_economics_key or "guest:guest"
        url = f"https://api.tradingeconomics.com/calendar/country/united%20states/{start}/{end}"
        try:
            response = await self.client.get(url, params={"c": key, "importance": "2"})
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        output: list[CalendarEvent] = []
        for item in response.json():
            output.append(
                CalendarEvent(
                    provider="tradingeconomics",
                    event_name=item.get("Event") or item.get("event") or item.get("Category") or "USD event",
                    country=item.get("Country") or item.get("country") or "United States",
                    currency=item.get("Currency") or item.get("currency") or "USD",
                    impact=str(item.get("Importance") or item.get("importance") or ""),
                    event_time_utc=self._parse_dt(item.get("Date") or item.get("date")),
                    actual=self._clean(item.get("Actual") or item.get("actual")),
                    forecast=self._clean(item.get("Forecast") or item.get("forecast")),
                    previous=self._clean(item.get("Previous") or item.get("previous")),
                )
            )
        return output

    async def _forex_factory_xml(self) -> list[CalendarEvent]:
        url = self.settings.forexfactory_rss_url
        try:
            response = await self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return []
        output: list[CalendarEvent] = []
        for event in root.findall(".//event"):
            currency = self._text(event, "currency")
            if currency != "USD":
                continue
            output.append(
                CalendarEvent(
                    provider="forexfactory",
                    event_name=self._text(event, "title") or "USD event",
                    country="United States",
                    currency=currency,
                    impact=self._text(event, "impact"),
                    event_time_utc=self._parse_ff_time(self._text(event, "date"), self._text(event, "time")),
                    actual=self._text(event, "actual"),
                    forecast=self._text(event, "forecast"),
                    previous=self._text(event, "previous"),
                )
            )
        return output

    def _text(self, event: ET.Element, tag: str) -> str | None:
        node = event.find(tag)
        return node.text.strip() if node is not None and node.text else None

    def _parse_dt(self, raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None

    def _parse_ff_time(self, date: str | None, time: str | None) -> datetime | None:
        if not date:
            return None
        raw = f"{date} {time or '00:00'}".replace("All Day", "00:00")
        for fmt in ("%m-%d-%Y %I:%M%p", "%m-%d-%Y %H:%M", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return None

    def _clean(self, value: object) -> str | None:
        if value in (None, "", "null"):
            return None
        return str(value)
