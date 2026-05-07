from __future__ import annotations

import base64

from openai import AsyncOpenAI

from app.config import Settings


class ChartVisionAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def analyze(self, image_bytes: bytes, language: str = "uz", symbol: str = "XAUUSD") -> str:
        if not self.client or not self.settings.openai_vision_active:
            return self._no_model(language)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        prompt = (
            "You are Pulsar AI chart signal engine. Detect the trading pair and timeframe from the screenshot if visible. "
            "Return ONLY this compact Telegram signal format, in the requested language, under 900 characters:\n"
            "📌 Xulosa: exactly 5 words, include BUY or SELL or WAIT\n"
            "💱 Para: SYMBOL | ⏱ TF: TIMEFRAME\n"
            "🔴/🟢 Yo'nalish: SELL/BUY/WAIT\n"
            "🎯 Entry: price-zone or 'zona kelmaguncha limit'\n"
            "🛡 Stop Loss: price\n"
            "✅ Take Profit: price\n"
            "🧠 Sabab: one short sentence about resistance/support, liquidity, OB/FVG or structure\n"
            "⚠️ Bozor har daqiqada o'zgarishi mumkin.\n"
            "If the chart has not reached the zone, write that a limit order can be considered. "
            "Do not promise profit. Do not add long education. "
            f"Default symbol if not visible: {symbol}. Language: {language}."
        )
        last_error: Exception | None = None
        payload = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}"},
                ],
            }
        ]
        for model in self.settings.openai_model_candidates(self.settings.openai_vision_model):
            try:
                response = await self.client.responses.create(
                    model=model,
                    input=payload,
                    temperature=self.settings.openai_temperature,
                    max_output_tokens=min(self.settings.openai_max_tokens, 750),
                )
                return response.output_text.strip()
            except Exception as exc:
                last_error = exc
                try:
                    response = await self.client.responses.create(
                        model=model,
                        input=payload,
                        max_output_tokens=min(self.settings.openai_max_tokens, 750),
                    )
                    return response.output_text.strip()
                except Exception as retry_exc:
                    last_error = retry_exc
                    continue
        if language == "ru":
            return f"Не удалось выполнить GPT-анализ графика: {last_error}"
        if language == "en":
            return f"Chart GPT analysis failed: {last_error}"
        return f"Grafik GPT analizi bajarilmadi: {last_error}"

    def _no_model(self, language: str) -> str:
        if language == "ru":
            return "GPT-5.5 chart analysis не активен. Проверьте OPENAI_API_KEY и OPENAI_VISION_MODEL."
        if language == "en":
            return "GPT-5.5 chart analysis is not active. Check OPENAI_API_KEY and OPENAI_VISION_MODEL."
        return "GPT-5.5 grafik analizi aktiv emas. OPENAI_API_KEY va OPENAI_VISION_MODEL ni tekshiring."
