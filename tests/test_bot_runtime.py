from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.handlers.start import command_start
from app.bot.keyboards.common import language_keyboard, main_menu
from app.bot.middlewares.db import DbUserMiddleware
from app.config import Settings
from app.db.models import Base
from app.db.session import make_engine
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.market_data.models import Candle
from app.services.visuals.cards import render_chart_card, render_news_card
from app.utils.telegram_messages import split_telegram_text


class FakeTelegramUser:
    id = 1001
    username = "tester"
    first_name = "Test"
    last_name = "User"


class FakeEvent:
    from_user = FakeTelegramUser()


class FakeUpdateEvent:
    from_user = None


class FakeMessage:
    def __init__(self) -> None:
        self.answers: list[tuple[str, object | None]] = []

    async def answer(self, text: str, reply_markup=None):
        self.answers.append((text, reply_markup))


@pytest.mark.asyncio
async def test_db_middleware_injects_language_and_user(tmp_path):
    settings = Settings(DATABASE_URL=f"sqlite+aiosqlite:///{tmp_path / 'bot.db'}")
    engine = make_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    middleware = DbUserMiddleware(session_factory, settings)
    seen = {}

    async def handler(event, data):
        seen.update(data)
        return "ok"

    result = await middleware(handler, FakeEvent(), {})
    assert result == "ok"
    assert seen["language"] == "uz"
    assert seen["db_user"].telegram_id == FakeTelegramUser.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_db_middleware_uses_aiogram_event_from_user(tmp_path):
    settings = Settings(DATABASE_URL=f"sqlite+aiosqlite:///{tmp_path / 'bot_update.db'}")
    engine = make_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    middleware = DbUserMiddleware(session_factory, settings)
    seen = {}

    async def handler(event, data):
        seen.update(data)
        return "ok"

    result = await middleware(handler, FakeUpdateEvent(), {"event_from_user": FakeTelegramUser()})
    assert result == "ok"
    assert seen["language"] == "uz"
    assert seen["settings"] is settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_start_handler_does_not_require_injected_language():
    message = FakeMessage()
    await command_start(message)
    assert len(message.answers) == 2
    assert message.answers[1][1] is not None


def test_keyboards_have_buttons():
    assert language_keyboard().inline_keyboard
    menu = main_menu("ru")
    button_texts = [button.text for row in menu.inline_keyboard for button in row]
    assert "📈 Анализ графика" in button_texts
    assert "Технический анализ" not in button_texts
    assert "🤖 Algo Trading" in button_texts


def test_openai_model_candidates_keep_gpt55_primary():
    settings = Settings(OPENAI_TEXT_MODEL="gpt-5.5", OPENAI_FALLBACK_MODELS="gpt-5.2,gpt-5")
    assert settings.openai_model_candidates(settings.openai_text_model) == ["gpt-5.5", "gpt-5.2", "gpt-5"]


def test_technical_analyzer_returns_report():
    candles = []
    base = 2000.0
    now = datetime.now(UTC)
    for i in range(260):
        close = base + i * 0.25 + ((i % 9) - 4) * 0.35
        candles.append(
            Candle(
                time=now + timedelta(minutes=i * 15),
                open=close - 0.4,
                high=close + 1.2,
                low=close - 1.1,
                close=close,
                volume=1000 + i,
            )
        )
    report = TechnicalAnalyzer().analyze("XAUUSD", candles, "15m")
    assert report.symbol == "XAUUSD"
    assert report.indicators["rsi14"] >= 0
    assert report.summary


def test_telegram_text_splitter_keeps_chunks_under_limit():
    chunks = split_telegram_text("A" * 8500, limit=3900)
    assert len(chunks) == 3
    assert all(len(chunk) <= 3900 for chunk in chunks)


def test_visual_cards_render_png_bytes():
    report = TechnicalAnalyzer().analyze("XAUUSD", _fake_candles(), "15m").to_dict()
    chart = render_chart_card(report, "uz")
    news = render_news_card(
        {
            "usd_bias": "bullish",
            "xauusd_bias": "bearish",
            "btc_bias": "neutral",
            "risk_mood": "mixed",
            "confidence": 61,
            "key_news": [{"title": "Fed policy expectations keep investors careful"}],
        },
        "en",
    )
    assert chart.startswith(b"\x89PNG")
    assert news.startswith(b"\x89PNG")


def _fake_candles() -> list[Candle]:
    candles = []
    base = 2000.0
    now = datetime.now(UTC)
    for i in range(260):
        close = base + i * 0.25 + ((i % 9) - 4) * 0.35
        candles.append(
            Candle(
                time=now + timedelta(minutes=i * 15),
                open=close - 0.4,
                high=close + 1.2,
                low=close - 1.1,
                close=close,
                volume=1000 + i,
            )
        )
    return candles
