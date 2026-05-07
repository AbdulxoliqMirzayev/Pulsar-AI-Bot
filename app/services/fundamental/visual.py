from __future__ import annotations

import base64

from openai import AsyncOpenAI

from app.config import Settings
from app.services.fundamental.analyzer import FundamentalReport
from app.services.visuals.cards import render_news_card


class NewsImageGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate(self, report: FundamentalReport, language: str | None = "uz") -> tuple[bytes, str]:
        if self.client and self.settings.openai_text_active:
            image = await self._generate_with_openai(report, language)
            if image:
                return image, "openai"
        return render_news_card(report.to_dict(), language), "local"

    async def _generate_with_openai(self, report: FundamentalReport, language: str | None) -> bytes | None:
        prompt = self._prompt(report, language)
        last_error: Exception | None = None
        for model in self.settings.openai_model_candidates(self.settings.openai_text_model):
            try:
                response = await self.client.responses.create(
                    model=model,
                    input=prompt,
                    tools=[{"type": "image_generation", "size": "1024x1024", "quality": "low"}],
                )
                for output in response.output:
                    if getattr(output, "type", "") == "image_generation_call" and getattr(output, "result", None):
                        return base64.b64decode(output.result)
            except Exception as exc:
                last_error = exc
                continue
        if last_error:
            return None
        return None

    def _prompt(self, report: FundamentalReport, language: str | None) -> str:
        news_titles = [item.get("title", "") for item in report.key_news[:5]]
        mood = self._mood(report)
        return (
            "Create a professional square financial-market illustration for a Telegram trading bot named Pulsar AI. "
            "No logos of real companies, no tiny unreadable text, no profit promises. "
            "Use a cinematic trading desk, macro news screens, gold and dollar visual language, clean premium fintech style. "
            f"Market mood: {mood}. USD bias: {report.usd_bias}. XAUUSD bias: {report.xauusd_bias}. "
            f"BTC bias: {report.btc_bias}. Risk mood: {report.risk_mood}. Confidence: {report.confidence}%. "
            f"Top news context: {news_titles}. Language context: {language or 'uz'}."
        )

    def _mood(self, report: FundamentalReport) -> str:
        if "bull" in report.xauusd_bias:
            return "bullish gold, defensive macro bid, confident but risk-aware investors"
        if "bear" in report.xauusd_bias:
            return "bearish gold pressure, stronger dollar or yields, cautious investors"
        if report.risk_mood == "risk_off":
            return "risk-off, safe-haven demand, tense investor sentiment"
        if report.risk_mood == "risk_on":
            return "risk-on, optimistic investors, improving liquidity"
        return "mixed market, uncertain investors, neutral consolidation"
