from __future__ import annotations

import re
from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import main_menu
from app.config import Settings
from app.db.models import User
from app.db.repositories.calendar import CalendarRepository
from app.db.repositories.journal import TradingJournalRepository
from app.db.repositories.market_snapshots import MarketSnapshotRepository
from app.db.repositories.news import NewsRepository
from app.services.analysis.technical import TechnicalAnalyzer
from app.services.analysis.vision import ChartVisionAnalyzer
from app.services.fundamental.analyzer import FundamentalAnalyzer
from app.services.fundamental.visual import NewsImageGenerator
from app.services.market_data.service import MarketDataService
from app.services.rag.market_context import MarketRAGContext
from app.services.visuals.cards import render_chart_card
from app.utils.formatters import h, price
from app.utils.i18n import pt, t
from app.utils.telegram_messages import answer_long, safe_callback_answer, safe_chat_action
from app.utils.telegram_files import download_file_bytes


router = Router(name="analysis")


@router.callback_query(F.data == "menu:technical")
async def technical(callback: CallbackQuery, settings: Settings, language: str | None = None, session: AsyncSession | None = None, db_user: User | None = None) -> None:
    await chart_analysis(callback, settings, language, session, db_user)


@router.callback_query(F.data == "menu:vision")
async def chart_analysis(callback: CallbackQuery, settings: Settings, language: str | None = None, session: AsyncSession | None = None, db_user: User | None = None) -> None:
    await safe_callback_answer(callback)
    await callback.message.edit_text(pt(language, "analysis.chart_loading"))
    await safe_chat_action(callback.message, ChatAction.UPLOAD_PHOTO)
    service = MarketDataService(settings)
    try:
        symbol = settings.technical_default_symbol
        candles = await service.candles(symbol, "15m", 240)
        if not candles:
            await callback.message.answer(pt(language, "analysis.no_data"), reply_markup=main_menu(language))
            return
        report = TechnicalAnalyzer().analyze(symbol, candles, "15m")
        if session is not None:
            await MarketSnapshotRepository(session).create(
                {
                    "symbol": report.symbol,
                    "provider": "mexc",
                    "market_type": "spot",
                    "price": report.price,
                    "timeframe": "15m",
                    "candles_json": [
                        {
                            "time": candle.time.isoformat() if candle.time else None,
                            "open": candle.open,
                            "high": candle.high,
                            "low": candle.low,
                            "close": candle.close,
                            "volume": candle.volume,
                        }
                        for candle in candles[-50:]
                    ],
                    "indicators_json": report.indicators,
                    "technical_summary": report.summary,
                }
            )
        card = render_chart_card(report.to_dict(), language)
        await callback.message.answer_photo(
            BufferedInputFile(card, filename=f"{report.symbol.lower()}_chart.png"),
            caption=_short_chart_caption(report.to_dict(), language),
        )
        await answer_long(callback.message, _format_chart(report.to_dict(), language), reply_markup=main_menu(language))
        await callback.message.answer(pt(language, "analysis.vision_prompt"))
    except Exception as exc:
        await callback.message.answer(f"{pt(language, 'errors.generic')}\n<code>{h(exc)}</code>", reply_markup=main_menu(language))
    finally:
        await service.close()


@router.callback_query(F.data == "menu:news")
async def news(callback: CallbackQuery, settings: Settings, language: str | None = None, session: AsyncSession | None = None) -> None:
    await safe_callback_answer(callback)
    await callback.message.edit_text(pt(language, "analysis.news_loading"))
    await safe_chat_action(callback.message, ChatAction.UPLOAD_PHOTO)
    analyzer = FundamentalAnalyzer(settings)
    image_generator = NewsImageGenerator(settings)
    try:
        report = await analyzer.analyze_now(language)
        if session is not None:
            await NewsRepository(session).save_many(report.key_news)
            await CalendarRepository(session).save_many(report.key_events)
        image, source = await image_generator.generate(report, language)
        prices = await _live_prices(settings)
        report_dict = report.to_dict()
        report_dict["market_prices"] = prices
        await callback.message.answer_photo(
            BufferedInputFile(image, filename="pulsar_news.png"),
            caption=_short_news_caption(report_dict, language, source),
        )
        await callback.message.answer(_format_fundamental(report_dict, language), reply_markup=main_menu(language))
    except Exception as exc:
        await callback.message.answer(f"{pt(language, 'errors.generic')}\n<code>{h(exc)}</code>", reply_markup=main_menu(language))
    finally:
        await analyzer.close()


