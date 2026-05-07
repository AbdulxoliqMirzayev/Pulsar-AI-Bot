from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminAction, User


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stats(self) -> dict:
        total = int(await self.session.scalar(select(func.count(User.id))) or 0)
        active = int(await self.session.scalar(select(func.count(User.id)).where(User.is_blocked.is_(False))) or 0)
        blocked = int(await self.session.scalar(select(func.count(User.id)).where(User.is_blocked.is_(True))) or 0)
        return {"users_total": total, "active_24h": active, "blocked": blocked}

    async def log(self, admin_id: int, action_type: str, details: dict | None = None) -> None:
        self.session.add(AdminAction(admin_id=admin_id, action_type=action_type, details=details or {}))
        await self.session.commit()
