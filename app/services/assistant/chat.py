from __future__ import annotations

from openai import AsyncOpenAI

from app.config import Settings


class PulsarChatAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def reply(self, user_text: str, language: str | None = "uz", market_context: str | None = None) -> str:
        if not self.client or not self.settings.openai_text_active:
            return self._fallback(user_text, language, market_context)
        prompt = (
            "You are Pulsar AI, a warm but professional trading and productivity assistant inside Telegram. "
            "Reply like a capable human analyst: friendly, concise, practical, and never overconfident. "
            "You can help with trading calculations, risk planning, journal reflection, market context, MT5 setup, and general questions. "
            "For trading, always mention risk and uncertainty when relevant. Do not promise profit. "
            "If market context is provided, use it as retrieved live context (RAG) and keep the answer short. "
            f"Answer language: {language or 'uz'}.\nMarket context: {market_context or 'none'}\nUser: {user_text}"
        )
        for model in self.settings.openai_model_candidates(self.settings.openai_text_model):
            try:
                response = await self.client.responses.create(
                    model=model,
                    input=prompt,
                    temperature=self.settings.openai_temperature,
                    max_output_tokens=950,
                )
                text = response.output_text.strip()
                if text:
                    return text
            except Exception:
                try:
                    response = await self.client.responses.create(model=model, input=prompt, max_output_tokens=950)
                    text = response.output_text.strip()
                    if text:
                        return text
                except Exception:
                    continue
        return self._fallback(user_text, language, market_context)

    def _fallback(self, user_text: str, language: str | None, market_context: str | None = None) -> str:
        if market_context:
            if language == "ru":
                return f"Live context: {market_context}\nНапишите, какой инструмент разобрать глубже."
            if language == "en":
                return f"Live context: {market_context}\nSend the instrument you want me to break down deeper."
            return f"Live context: {market_context}\nQaysi instrumentni chuqurroq ko'rib chiqamiz?"
        if language == "ru":
            return (
                "Я рядом. Сейчас GPT-модуль недоступен, но я всё равно помогу: напишите символ, риск, депозит или вопрос, "
                "и я разберу это максимально аккуратно. Для сделок держим риск под контролем и не входим без плана."
            )
        if language == "en":
            return (
                "I am here with you. The GPT module is not active right now, but I can still help: send the symbol, risk, "
                "balance, or your question, and we will structure it carefully. For trades, risk comes first."
            )
        return (
            "Men yoningizdaman. Hozir GPT moduli aktiv bo'lmasa ham yordam beraman: symbol, risk, depozit yoki savolingizni yozing, "
            "birga tartibli hisoblaymiz. Savdoda birinchi navbatda risk va reja."
        )
