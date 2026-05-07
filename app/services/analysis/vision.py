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
            "Analyze this trading chart professionally. Focus on market structure, support/resistance, key levels, "
            "order blocks, fair value gaps, liquidity pools, volume context if visible, and a short risk plan. "
            "Do not promise profit and do not give overconfident financial advice. "
            f"Symbol: {symbol}. Language: {language}."
        )
        try:
            response = await self.client.responses.create(
                model=self.settings.openai_vision_model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}"},
                        ],
                    }
                ],
                temperature=self.settings.openai_temperature,
                max_output_tokens=self.settings.openai_max_tokens,
            )
            return response.output_text.strip()
        except Exception as exc:
            if language == "ru":
                return f"Не удалось выполнить GPT-анализ графика: {exc}"
            if language == "en":
                return f"Chart GPT analysis failed: {exc}"
            return f"Grafik GPT analizi bajarilmadi: {exc}"

    def _no_model(self, language: str) -> str:
        if language == "ru":
            return "GPT-5.5 chart analysis не активен. Проверьте OPENAI_API_KEY и OPENAI_VISION_MODEL."
        if language == "en":
            return "GPT-5.5 chart analysis is not active. Check OPENAI_API_KEY and OPENAI_VISION_MODEL."
        return "GPT-5.5 grafik analizi aktiv emas. OPENAI_API_KEY va OPENAI_VISION_MODEL ni tekshiring."
