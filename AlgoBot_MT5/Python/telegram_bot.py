from __future__ import annotations

import argparse
import csv
import io
import json
import os
import socket
from pathlib import Path

try:
    import matplotlib.pyplot as plt
except Exception:  # noqa: BLE001
    plt = None

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
except Exception as exc:  # noqa: BLE001
    raise SystemExit("Install python-telegram-bot and matplotlib to run this bot: pip install python-telegram-bot matplotlib") from exc


BOT_TOKEN = os.getenv("ALGOBOT_TELEGRAM_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
MT5_HOST = os.getenv("ALGOBOT_MT5_HOST", "127.0.0.1")
MT5_PORT = int(os.getenv("ALGOBOT_MT5_PORT", "8888"))
CONFIG_DIR = Path(__file__).resolve().parents[1] / "Config"
LOG_DIR = Path(__file__).resolve().parents[1] / "Logs"


def write_command(command: str) -> str:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "commands.csv"
    with path.open("a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow([command])
    return "Command queued for EA."


async def send_mt5_command(command: str) -> str:
    try:
        with socket.create_connection((MT5_HOST, MT5_PORT), timeout=1.5) as sock:
            sock.sendall(command.encode("utf-8"))
            return sock.recv(4096).decode("utf-8")
    except OSError:
        return write_command(command)


def read_status() -> dict:
    path = LOG_DIR / "state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "active": False,
        "balance": 0,
        "currency": "",
        "open_trades": 0,
        "daily_pnl": 0,
        "signal_score": 0,
        "ml_signal": "NEUTRAL",
        "elliott_wave": 0,
        "sentiment": 0,
        "daily_bias": "NEUTRAL",
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Status", callback_data="status"), InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Start Bot", callback_data="start_bot"), InlineKeyboardButton("Pause Bot", callback_data="pause_bot")],
        [InlineKeyboardButton("Close ALL", callback_data="close_all"), InlineKeyboardButton("P/L Chart", callback_data="pnl_chart")],
        [InlineKeyboardButton("Settings", callback_data="settings"), InlineKeyboardButton("Trade Log", callback_data="trade_log")],
    ]
    await update.message.reply_text("AlgoBot v3.0 boshqaruv markazi:", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "status":
        status = read_status()
        text = (
            f"Bot holati: {'FAOL' if status.get('active') else 'TOXTATILGAN'}\n"
            f"Balans: {status.get('balance', 0):.2f} {status.get('currency', '')}\n"
            f"Ochiq savdolar: {status.get('open_trades', 0)}\n"
            f"Kunlik P/L: {status.get('daily_pnl', 0):+.2f}\n"
            f"Signal kuchi: {status.get('signal_score', 0)}/40\n"
            f"ML signal: {status.get('ml_signal', 'NEUTRAL')}\n"
            f"Elliott: {status.get('elliott_wave', 0)}\n"
            f"Sentiment: {status.get('sentiment', 0):.2f}\n"
            f"HTF trend: {status.get('daily_bias', 'NEUTRAL')}"
        )
        await query.edit_message_text(text)
    elif query.data == "balance":
        status = read_status()
        await query.edit_message_text(f"Balance: {status.get('balance', 0):.2f} {status.get('currency', '')}")
    elif query.data == "start_bot":
        await query.edit_message_text(await send_mt5_command("START"))
    elif query.data == "pause_bot":
        await query.edit_message_text(await send_mt5_command("PAUSE"))
    elif query.data == "close_all":
        keyboard = [[InlineKeyboardButton("HA, yopish", callback_data="confirm_close"), InlineKeyboardButton("Bekor qilish", callback_data="cancel")]]
        await query.edit_message_text("Barcha ochiq pozitsiyalarni yopishni tasdiqlaysizmi?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == "confirm_close":
        await query.edit_message_text(await send_mt5_command("CLOSE_ALL"))
    elif query.data == "cancel":
        await query.edit_message_text("Bekor qilindi.")
    elif query.data == "pnl_chart":
        img = generate_pnl_chart()
        if img:
            await context.bot.send_photo(query.message.chat_id, img, caption="So'nggi equity curve")
        else:
            await query.edit_message_text("Chart yaratish uchun matplotlib yoki equity data topilmadi.")
    elif query.data == "trade_log":
        await query.edit_message_text(read_trade_log())
    else:
        await query.edit_message_text("Settings config.json orqali boshqariladi.")


def generate_pnl_chart() -> io.BytesIO | None:
    if plt is None:
        return None
    status = read_status()
    equity = status.get("equity") or []
    if not equity:
        return None
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(equity, color="#00aa66", linewidth=2)
    ax.set_title("AlgoBot Equity Curve")
    ax.grid(True, alpha=0.25)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return buf


def read_trade_log(limit: int = 10) -> str:
    path = LOG_DIR / "trades.csv"
    if not path.exists():
        return "Trade log topilmadi."
    rows = list(csv.reader(path.open(encoding="utf-8")))[-limit:]
    return "\n".join(" | ".join(row[:8]) for row in rows) or "Trade log bo'sh."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=BOT_TOKEN)
    args = parser.parse_args()
    if not args.token:
        raise SystemExit("Telegram token required: --token or ALGOBOT_TELEGRAM_TOKEN.")
    app = ApplicationBuilder().token(args.token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Telegram control bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
