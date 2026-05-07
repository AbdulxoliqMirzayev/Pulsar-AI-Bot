from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TradingJournalEntry
from app.utils.math import calc_rr
from app.utils.timezone import utc_now


class TradingJournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, data: dict) -> TradingJournalEntry:
        payload = dict(data)
        if payload.get("rr") is None and all(payload.get(k) is not None for k in ("entry_price", "stop_loss", "take_profit")):
            payload["rr"] = calc_rr(payload["entry_price"], payload["stop_loss"], payload["take_profit"])
        entry = TradingJournalEntry(user_id=user_id, **payload)
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def history(self, user_id: int, limit: int = 20) -> list[TradingJournalEntry]:
        rows = await self.session.scalars(
            select(TradingJournalEntry)
            .where(TradingJournalEntry.user_id == user_id)
            .order_by(desc(TradingJournalEntry.opened_at))
            .limit(limit)
        )
        return list(rows)

    async def close(self, entry: TradingJournalEntry, result: str, profit_loss: float | None = None, notes: str | None = None) -> TradingJournalEntry:
        entry.result = result
        entry.profit_loss = profit_loss
        entry.notes = notes or entry.notes
        entry.closed_at = utc_now()
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def stats(self, user_id: int) -> dict:
        rows = list(await self.session.scalars(select(TradingJournalEntry).where(TradingJournalEntry.user_id == user_id)))
        closed = [row for row in rows if row.result in {"win", "loss", "breakeven"}]
        wins = sum(row.result == "win" for row in closed)
        losses = sum(row.result == "loss" for row in closed)
        total_pl = round(sum(float(row.profit_loss or 0) for row in closed), 2)
        avg_rr = round(sum(float(row.rr or 0) for row in closed) / len(closed), 2) if closed else 0
        return {
            "total": len(rows),
            "closed": len(closed),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / (wins + losses) * 100, 1) if wins + losses else 0,
            "total_pl": total_pl,
            "avg_rr": avg_rr,
        }
