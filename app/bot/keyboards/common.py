from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.i18n import t


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
            ]
        ]
    )


def main_menu(language: str | None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(language, "menu.vision"), callback_data="menu:vision"),
                InlineKeyboardButton(text=t(language, "menu.news"), callback_data="menu:news"),
            ],
            [
                InlineKeyboardButton(text=t(language, "menu.calendar"), callback_data="menu:calendar"),
                InlineKeyboardButton(text=t(language, "menu.journal"), callback_data="menu:journal"),
            ],
            [
                InlineKeyboardButton(text=t(language, "menu.algo"), callback_data="menu:algo"),
                InlineKeyboardButton(text=t(language, "menu.agent"), callback_data="menu:agent"),
            ],
            [InlineKeyboardButton(text=t(language, "menu.language"), callback_data="menu:language")],
        ]
    )