@router.callback_query(F.data == "menu:calendar")
async def calendar(callback: CallbackQuery, settings: Settings, language: str | None = None) -> None:
    await safe_callback_answer(callback)
    analyzer = FundamentalAnalyzer(settings)
    try:
        events = await analyzer.calendar.upcoming_usd_events()
        lines = [f"<b>{h(t(language, 'analysis.calendar_title'))}</b>"]
        for event in events[:10]:
            time_text = event.event_time_utc.strftime("%Y-%m-%d %H:%M UTC") if event.event_time_utc else "TBA"
            lines.append(
                f"{h(time_text)} | <b>{h(event.event_name)}</b> | {h(event.impact)} | A:{h(event.actual)} F:{h(event.forecast)} P:{h(event.previous)}"
            )
        await answer_long(callback.message, "\n".join(lines), reply_markup=main_menu(language))
    finally:
        await analyzer.close()


@router.message(F.photo)
async def vision_photo(message: Message, settings: Settings, language: str | None = None) -> None:
    await safe_chat_action(message, ChatAction.TYPING)
    photo = message.photo[-1]
    image = await download_file_bytes(message.bot, photo.file_id)
    analyzer = ChartVisionAnalyzer(settings)
    text = h(await analyzer.analyze(image, language=language, symbol=settings.technical_default_symbol))
    service = MarketDataService(settings)
    try:
        symbol = _detect_symbol(text) or settings.technical_default_symbol
        quote = await service.quote(symbol)
        if quote.price is not None:
            text = f"{text}\n📡 Real-time: {h(symbol)} {price(quote.price)}"
    except Exception:
        pass
    finally:
        await service.close()
    await answer_long(message, text, reply_markup=main_menu(language))


@router.callback_query(F.data == "menu:journal")
async def journal(callback: CallbackQuery, language: str | None = None, session: AsyncSession | None = None, db_user: User | None = None) -> None:
    await safe_callback_answer(callback)
    if session is None or db_user is None:
        await callback.message.answer(pt(language, "errors.generic"), reply_markup=main_menu(language))
        return
    repo = TradingJournalRepository(session)
    stats = await repo.stats(db_user.id)
    history = await repo.history(db_user.id, 5)
    lines = [
        f"<b>{h(t(language, 'journal.stats'))}</b>",
        f"Total: {stats['total']} | Closed: {stats['closed']} | Win-rate: {stats['win_rate']}% | P/L: {stats['total_pl']} | Avg RR: {stats['avg_rr']}",
    ]
    if not history:
        lines.append(t(language, "journal.empty"))
    for item in history:
        lines.append(f"#{item.id} {h(item.symbol)} {h(item.direction)} {h(item.result)} RR {item.rr or '-'} P/L {item.profit_loss or '-'}")
    await answer_long(callback.message, "\n".join(lines), reply_markup=main_menu(language))


@router.callback_query(F.data == "menu:algo")
async def algo(callback: CallbackQuery, language: str | None = None) -> None:
    await safe_callback_answer(callback)
    await answer_long(callback.message, f"<b>{h(t(language, 'algo.title'))}</b>\n{h(t(language, 'algo.text'))}", reply_markup=main_menu(language))
    ea_path = Path("mql5/AlgoTradingBot_v1.mq5")
    if ea_path.exists():
        await callback.message.answer_document(
            FSInputFile(ea_path),
            caption="MT5 ga ulash uchun asosiy EA fayl. MetaEditor ichida compile qiling.",
        )


