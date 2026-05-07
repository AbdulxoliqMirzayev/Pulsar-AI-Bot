from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketSnapshot


class MarketSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: dict) -> MarketSnapshot:
        snapshot = MarketSnapshot(**data)
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot
