from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.config import Settings
from app.services.fundamental.models import NewsEvent
from app.utils.deduplication import deduplicate_news


DEFAULT_RSS_FEEDS = {
    "FXStreet": "https://www.fxstreet.com/rss/news",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
}


class NewsClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def fetch(self, query: str = "gold OR dollar OR fed OR inflation OR bitcoin", limit: int | None = None) -> list[NewsEvent]:
        limit = limit or self.settings.news_fetch_limit
        items: list[dict] = []
        for source, url in DEFAULT_RSS_FEEDS.items():
            items.extend(await self._rss(source, url))
        if self.settings.newsapi_enable and self.settings.newsapi_key:
            items.extend(await self._newsapi(query))
        if self.settings.crypto_panic_enable and self.settings.crypto_panic_api_key:
            items.extend(await self._cryptopanic())
        deduped = deduplicate_news(items)
        events = [self._to_event(item) for item in deduped]
        return sorted(events, key=lambda event: event.published_at or datetime.min.replace(tzinfo=UTC), reverse=True)[:limit]

    async def _rss(self, source: str, url: str) -> list[dict]:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        parsed = feedparser.parse(response.text)
        output: list[dict] = []
        for entry in parsed.entries[: self.settings.news_fetch_limit]:
            published = self._parse_date(getattr(entry, "published", None) or getattr(entry, "updated", None))
            if published and published < datetime.now(UTC) - timedelta(hours=max(self.settings.news_lookback_hours, 1) * 6):
                continue
            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "")
            output.append(
                {
                    "source": source,
                    "source_type": "rss",
                    "title": title,
                    "description": summary,
                    "url": getattr(entry, "link", None),
                    "published_at": published,
                    "related_instruments": self._related(title + " " + summary),
                }
            )
        return output

    async def _newsapi(self, query: str) -> list[dict]:
        try:
            response = await self.client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(self.settings.news_fetch_limit, 100),
                    "apiKey": self.settings.newsapi_key,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        output = []
        for item in response.json().get("articles", []):
            text = f"{item.get('title') or ''} {item.get('description') or ''}"
            output.append(
                {
                    "source": (item.get("source") or {}).get("name") or "NewsAPI",
                    "source_type": "newsapi",
                    "title": item.get("title") or "",
                    "description": item.get("description"),
                    "url": item.get("url"),
                    "published_at": self._parse_date(item.get("publishedAt")),
                    "related_instruments": self._related(text),
                }
            )
        return output

    async def _cryptopanic(self) -> list[dict]:
        try:
            response = await self.client.get(
                "https://cryptopanic.com/api/v1/posts/",
                params={"auth_token": self.settings.crypto_panic_api_key, "public": "true", "kind": "news"},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        output = []
        for item in response.json().get("results", [])[: self.settings.news_fetch_limit]:
            output.append(
                {
                    "source": "CryptoPanic",
                    "source_type": "cryptopanic",
                    "title": item.get("title") or "",
                    "description": item.get("metadata", {}).get("description"),
                    "url": item.get("url"),
                    "published_at": self._parse_date(item.get("published_at")),
                    "related_instruments": ["BTCUSDT"],
                }
            )
        return output

    def _to_event(self, item: dict) -> NewsEvent:
        text = f"{item.get('title') or ''} {item.get('description') or ''}"
        sentiment, score = self._sentiment(text)
        return NewsEvent(
            title=item.get("title", ""),
            source=item.get("source") or "unknown",
            url=item.get("url"),
            published_at=item.get("published_at"),
            summary=item.get("description"),
            sentiment=sentiment,
            impact_score=score,
            related_instruments=item.get("related_instruments") or self._related(text),
        )

    def _sentiment(self, text: str) -> tuple[str, float]:
        lower = text.lower()
        positive = sum(word in lower for word in ("beat", "strong", "hawkish", "inflation hot", "yields rise", "risk-on", "rally", "surge"))
        negative = sum(word in lower for word in ("miss", "weak", "dovish", "recession", "cuts", "risk-off", "drop", "selloff"))
        score = float(positive - negative)
        if score > 0:
            return "bullish", min(5.0, score)
        if score < 0:
            return "bearish", max(-5.0, score)
        return "neutral", 0.0

    def _related(self, text: str) -> list[str]:
        lower = text.lower()
        instruments: list[str] = []
        if any(word in lower for word in ("gold", "xau", "xagusd", "silver")):
            instruments.append("XAUUSD")
        if any(word in lower for word in ("bitcoin", "btc", "crypto", "etf")):
            instruments.append("BTCUSDT")
        if any(word in lower for word in ("dollar", "fed", "fomc", "treasury", "inflation", "nfp", "cpi")):
            instruments.append("DXY")
            instruments.append("XAUUSD")
        return sorted(set(instruments or ["DXY"]))

    def _parse_date(self, raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
