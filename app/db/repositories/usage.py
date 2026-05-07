from __future__ import annotations

from app.db.models import User
from app.db.repositories.users import reset_daily_counts_if_needed


class UsageRepository:
    def __init__(self, user: User, timezone: str = "Asia/Tashkent") -> None:
        self.user = user
        self.timezone = timezone

    def check_and_increment(self, action: str, limit: int) -> tuple[bool, int]:
        if self.user.is_admin or self.user.is_premium:
            return True, 0
        reset_daily_counts_if_needed(self.user, self.timezone)
        field = {
            "market_signal": "daily_signal_count",
            "chart_vision": "daily_vision_count",
            "news_impact": "daily_news_count",
            "risk_calculator": "daily_risk_count",
        }[action]
        current = int(getattr(self.user, field) or 0)
        if current >= limit:
            return False, current
        setattr(self.user, field, current + 1)
        return True, current + 1
