from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.config import Settings
from app.services.market_data.models import Candle, MarketQuote


MEXC_INTERVALS = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "60m",
    "4h": "4h",
    "1d": "1d",
}


class MexcMarketDataClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=15)

    async def candles(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> list[Candle]:
        interval = MEXC_INTERVALS.get(timeframe, timeframe)
        response = await self.client.get(
            f"{self.settings.mexc_base_url.rstrip('/')}/api/v3/klines",
            params={"symbol": symbol.upper(), "interval": interval, "limit": min(limit, 1000)},
        )
        response.raise_for_status()
        output: list[Candle] = []
        for row in response.json():
            output.append(
                Candle(
                    time=datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5] or 0),
                )
            )
        return output

    async def quote(self, symbol: str) -> MarketQuote:
        response = await self.client.get(
            f"{self.settings.mexc_base_url.rstrip('/')}/api/v3/ticker/24hr",
            params={"symbol": symbol.upper()},
        )
        response.raise_for_status()
        data = response.json()
        return MarketQuote(
            symbol=symbol.upper(),
            price=float(data["lastPrice"]) if data.get("lastPrice") else None,
            change_percent=float(data["priceChangePercent"]) if data.get("priceChangePercent") else None,
            volume_24h=float(data["volume"]) if data.get("volume") else None,
            high_24h=float(data["highPrice"]) if data.get("highPrice") else None,
            low_24h=float(data["lowPrice"]) if data.get("lowPrice") else None,
            provider="mexc",
        )
