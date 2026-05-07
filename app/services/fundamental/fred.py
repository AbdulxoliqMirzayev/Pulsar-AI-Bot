from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from app.config import Settings


MACRO_SERIES = {
    "DGS10": "US 10Y Treasury yield",
    "DFF": "Effective Fed Funds Rate",
    "CPIAUCSL": "US CPI",
    "UNRATE": "US Unemployment Rate",
    "PAYEMS": "US Nonfarm Payrolls",
}


class FredClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=20)

    async def latest_macro_snapshot(self) -> dict[str, dict]:
        if not self.settings.fred_enable or not self.settings.fred_api_key:
            return {}
        output: dict[str, dict] = {}
        for series_id, title in MACRO_SERIES.items():
            latest = await self._latest(series_id)
            if latest:
                output[series_id] = {"title": title, **latest}
        return output

    async def _latest(self, series_id: str) -> dict | None:
        start = (datetime.now(UTC) - timedelta(days=370)).date().isoformat()
        try:
            response = await self.client.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": self.settings.fred_api_key,
                    "file_type": "json",
                    "observation_start": start,
                    "sort_order": "desc",
                    "limit": 2,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return None
        observations = [item for item in response.json().get("observations", []) if item.get("value") not in {".", None}]
        if not observations:
            return None
        current = float(observations[0]["value"])
        previous = float(observations[1]["value"]) if len(observations) > 1 else None
        return {
            "date": observations[0].get("date"),
            "value": current,
            "previous": previous,
            "change": None if previous is None else round(current - previous, 4),
        }
