from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx


class TelegramAlertClient:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_ALERT_CHAT_ID", "")
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required.")
        if not self.chat_id:
            raise RuntimeError("TELEGRAM_ALERT_CHAT_ID is required.")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, text: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.base_url}/sendMessage", data={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"})
            response.raise_for_status()

    async def send_photo(self, photo_path: str, caption: str = "") -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            with Path(photo_path).open("rb") as file:
                response = await client.post(
                    f"{self.base_url}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"photo": file},
                )
            response.raise_for_status()

    async def signal_alert(self, symbol: str, direction: str, entry: float, sl: float, tp: float, score: int) -> None:
        await self.send_message(
            f"<b>Algo signal</b>\nSymbol: {symbol}\nDirection: {direction}\nEntry: {entry}\nSL: {sl}\nTP: {tp}\nScore: {score}/15"
        )

    async def daily_summary(self, pnl: float, win_rate: float, open_trades: int, risk_used: float) -> None:
        await self.send_message(
            f"<b>Daily summary</b>\nP/L: {pnl:.2f}\nWin-rate: {win_rate:.1f}%\nOpen trades: {open_trades}\nRisk used: {risk_used:.2f}%"
        )

    async def risk_alert(self, drawdown: float) -> None:
        await self.send_message(f"<b>Risk alert</b>\nDrawdown: {drawdown:.2f}%")


async def main() -> None:
    client = TelegramAlertClient()
    await client.send_message("Pulsar Telegram alerts are connected.")


if __name__ == "__main__":
    asyncio.run(main())