def _format_chart(report: dict, language: str | None) -> str:
    indicators = report["indicators"]
    strategies = report["strategies"][:6]
    lines = [
        f"<b>{h(t(language, 'analysis.technical_title'))}: {h(report['symbol'])}</b>",
        f"Price: <b>{price(report['price'])}</b> | Bias: <b>{h(report['bias'])}</b> | Confidence: {report['confidence']}%",
        f"RSI: {indicators['rsi14']} | MACD hist: {indicators['macd_histogram']} | ATR: {price(indicators['atr14'])} | Vol: {indicators['volume_ratio']}x",
        f"Structure: {h(report['market_structure']['trend'])} | BOS: {h(report['market_structure']['bos'])} | CHoCH: {h(report['market_structure']['choch'])}",
        "",
        h(report["summary"]),
        "",
        "<b>Confluence</b>",
    ]
    for item in strategies:
        lines.append(f"+ {h(item['name'])}: {h(item['direction'])} ({item['score']})")
    return "\n".join(lines)


def _short_chart_caption(report: dict, language: str | None) -> str:
    return (
        f"<b>{h(t(language, 'analysis.technical_title'))}</b>\n"
        f"{h(report['symbol'])} | {price(report['price'])} | {h(report['bias'])} | {report['confidence']}%"
    )


def _format_fundamental(report: dict, language: str) -> str:
    prices = _format_prices(report.get("market_prices") or [])
    top_news = report["key_news"][:3]
    lines = [
        f"<b>🗞 {h(t(language, 'analysis.fundamental_title'))}</b>",
        f"📡 {h(prices)}",
        f"USD: <b>{h(report['usd_bias'])}</b> | XAUUSD: <b>{h(report['xauusd_bias'])}</b> | BTC: <b>{h(report['btc_bias'])}</b>",
        f"Risk: {h(report['risk_mood'])} | Ishonch: {report['confidence']}%",
        f"🧠 {h(_trim(report['summary'], 520))}",
    ]
    for item in top_news:
        lines.append(f"• {h(_trim(item['title'], 105))}")
    lines.append("⚠️ Bozor har daqiqada o'zgarishi mumkin.")
    return "\n".join(lines)


def _short_news_caption(report: dict, language: str | None, source: str) -> str:
    visual = "GPT image" if source == "openai" else "Pulsar visual"
    news_line = _trim((report.get("key_news") or [{}])[0].get("title", "Fresh market news"), 140)
    return (
        f"<b>🗞 {h(t(language, 'analysis.fundamental_title'))}</b>\n"
        f"📡 {h(_format_prices(report.get('market_prices') or []))}\n"
        f"XAUUSD: {h(report['xauusd_bias'])} | USD: {h(report['usd_bias'])} | {visual}\n"
        f"🧠 {h(news_line)}"
    )


async def _live_prices(settings: Settings) -> list[dict]:
    rag = MarketRAGContext(settings)
    try:
        return await rag.live_quotes()
    finally:
        await rag.close()


def _format_prices(quotes: list[dict]) -> str:
    parts = []
    for quote in quotes:
        value = quote.get("price")
        if value is None:
            parts.append(f"{quote.get('symbol')}: n/a")
            continue
        change = quote.get("change_percent")
        change_text = "" if change is None else f" {change:+.2f}%"
        parts.append(f"{quote.get('symbol')}: {price(value)}{change_text}")
    return " | ".join(parts) or "XAUUSD/BTCUSD/DXY: n/a"


def _detect_symbol(text: str) -> str | None:
    upper = text.upper()
    patterns = {
        "XAUUSD": r"\b(XAUUSD|XAU/USD|GOLD|OLTIN)\b",
        "BTCUSD": r"\b(BTCUSD|BTC/USD|BTCUSDT|BITCOIN)\b",
        "DXY": r"\b(DXY|USDX|DOLLAR INDEX)\b",
        "EURUSD": r"\b(EURUSD|EUR/USD)\b",
        "GBPUSD": r"\b(GBPUSD|GBP/USD)\b",
        "USDJPY": r"\b(USDJPY|USD/JPY)\b",
    }
    for symbol, pattern in patterns.items():
        if re.search(pattern, upper):
            return symbol
    return None


def _trim(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"
