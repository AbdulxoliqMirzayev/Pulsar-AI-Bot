from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import User
from app.utils.timezone import today_key, utc_now


class UserRepository:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_or_create(self, telegram_id: int, username: str | None, full_name: str | None) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        now = utc_now()
        if user:
            user.username = username
            user.full_name = full_name
            user.last_active_at = now
            user.is_admin = self.settings.is_admin(telegram_id)
            await self.session.commit()
            return user, False
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=self.settings.default_language,
            timezone=self.settings.default_timezone,
            is_admin=self.settings.is_admin(telegram_id),
            last_reset_date=today_key(self.settings.default_timezone),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user, True

    async def set_language(self, user: User, language: str) -> User:
        user.language = language
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_reminders(self, user: User, enabled: bool) -> User:
        user.session_reminders_enabled = enabled
        await self.session.commit()
        return user

    async def active_users(self) -> list[User]:
        rows = await self.session.scalars(select(User).where(User.is_blocked.is_(False)))
        return list(rows)


def reset_daily_counts_if_needed(user: User, timezone: str) -> None:
    today = today_key(timezone)
    if user.last_reset_date != today:
        user.daily_signal_count = 0
        user.daily_vision_count = 0
        user.daily_news_count = 0
        user.daily_risk_count = 0
        user.last_reset_date = today
