from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.bot.keyboards.common import main_menu
from app.config import Settings
from app.services.assistant.chat import PulsarChatAgent
from app.utils.formatters import pulsar
from app.utils.telegram_messages import answer_long, safe_chat_action


router = Router(name="chat")


@router.message(F.text)
async def friendly_chat(message: Message, settings: Settings, language: str | None = None) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    await safe_chat_action(message, ChatAction.TYPING)
    agent = PulsarChatAgent(settings)
    reply = await agent.reply(text, language)
    await answer_long(message, pulsar(reply), reply_markup=main_menu(language))
