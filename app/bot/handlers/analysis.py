from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
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
from app.services.market_data.service import MarketDataService
from app.utils.formatters import h, price
from app.utils.i18n import pt, t
from app.utils.telegram_files import download_file_bytes


router = Router(name="analysis")


@router.callback_query(F.data == "menu:technical")
async def technical(callback: CallbackQuery, settings: Settings, language: str | None = None, session: AsyncSession | None = None, db_user: User | None = None) -> None:
    await callback.message.edit_text(pt(language, "analysis.loading"))
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
        await callback.message.answer(_format_technical(report.to_dict(), language), reply_markup=main_menu(language))
    except Exception as exc:
        await callback.message.answer(f"{pt(language, 'errors.generic')}\n<code>{h(exc)}</code>", reply_markup=main_menu(language))
    finally:
        await service.close()
        await callback.answer()


@router.callback_query(F.data == "menu:news")
async def news(callback: CallbackQuery, settings: Settings, language: str | None = None, session: AsyncSession | None = None) -> None:
    await callback.message.edit_text(pt(language, "analysis.loading"))
    analyzer = FundamentalAnalyzer(settings)
    try:
        report = await analyzer.analyze_now(language)
        if session is not None:
            await NewsRepository(session).save_many(report.key_news)
            await CalendarRepository(session).save_many(report.key_events)
        await callback.message.answer(_format_fundamental(report.to_dict(), language), reply_markup=main_menu(language))
    except Exception as exc:
        await callback.message.answer(f"{pt(language, 'errors.generic')}\n<code>{h(exc)}</code>", reply_markup=main_menu(language))
    finally:
        await analyzer.close()
        await callback.answer()


@router.callback_query(F.data == "menu:calendar")
async def calendar(callback: CallbackQuery, settings: Settings, language: str | None = None) -> None:
    analyzer = FundamentalAnalyzer(settings)
    try:
        events = await analyzer.calendar.upcoming_usd_events()
        lines = [f"<b>{h(t(language, 'analysis.calendar_title'))}</b>"]
        for event in events[:10]:
            time_text = event.event_time_utc.strftime("%Y-%m-%d %H:%M UTC") if event.event_time_utc else "TBA"
            lines.append(
                f"{h(time_text)} | <b>{h(event.event_name)}</b> | {h(event.impact)} | A:{h(event.actual)} F:{h(event.forecast)} P:{h(event.previous)}"
            )
        await callback.message.answer("\n".join(lines), reply_markup=main_menu(language))
    finally:
        await analyzer.close()
        await callback.answer()


@router.callback_query(F.data == "menu:vision")
async def vision_prompt(callback: CallbackQuery, language: str | None = None) -> None:
    await callback.message.answer(pt(language, "analysis.vision_prompt"))
    await callback.answer()


@router.message(F.photo)
async def vision_photo(message: Message, settings: Settings, language: str | None = None) -> None:
    photo = message.photo[-1]
    image = await download_file_bytes(message.bot, photo.file_id)
    analyzer = ChartVisionAnalyzer(settings)
    text = await analyzer.analyze(image, language=language, symbol=settings.technical_default_symbol)
    await message.answer(text)


@router.callback_query(F.data == "menu:journal")
async def journal(callback: CallbackQuery, language: str | None = None, session: AsyncSession | None = None, db_user: User | None = None) -> None:
    if session is None or db_user is None:
        await callback.message.answer(pt(language, "errors.generic"), reply_markup=main_menu(language))
        await callback.answer()
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
    await callback.message.answer("\n".join(lines), reply_markup=main_menu(language))
    await callback.answer()


@router.callback_query(F.data == "menu:algo")
async def algo(callback: CallbackQuery, language: str | None = None) -> None:
    await callback.message.answer(f"<b>{h(t(language, 'algo.title'))}</b>\n{h(t(language, 'algo.text'))}", reply_markup=main_menu(language))
    await callback.answer()


def _format_technical(report: dict, language: str) -> str:
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


def _format_fundamental(report: dict, language: str) -> str:
    lines = [
        f"<b>{h(t(language, 'analysis.fundamental_title'))}</b>",
        f"USD: <b>{h(report['usd_bias'])}</b> | XAUUSD: <b>{h(report['xauusd_bias'])}</b> | BTC: <b>{h(report['btc_bias'])}</b>",
        f"Risk: {h(report['risk_mood'])} | Confidence: {report['confidence']}%",
        "",
        h(report["summary"]),
    ]
    if report["key_news"]:
        lines.append("\n<b>News</b>")
        for item in report["key_news"][:5]:
            lines.append(f"- {h(item['title'])} ({h(item['source'])})")
    if report["key_events"]:
        lines.append("\n<b>Calendar</b>")
        for item in report["key_events"][:5]:
            lines.append(f"- {h(item['event_name'])}: A {h(item['actual'])} / F {h(item['forecast'])}")
    return "\n".join(lines)
