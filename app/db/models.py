from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


JsonType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(8), default="uz")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_vision_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_news_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_risk_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reset_date: Mapped[str | None] = mapped_column(String(16))
    session_reminders_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    signals: Mapped[list["Signal"]] = relationship(back_populates="user")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str] = mapped_column(String(64), default="mexc")
    market_type: Mapped[str] = mapped_column(String(32), default="spot")
    price: Mapped[float | None] = mapped_column(Float)
    change_percent: Mapped[float | None] = mapped_column(Float)
    volume_24h: Mapped[float | None] = mapped_column(Float)
    high_24h: Mapped[float | None] = mapped_column(Float)
    low_24h: Mapped[float | None] = mapped_column(Float)
    timeframe: Mapped[str | None] = mapped_column(String(16))
    candles_json: Mapped[dict | list | None] = mapped_column(JsonType)
    indicators_json: Mapped[dict | None] = mapped_column(JsonType)
    order_book_summary_json: Mapped[dict | None] = mapped_column(JsonType)
    buy_sell_pressure_json: Mapped[dict | None] = mapped_column(JsonType)
    funding_rate: Mapped[float | None] = mapped_column(Float)
    open_interest: Mapped[float | None] = mapped_column(Float)
    long_short_ratio: Mapped[float | None] = mapped_column(Float)
    technical_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_type: Mapped[str] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    entry_min: Mapped[float | None] = mapped_column(Float)
    entry_max: Mapped[float | None] = mapped_column(Float)
    entry_type: Mapped[str | None] = mapped_column(String(16))
    stop_loss: Mapped[float | None] = mapped_column(Float)
    take_profit_1: Mapped[float | None] = mapped_column(Float)
    take_profit_2: Mapped[float | None] = mapped_column(Float)
    take_profit_3: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(16))
    risk_amount_percent: Mapped[float | None] = mapped_column(Float)
    rr: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    max_stop_pips: Mapped[float | None] = mapped_column(Float)
    technical_reason: Mapped[str | None] = mapped_column(Text)
    fundamental_reason: Mapped[str | None] = mapped_column(Text)
    full_reason_json: Mapped[dict | None] = mapped_column(JsonType)
    mexc_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("market_snapshots.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="signals")


class SignalFeedback(Base):
    __tablename__ = "signal_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    result: Mapped[str] = mapped_column(String(24))
    user_note: Mapped[str | None] = mapped_column(Text)
    ai_post_review: Mapped[str | None] = mapped_column(Text)
    mistake_reason: Mapped[str | None] = mapped_column(Text)
    improvement_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SignalLearningMemory(Base):
    __tablename__ = "signal_learning_memory"
    __table_args__ = (UniqueConstraint("symbol", "setup_type", name="uq_learning_symbol_setup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    setup_type: Mapped[str] = mapped_column(String(64))
    failed_reasons_json: Mapped[list | dict | None] = mapped_column(JsonType)
    successful_reasons_json: Mapped[list | dict | None] = mapped_column(JsonType)
    strategy_weights_json: Mapped[dict | None] = mapped_column(JsonType)
    win_count: Mapped[int] = mapped_column(Integer, default=0)
    loss_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_instruments: Mapped[list | None] = mapped_column(JsonType)
    sentiment_label: Mapped[str | None] = mapped_column(String(32))
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    impact_score: Mapped[float | None] = mapped_column(Float)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JsonType)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    hash_key: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str | None] = mapped_column(String(64))
    event_name: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str | None] = mapped_column(String(8), index=True)
    impact: Mapped[str | None] = mapped_column(String(16), index=True)
    forecast: Mapped[str | None] = mapped_column(String(128))
    previous: Mapped[str | None] = mapped_column(String(128))
    actual: Mapped[str | None] = mapped_column(String(128))
    event_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_time_local: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_instruments: Mapped[list | None] = mapped_column(JsonType)
    raw_payload: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelegramSource(Base):
    __tablename__ = "telegram_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_username: Mapped[str] = mapped_column(String(255), unique=True)
    channel_title: Mapped[str | None] = mapped_column(String(255))
    channel_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetch_error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrokerReferral(Base):
    __tablename__ = "broker_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    broker_name: Mapped[str] = mapped_column(String(255))
    referral_url: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    image_file_id: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    content_type: Mapped[str] = mapped_column(String(32), default="text")
    text: Mapped[str | None] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(Text)
    video_file_id: Mapped[str | None] = mapped_column(Text)
    document_file_id: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiUsage(Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    endpoint: Mapped[str | None] = mapped_column(String(255))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    cost_estimate: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str | None] = mapped_column(String(32))
    error_message: Mapped[str | None] = mapped_column(Text)
    response_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action_type: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JsonType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TradingJournalEntry(Base):
    __tablename__ = "trading_journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    entry_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    take_profit: Mapped[float | None] = mapped_column(Float)
    lot_size: Mapped[float | None] = mapped_column(Float)
    risk_percent: Mapped[float | None] = mapped_column(Float)
    rr: Mapped[float | None] = mapped_column(Float)
    strategy: Mapped[str | None] = mapped_column(String(128))
    setup_tags: Mapped[list | None] = mapped_column(JsonType)
    result: Mapped[str] = mapped_column(String(24), default="open")
    profit_loss: Mapped[float | None] = mapped_column(Float)
    profit_loss_percent: Mapped[float | None] = mapped_column(Float)
    emotion_before: Mapped[str | None] = mapped_column(String(64))
    emotion_after: Mapped[str | None] = mapped_column(String(64))
    mistake_tags: Mapped[list | None] = mapped_column(JsonType)
    screenshot_file_id: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    ai_review: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
