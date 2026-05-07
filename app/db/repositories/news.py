from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NewsItem
from app.utils.deduplication import news_hash


class NewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_many(self, items: list[dict]) -> None:
        for item in items:
            payload = _json_ready(item)
            self.session.add(
                NewsItem(
                    source=item.get("source"),
                    source_type=item.get("source_type", "rss"),
                    title=item.get("title", ""),
                    description=item.get("description") or item.get("summary"),
                    url=item.get("url"),
                    published_at=item.get("published_at"),
                    related_instruments=item.get("related_instruments", []),
                    sentiment_label=item.get("sentiment_label"),
                    sentiment_score=item.get("sentiment_score"),
                    impact_score=item.get("impact_score"),
                    raw_payload=payload,
                    hash_key=news_hash(item.get("title", ""), item.get("url"), item.get("source")),
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
