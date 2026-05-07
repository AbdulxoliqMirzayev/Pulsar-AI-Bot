from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.config import Settings
from app.services.market_data.models import Candle


class AlphaVantageClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=20)

    async def fx_daily(self, from_symbol: str, to_symbol: str = "USD", outputsize: str = "compact") -> list[Candle]:
        if not self.settings.alpha_vantage_api_key:
            return []
        response = await self.client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "FX_DAILY",
                "from_symbol": from_symbol.upper(),
                "to_symbol": to_symbol.upper(),
                "outputsize": outputsize,
                "apikey": self.settings.alpha_vantage_api_key,
            },
        )
        response.raise_for_status()
        data = response.json()
        series = data.get("Time Series FX (Daily)", {})
        candles: list[Candle] = []
        for key, value in series.items():
            candles.append(
                Candle(
                    time=datetime.fromisoformat(key).replace(tzinfo=UTC),
                    open=float(value["1. open"]),
                    high=float(value["2. high"]),
                    low=float(value["3. low"]),
                    close=float(value["4. close"]),
                    volume=0,
                )
            )
        return sorted(candles, key=lambda item: item.time or datetime.min.replace(tzinfo=UTC))
