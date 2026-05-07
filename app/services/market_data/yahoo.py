from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.services.market_data.models import Candle


YAHOO_SYMBOLS = {
    "XAUUSD": "GC=F",
    "GOLD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "DXY": "DX-Y.NYB",
}


class YahooChartClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, headers={"User-Agent": "Mozilla/5.0"})

    async def candles(self, symbol: str, interval: str = "15m", range_: str = "5d") -> list[Candle]:
        yahoo_symbol = YAHOO_SYMBOLS.get(symbol.upper())
        if not yahoo_symbol:
            return []
        response = await self.client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
            params={"range": range_, "interval": interval},
        )
        response.raise_for_status()
        result = (response.json().get("chart", {}).get("result") or [None])[0]
        if not result:
            return []
        timestamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        output: list[Candle] = []
        for idx, ts in enumerate(timestamps):
            try:
                open_ = quote["open"][idx]
                high = quote["high"][idx]
                low = quote["low"][idx]
                close = quote["close"][idx]
            except (KeyError, IndexError):
                continue
            if None in (open_, high, low, close):
                continue
            volume = 0
            if "volume" in quote and idx < len(quote["volume"]) and quote["volume"][idx] is not None:
                volume = float(quote["volume"][idx])
            output.append(
                Candle(
                    time=datetime.fromtimestamp(int(ts), tz=UTC),
                    open=float(open_),
                    high=float(high),
                    low=float(low),
                    close=float(close),
                    volume=volume,
                )
            )
        return output
