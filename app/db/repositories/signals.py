from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Signal, SignalFeedback, SignalLearningMemory
from app.utils.timezone import utc_now


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def pending_for_user(self, user_id: int) -> Signal | None:
        return await self.session.scalar(
            select(Signal).where(Signal.user_id == user_id, Signal.status == "pending").order_by(desc(Signal.created_at)).limit(1)
        )

    async def create(self, user_id: int, data: dict) -> Signal:
        signal = Signal(user_id=user_id, **data)
        self.session.add(signal)
        await self.session.commit()
        await self.session.refresh(signal)
        return signal

    async def history(self, user_id: int, limit: int = 10) -> list[Signal]:
        rows = await self.session.scalars(select(Signal).where(Signal.user_id == user_id).order_by(desc(Signal.created_at)).limit(limit))
        return list(rows)

    async def close_with_feedback(self, signal: Signal, result: str, note: str | None = None) -> Signal:
        status = {"tp_hit": "tp_hit", "sl_hit": "sl_hit", "cancelled": "cancelled", "tp": "tp_hit", "sl": "sl_hit", "cancel": "cancelled"}[result]
        signal.status = status
        signal.closed_at = utc_now()
        feedback = SignalFeedback(
            signal_id=signal.id,
            user_id=signal.user_id,
            result=status,
            user_note=note,
            ai_post_review="DB adaptive learning review saved.",
            mistake_reason="News/volatility confirmation" if status == "sl_hit" else None,
            improvement_note="Weight adjusted by setup performance.",
        )
        self.session.add(feedback)
        await self.update_learning(signal.symbol, signal.full_reason_json or {}, status)
        await self.session.commit()
        return signal

    async def update_learning(self, symbol: str, reason: dict, result: str) -> None:
        setup = reason.get("setup_type") or "general"
        memory = await self.session.scalar(
            select(SignalLearningMemory).where(SignalLearningMemory.symbol == symbol, SignalLearningMemory.setup_type == setup)
        )
        if not memory:
            memory = SignalLearningMemory(
                symbol=symbol,
                setup_type=setup,
                failed_reasons_json=[],
                successful_reasons_json=[],
                strategy_weights_json={setup: 1.0},
            )
            self.session.add(memory)
        weights = memory.strategy_weights_json or {setup: 1.0}
        if result == "tp_hit":
            memory.win_count += 1
            memory.successful_reasons_json = [*(memory.successful_reasons_json or []), reason]
            weights[setup] = min(1.5, float(weights.get(setup, 1.0)) + 0.1)
        elif result == "sl_hit":
            memory.loss_count += 1
            memory.failed_reasons_json = [*(memory.failed_reasons_json or []), reason]
            weights[setup] = max(0.5, float(weights.get(setup, 1.0)) - 0.05)
        memory.total_count = memory.win_count + memory.loss_count
        memory.strategy_weights_json = weights
        memory.last_updated_at = utc_now()

    async def stats(self, user_id: int | None = None) -> dict:
        query = select(Signal)
        if user_id:
            query = query.where(Signal.user_id == user_id)
        rows = list(await self.session.scalars(query))
        total = len(rows)
        tp = sum(row.status == "tp_hit" for row in rows)
        sl = sum(row.status == "sl_hit" for row in rows)
        pending = sum(row.status == "pending" for row in rows)
        cancelled = sum(row.status == "cancelled" for row in rows)
        closed = tp + sl
        avg_rr = sum(float(row.rr or 0) for row in rows) / total if total else 0
        return {"total": total, "tp": tp, "sl": sl, "pending": pending, "cancelled": cancelled, "win_rate": round(tp / closed * 100, 1) if closed else 0, "avg_rr": round(avg_rr, 2)}

    async def today_count(self) -> int:
        return int(await self.session.scalar(select(func.count(Signal.id)).where(func.date(Signal.created_at) == func.current_date())) or 0)
