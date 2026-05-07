from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BrokerReferral


class BrokerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_update(self, broker_name: str, referral_url: str, description: str, created_by: int | None = None) -> BrokerReferral:
        active = list(await self.session.scalars(select(BrokerReferral).where(BrokerReferral.is_active.is_(True))))
        for item in active:
            item.is_active = False
        broker = BrokerReferral(broker_name=broker_name, referral_url=referral_url, description=description, created_by=created_by)
        self.session.add(broker)
        await self.session.commit()
        await self.session.refresh(broker)
        return broker

    async def active(self) -> list[BrokerReferral]:
        return list(await self.session.scalars(select(BrokerReferral).where(BrokerReferral.is_active.is_(True))))
