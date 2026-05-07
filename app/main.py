from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.handlers import analysis, chat, start
from app.bot.middlewares.db import DbUserMiddleware
from app.config import get_settings
from app.db.models import Base
from app.db.session import make_engine
from app.logging_config import setup_logging


async def run_bot() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env ichida ko'rsatilmagan.")
    if settings.resolved_database_url.startswith("sqlite"):
        Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = make_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    bot = Bot(settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(settings=settings)
    dp["settings"] = settings
    dp.update.middleware(DbUserMiddleware(session_factory, settings))
    dp.include_router(start.router)
    dp.include_router(analysis.router)
    dp.include_router(chat.router)
    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
