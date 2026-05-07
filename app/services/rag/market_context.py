from __future__ import annotations

from app.config import Settings
from app.services.market_data.models import MarketQuote
from app.services.market_data.service import MarketDataService
from app.utils.formatters import price


CORE_SYMBOLS = ("XAUUSD", "BTCUSD", "DXY")


class MarketRAGContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.market = MarketDataService(settings)

    async def close(self) -> None:
        await self.market.close()

    async def live_quotes(self, symbols: tuple[str, ...] = CORE_SYMBOLS) -> list[dict]:
        output: list[dict] = []
        for symbol in symbols:
            try:
                quote = await self.market.quote(symbol)
                output.append(_quote_dict(symbol, quote))
            except Exception:
                output.append({"symbol": symbol, "price": None, "change_percent": None, "provider": "unavailable"})
        return output

    async def brief(self) -> str:
        quotes = await self.live_quotes()
        parts = []
        for quote in quotes:
            if quote["price"] is None:
                parts.append(f"{quote['symbol']}: n/a")
                continue
            change = quote["change_percent"]
            change_text = "" if change is None else f" ({change:+.2f}%)"
            parts.append(f"{quote['symbol']}: {price(quote['price'])}{change_text}")
        return " | ".join(parts)


def _quote_dict(requested: str, quote: MarketQuote) -> dict:
    return {
        "symbol": requested,
        "provider_symbol": quote.symbol,
        "price": quote.price,
        "change_percent": quote.change_percent,
        "high_24h": quote.high_24h,
        "low_24h": quote.low_24h,
        "provider": quote.provider,
    }
