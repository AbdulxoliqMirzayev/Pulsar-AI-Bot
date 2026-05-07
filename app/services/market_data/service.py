from __future__ import annotations

import httpx

from app.config import Settings
from app.services.market_data.alpha_vantage import AlphaVantageClient
from app.services.market_data.binance import BinanceMarketDataClient
from app.services.market_data.coingecko import CoinGeckoClient
from app.services.market_data.mexc import MexcMarketDataClient
from app.services.market_data.models import Candle, MarketQuote
from app.services.market_data.yahoo import YahooChartClient


SYMBOL_ALIASES = {
    "BTC": "BTCUSDT",
    "BTCUSD": "BTCUSDT",
    "BTC/USD": "BTCUSDT",
    "XAU": "XAUUSD",
    "XAU/USD": "XAUUSD",
    "GOLD": "XAUUSD",
    "USDX": "DXY",
}


class MarketDataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.AsyncClient(timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        self.mexc = MexcMarketDataClient(settings, self.http)
        self.binance = BinanceMarketDataClient(self.http)
        self.coingecko = CoinGeckoClient(settings, self.http)
        self.alpha_vantage = AlphaVantageClient(settings, self.http)
        self.yahoo = YahooChartClient(self.http)

    async def close(self) -> None:
        await self.http.aclose()

    def normalize_symbol(self, symbol: str) -> str:
        return SYMBOL_ALIASES.get(symbol.upper().replace("/", ""), symbol.upper().replace("/", ""))

    async def candles(self, symbol: str, timeframe: str = "15m", limit: int = 240) -> list[Candle]:
        normalized = self.normalize_symbol(symbol)
        if normalized.endswith("USDT"):
            try:
                return await self.mexc.candles(normalized, timeframe=timeframe, limit=limit)
            except httpx.HTTPError:
                return await self.binance.candles(normalized, timeframe=timeframe, limit=limit)
        if normalized in {"XAUUSD", "GOLD", "EURUSD", "GBPUSD", "USDJPY", "DXY"}:
            if normalized == "XAUUSD":
                for proxy in ("XAUTUSDT", "PAXGUSDT"):
                    try:
                        return await self.binance.candles(proxy, timeframe=timeframe, limit=limit)
                    except httpx.HTTPError:
                        continue
            try:
                yahoo = await self.yahoo.candles(normalized, interval=timeframe, range_="5d")
                if yahoo:
                    return yahoo[-limit:]
            except httpx.HTTPError:
                pass
        if len(normalized) == 6 and normalized.endswith("USD"):
            return await self.alpha_vantage.fx_daily(normalized[:3], normalized[3:])
        return []

    async def quote(self, symbol: str) -> MarketQuote:
        normalized = self.normalize_symbol(symbol)
        if normalized.endswith("USDT"):
            try:
                return await self.mexc.quote(normalized)
            except httpx.HTTPError:
                return await self.binance.quote(normalized)
        if normalized == "XAUUSD":
            try:
                return await self.binance.quote("XAUTUSDT")
            except httpx.HTTPError:
                try:
                    return await self.binance.quote("PAXGUSDT")
                except httpx.HTTPError:
                    return await self.yahoo.quote("XAUUSD")
        if normalized in {"DXY", "EURUSD", "GBPUSD", "USDJPY"}:
            return await self.yahoo.quote(normalized)
        if len(normalized) == 6 and normalized.endswith("USD"):
            return await self.yahoo.quote(normalized)
        return MarketQuote(symbol=normalized, price=None)
