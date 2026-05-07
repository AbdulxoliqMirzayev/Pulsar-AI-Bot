from __future__ import annotations

import httpx

from app.config import Settings


COINGECKO_IDS = {
    "BTC": "bitcoin",
    "BTCUSDT": "bitcoin",
    "ETH": "ethereum",
    "ETHUSDT": "ethereum",
    "XAUT": "tether-gold",
    "XAUTUSDT": "tether-gold",
    "PAXG": "pax-gold",
    "PAXGUSDT": "pax-gold",
}


class CoinGeckoClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=15)

    async def simple_price(self, symbols: list[str], vs_currency: str = "usd") -> dict[str, dict]:
        ids = sorted({COINGECKO_IDS.get(symbol.upper(), symbol.lower()) for symbol in symbols})
        response = await self.client.get(
            f"{self.settings.coingecko_base_url.rstrip('/')}/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": vs_currency, "include_24hr_change": "true", "include_24hr_vol": "true"},
        )
        response.raise_for_status()
        return response.json()
