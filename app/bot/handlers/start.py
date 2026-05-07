from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import language_keyboard, main_menu
from app.config import Settings
from app.db.models import User
from app.db.repositories.users import UserRepository
from app.utils.i18n import pt, t


router = Router(name="start")


@router.message(CommandStart())
async def command_start(message: Message, language: str) -> None:
    await message.answer(pt(language, "start.welcome"))
    await message.answer(t(language, "start.choose_language"), reply_markup=language_keyboard())


@router.message(Command("menu"))
async def command_menu(message: Message, language: str) -> None:
    await message.answer(pt(language, "menu.title"), reply_markup=main_menu(language))


@router.callback_query(F.data == "menu:language")
async def choose_language(callback: CallbackQuery, language: str) -> None:
    await callback.message.answer(t(language, "start.choose_language"), reply_markup=language_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession, db_user: User, settings: Settings) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in {"uz", "ru", "en"}:
        language = settings.default_language
    await UserRepository(session, settings).set_language(db_user, language)
    await callback.message.answer(pt(language, "start.saved"))
    await callback.message.answer(pt(language, "menu.title"), reply_markup=main_menu(language))
    await callback.answer()
