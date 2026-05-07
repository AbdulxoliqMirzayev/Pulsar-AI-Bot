from __future__ import annotations

from dataclasses import asdict, dataclass

import httpx
from openai import AsyncOpenAI

from app.config import Settings
from app.services.fundamental.calendar import EconomicCalendarClient
from app.services.fundamental.fred import FredClient
from app.services.fundamental.models import CalendarEvent, NewsEvent
from app.services.fundamental.news import NewsClient


@dataclass(slots=True)
class FundamentalReport:
    usd_bias: str
    xauusd_bias: str
    btc_bias: str
    risk_mood: str
    confidence: int
    key_events: list[dict]
    key_news: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class FundamentalAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = httpx.AsyncClient(timeout=25, follow_redirects=True)
        self.news = NewsClient(settings, self.http)
        self.calendar = EconomicCalendarClient(settings, self.http)
        self.fred = FredClient(settings, self.http)
        self.openai = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def close(self) -> None:
        await self.http.aclose()

    async def analyze_now(self, language: str = "uz") -> FundamentalReport:
        news_items = await self.news.fetch()
        calendar_events = await self.calendar.upcoming_usd_events()
        macro = await self.fred.latest_macro_snapshot()
        scores = self._score(news_items, calendar_events)
        self._apply_macro(scores, macro)
        summary = self._deterministic_summary(scores, news_items, calendar_events, language)
        if self.openai and self.settings.openai_text_active:
            summary = await self._ai_summary(scores, news_items[:8], calendar_events[:8], language, summary, macro)
        return FundamentalReport(
            usd_bias=self._label(scores["usd"]),
            xauusd_bias=self._label(scores["xau"]),
            btc_bias=self._label(scores["btc"]),
            risk_mood=self._risk_label(scores["risk"]),
            confidence=min(92, max(35, int(abs(scores["usd"]) * 12 + abs(scores["xau"]) * 10 + 45))),
            key_events=[event.to_dict() for event in calendar_events[:8]],
            key_news=[event.to_dict() for event in news_items[:10]],
            summary=summary,
        )

    def _score(self, news_items: list[NewsEvent], calendar_events: list[CalendarEvent]) -> dict[str, float]:
        score = {"usd": 0.0, "xau": 0.0, "btc": 0.0, "risk": 0.0}
        for item in news_items[:25]:
            text = f"{item.title} {item.summary or ''}".lower()
            impact = max(abs(item.impact_score), 1.0)
            if any(word in text for word in ("fed", "fomc", "rate", "yield", "treasury", "inflation", "cpi", "nfp")):
                if any(word in text for word in ("hawkish", "higher", "hot", "strong", "beat", "yields rise")):
                    score["usd"] += impact
                    score["xau"] -= impact * 0.8
                if any(word in text for word in ("dovish", "cut", "weak", "miss", "cooling", "recession")):
                    score["usd"] -= impact
                    score["xau"] += impact * 0.9
            if any(word in text for word in ("risk-off", "war", "geopolitical", "banking stress", "selloff")):
                score["risk"] -= impact
                score["xau"] += impact * 0.7
                score["btc"] -= impact * 0.5
            if any(word in text for word in ("risk-on", "rally", "etf inflows", "liquidity", "stocks rise")):
                score["risk"] += impact
                score["btc"] += impact * 0.7
            if "bitcoin" in text or "btc" in text or "crypto" in text:
                score["btc"] += item.impact_score
        for event in calendar_events[:12]:
            surprise = self._event_surprise(event)
            if surprise is None:
                continue
            name = event.event_name.lower()
            weight = 2.0 if str(event.impact).lower() in {"3", "high"} else 1.2
            if any(word in name for word in ("cpi", "inflation", "payroll", "employment", "jobs", "retail", "gdp", "pmi", "fed")):
                score["usd"] += surprise * weight
                score["xau"] -= surprise * weight * 0.8
                score["btc"] -= max(surprise, 0) * 0.3
        return score

    def _apply_macro(self, score: dict[str, float], macro: dict[str, dict]) -> None:
        ten_year = macro.get("DGS10", {}).get("change")
        fed_funds = macro.get("DFF", {}).get("change")
        unemployment = macro.get("UNRATE", {}).get("change")
        if ten_year is not None:
            score["usd"] += max(-1.5, min(1.5, ten_year * 4))
            score["xau"] -= max(-1.5, min(1.5, ten_year * 3))
        if fed_funds is not None:
            score["usd"] += max(-1.0, min(1.0, fed_funds * 4))
        if unemployment is not None:
            score["usd"] -= max(-1.0, min(1.0, unemployment * 2))
            score["risk"] -= max(-1.0, min(1.0, unemployment))

    def _event_surprise(self, event: CalendarEvent) -> float | None:
        actual = self._number(event.actual)
        forecast = self._number(event.forecast)
        if actual is None or forecast is None:
            return None
        if forecast == 0:
            return 0
        raw = (actual - forecast) / abs(forecast)
        if any(word in event.event_name.lower() for word in ("unemployment", "jobless claims")):
            raw *= -1
        return max(-2.0, min(2.0, raw * 10))

    def _number(self, value: str | None) -> float | None:
        if not value:
            return None
        cleaned = value.replace("%", "").replace(",", "").replace("K", "000").replace("M", "000000").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None

    def _label(self, value: float) -> str:
        if value >= 4:
            return "strong_bullish"
        if value >= 1:
            return "bullish"
        if value <= -4:
            return "strong_bearish"
        if value <= -1:
            return "bearish"
        return "neutral"

    def _risk_label(self, value: float) -> str:
        if value >= 2:
            return "risk_on"
        if value <= -2:
            return "risk_off"
        return "mixed"

    def _deterministic_summary(self, scores: dict[str, float], news_items: list[NewsEvent], events: list[CalendarEvent], language: str) -> str:
        top_news = "; ".join(item.title for item in news_items[:3]) or "no fresh high-impact news"
        top_events = "; ".join(event.event_name for event in events[:3]) or "no high-impact USD events"
        if language == "ru":
            return (
                f"Фундаментальный фон: USD {self._label(scores['usd'])}, XAUUSD {self._label(scores['xau'])}, "
                f"BTC {self._label(scores['btc'])}, риск {self._risk_label(scores['risk'])}. "
                f"Главные новости: {top_news}. Календарь: {top_events}."
            )
        if language == "en":
            return (
                f"Fundamental backdrop: USD {self._label(scores['usd'])}, XAUUSD {self._label(scores['xau'])}, "
                f"BTC {self._label(scores['btc'])}, risk mood {self._risk_label(scores['risk'])}. "
                f"Top news: {top_news}. Calendar: {top_events}."
            )
        return (
            f"Fundamental holat: USD {self._label(scores['usd'])}, XAUUSD {self._label(scores['xau'])}, "
            f"BTC {self._label(scores['btc'])}, risk mood {self._risk_label(scores['risk'])}. "
            f"Asosiy news: {top_news}. Kalendar: {top_events}."
        )

    async def _ai_summary(
        self,
        scores: dict[str, float],
        news_items: list[NewsEvent],
        events: list[CalendarEvent],
        language: str,
        fallback: str,
        macro: dict[str, dict] | None = None,
    ) -> str:
        if not self.openai:
            return fallback
        prompt = (
            "You are a professional macro/FX analyst. Write a concise Telegram-ready market note in the requested language. "
            "Focus on USD and XAUUSD impact, mention uncertainty, no financial advice. "
            f"Language: {language}\nScores: {scores}\n"
            f"News: {[item.to_dict() for item in news_items]}\nCalendar: {[item.to_dict() for item in events]}\nMacro: {macro or {}}"
        )
        try:
            response = await self.openai.responses.create(
                model=self.settings.openai_text_model,
                input=prompt,
                temperature=self.settings.openai_temperature,
                max_output_tokens=900,
            )
            return response.output_text.strip() or fallback
        except Exception:
            return fallback
