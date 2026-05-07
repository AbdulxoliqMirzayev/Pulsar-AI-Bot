from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.repositories.users import UserRepository, reset_daily_counts_if_needed


class DbUserMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            data["settings"] = self.settings
            telegram_user = getattr(event, "from_user", None) or data.get("event_from_user")
            if telegram_user is None and hasattr(event, "message") and getattr(event, "message"):
                telegram_user = getattr(event.message, "from_user", None)
            if telegram_user is None and hasattr(event, "callback_query") and getattr(event, "callback_query"):
                telegram_user = getattr(event.callback_query, "from_user", None)
            if telegram_user:
                repo = UserRepository(session, self.settings)
                full_name = " ".join(part for part in [telegram_user.first_name, telegram_user.last_name] if part)
                user, _ = await repo.get_or_create(telegram_user.id, telegram_user.username, full_name or None)
                reset_daily_counts_if_needed(user, user.timezone or self.settings.default_timezone)
                data["db_user"] = user
                data["language"] = user.language or self.settings.default_language
            else:
                data["language"] = self.settings.default_language
            result = await handler(event, data)
            await session.commit()
            return result
