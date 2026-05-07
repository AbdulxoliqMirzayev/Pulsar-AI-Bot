from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.common import main_menu
from app.config import Settings
from app.services.assistant.chat import PulsarChatAgent
from app.services.rag.market_context import MarketRAGContext
from app.utils.formatters import pulsar
from app.utils.telegram_messages import answer_long, safe_callback_answer, safe_chat_action


router = Router(name="chat")


@router.callback_query(F.data == "menu:agent")
async def agent_mode(callback: CallbackQuery, settings: Settings, language: str | None = None) -> None:
    await safe_callback_answer(callback)
    rag = MarketRAGContext(settings)
    try:
        context = await rag.brief()
    finally:
        await rag.close()
    if language == "ru":
        text = f"AI Agent mode активен.\nLive: {context}\nНапишите вопрос: XAUUSD, BTCUSD, DXY, риск, entry/SL/TP или новости."
    elif language == "en":
        text = f"AI Agent mode is active.\nLive: {context}\nAsk about XAUUSD, BTCUSD, DXY, risk, entry/SL/TP, or news."
    else:
        text = f"AI Agent mode aktiv.\nLive: {context}\nXAUUSD, BTCUSD, DXY, risk, entry/SL/TP yoki news haqida yozing."
    await callback.message.answer(pulsar(text), reply_markup=main_menu(language))


@router.message(F.text)
async def friendly_chat(message: Message, settings: Settings, language: str | None = None) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    await safe_chat_action(message, ChatAction.TYPING)
    market_context = None
    if _needs_market_context(text):
        rag = MarketRAGContext(settings)
        try:
            market_context = await rag.brief()
        finally:
            await rag.close()
    agent = PulsarChatAgent(settings)
    reply = await agent.reply(text, language, market_context)
    await answer_long(message, pulsar(reply), reply_markup=main_menu(language))


def _needs_market_context(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in ("xau", "gold", "oltin", "btc", "bitcoin", "dxy", "dollar", "narx", "price", "news", "yangilik"))
