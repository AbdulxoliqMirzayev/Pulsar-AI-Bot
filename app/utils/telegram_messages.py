from __future__ import annotations

from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

TELEGRAM_TEXT_LIMIT = 3900


def split_telegram_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current = line
    if current:
        chunks.append(current)
    return chunks


async def answer_long(message: Message, text: str, reply_markup=None) -> None:
    chunks = split_telegram_text(text)
    if not chunks:
        return
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)


async def safe_callback_answer(callback: CallbackQuery, text: str | None = None) -> None:
    try:
        await callback.answer(text=text)
    except TelegramBadRequest as exc:
        if "query is too old" not in str(exc) and "query ID is invalid" not in str(exc):
            raise


async def safe_chat_action(message: Message, action: ChatAction) -> None:
    try:
        await message.bot.send_chat_action(message.chat.id, action)
    except Exception:
        return
