from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    admin_contact_username: str = Field(default="mirzayev_ai", alias="ADMIN_CONTACT_USERNAME")

    database_url: str = Field(default="", alias="DATABASE_URL")
    db_path: str = Field(default="data/pulsar.db", alias="DB_PATH")
    redis_url: str = Field(default="", alias="REDIS_URL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_text_model: str = Field(default="gpt-5.5", alias="OPENAI_TEXT_MODEL")
    openai_vision_model: str = Field(default="gpt-5.5", alias="OPENAI_VISION_MODEL")
    openai_temperature: float = Field(default=0.2, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=3500, alias="OPENAI_MAX_TOKENS")
    enable_vision_analysis: bool = Field(default=True, alias="ENABLE_VISION_ANALYSIS")

    mexc_api_key: str = Field(default="", alias="MEXC_API_KEY")
    mexc_api_secret: str = Field(default="", alias="MEXC_API_SECRET")
    mexc_base_url: str = Field(default="https://api.mexc.com", alias="MEXC_BASE_URL")
    mexc_enable_spot: bool = Field(default=True, alias="MEXC_ENABLE_SPOT")
    mexc_enable_futures: bool = Field(default=True, alias="MEXC_ENABLE_FUTURES")
    default_btc_symbol: str = Field(default="BTCUSDT", alias="DEFAULT_BTC_SYMBOL")
    default_gold_symbol: str = Field(default="XAUTUSDT", alias="DEFAULT_GOLD_SYMBOL")

    coingecko_base_url: str = Field(default="https://api.coingecko.com/api/v3", alias="COINGECKO_BASE_URL")
    coingecko_enable: bool = Field(default=True, alias="COINGECKO_ENABLE")
    crypto_panic_api_key: str = Field(default="", alias="CRYPTO_PANIC_API_KEY")
    crypto_panic_enable: bool = Field(default=True, alias="CRYPTO_PANIC_ENABLE")
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    finnhub_enable: bool = Field(default=True, alias="FINNHUB_ENABLE")
    alpha_vantage_api_key: str = Field(default="", alias="ALPHA_VANTAGE_API_KEY")
    alpha_vantage_enable: bool = Field(default=True, alias="ALPHA_VANTAGE_ENABLE")
    newsapi_key: str = Field(default="", alias="NEWSAPI_KEY")
    newsapi_enable: bool = Field(default=True, alias="NEWSAPI_ENABLE")
    yfinance_enable: bool = Field(default=True, alias="YFINANCE_ENABLE")
    fred_api_key: str = Field(default="", alias="FRED_API_KEY")
    fred_enable: bool = Field(default=True, alias="FRED_ENABLE")
    trading_economics_key: str = Field(default="guest:guest", alias="TRADING_ECONOMICS_KEY")
    trading_economics_enable: bool = Field(default=True, alias="TRADING_ECONOMICS_ENABLE")

    forexfactory_rss_enable: bool = Field(default=True, alias="FOREXFACTORY_RSS_ENABLE")
    forexfactory_rss_url: str = Field(
        default="https://nfs.faireconomy.media/ff_calendar_thisweek.xml",
        alias="FOREXFACTORY_RSS_URL",
    )
    investing_rss_enable: bool = Field(default=True, alias="INVESTING_RSS_ENABLE")
    coindesk_rss_url: str = Field(default="https://www.coindesk.com/arc/outboundfeeds/rss/", alias="COINDESK_RSS_URL")
    cointelegraph_rss_url: str = Field(default="https://cointelegraph.com/rss", alias="COINTELEGRAPH_RSS_URL")
    reuters_rss_url: str = Field(default="https://feeds.reuters.com/reuters/businessNews", alias="REUTERS_RSS_URL")
    fxstreet_rss_url: str = Field(default="https://www.fxstreet.com/rss/news", alias="FXSTREET_RSS_URL")

    telethon_api_id: str = Field(default="", alias="TELETHON_API_ID")
    telethon_api_hash: str = Field(default="", alias="TELETHON_API_HASH")
    telethon_session_string: str = Field(default="", alias="TELETHON_SESSION_STRING")
    enable_telegram_channel_sources: bool = Field(default=True, alias="ENABLE_TELEGRAM_CHANNEL_SOURCES")
    telegram_source_channels: str = Field(default="", alias="TELEGRAM_SOURCE_CHANNELS")

    default_language: str = Field(default="uz", alias="DEFAULT_LANGUAGE")
    default_timezone: str = Field(default="Asia/Tashkent", alias="DEFAULT_TIMEZONE")
    app_env: str = Field(default="production", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    price_cache_seconds: int = Field(default=30, alias="PRICE_CACHE_SECONDS")
    news_lookback_hours: int = Field(default=2, alias="NEWS_LOOKBACK_HOURS")
    news_fetch_limit: int = Field(default=60, alias="NEWS_FETCH_LIMIT")
    candle_timeframes: str = Field(default="1m,5m,15m,1h,4h", alias="CANDLE_TIMEFRAMES")

    signal_max_open_per_user: int = Field(default=1, alias="SIGNAL_MAX_OPEN_PER_USER")
    gold_max_stop_pips: float = Field(default=70, alias="GOLD_MAX_STOP_PIPS")
    btc_max_stop_percent: float = Field(default=1.5, alias="BTC_MAX_STOP_PERCENT")
    min_risk_reward: float = Field(default=1.5, alias="MIN_RISK_REWARD")
    signal_confidence_threshold: int = Field(default=55, alias="SIGNAL_CONFIDENCE_THRESHOLD")
    technical_confluence_threshold: int = Field(default=8, alias="TECHNICAL_CONFLUENCE_THRESHOLD")
    technical_default_symbol: str = Field(default="XAUUSD", alias="TECHNICAL_DEFAULT_SYMBOL")
    algo_config_path: str = Field(default="config.json", alias="ALGO_CONFIG_PATH")

    free_daily_signal_limit: int = Field(default=5, alias="FREE_DAILY_SIGNAL_LIMIT")
    free_daily_vision_limit: int = Field(default=3, alias="FREE_DAILY_VISION_LIMIT")
    free_daily_news_limit: int = Field(default=5, alias="FREE_DAILY_NEWS_LIMIT")
    free_daily_risk_limit: int = Field(default=20, alias="FREE_DAILY_RISK_LIMIT")

    session_reminders_enabled: bool = Field(default=True, alias="SESSION_REMINDERS_ENABLED")
    asia_session_time: str = Field(default="05:00", alias="ASIA_SESSION_TIME")
    london_session_time: str = Field(default="12:00", alias="LONDON_SESSION_TIME")
    new_york_session_time: str = Field(default="17:00", alias="NEW_YORK_SESSION_TIME")
    session_timezone: str = Field(default="Asia/Tashkent", alias="SESSION_TIMEZONE")

    broadcast_batch_size: int = Field(default=25, alias="BROADCAST_BATCH_SIZE")
    broadcast_delay_seconds: float = Field(default=1, alias="BROADCAST_DELAY_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    @property
    def admin_id_set(self) -> set[int]:
        return set(_parse_ints(self.admin_ids))

    @property
    def timeframes(self) -> list[str]:
        return list(_parse_strings(self.candle_timeframes)) or ["1m", "5m", "15m", "1h", "4h"]

    @property
    def telegram_channels(self) -> list[str]:
        return list(_parse_strings(self.telegram_source_channels))

    @property
    def openai_text_active(self) -> bool:
        return bool(self.openai_api_key and self.openai_text_model)

    @property
    def openai_vision_active(self) -> bool:
        return bool(self.openai_api_key and self.openai_vision_model and self.enable_vision_analysis)

    @property
    def redis_active(self) -> bool:
        return bool(self.redis_url)

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.db_path}"

    def is_admin(self, telegram_id: int | str) -> bool:
        try:
            return int(telegram_id) in self.admin_id_set
        except (TypeError, ValueError):
            return False

    def daily_limit_for(self, action: str) -> int:
        return {
            "market_signal": self.free_daily_signal_limit,
            "chart_vision": self.free_daily_vision_limit,
            "news_impact": self.free_daily_news_limit,
            "risk_calculator": self.free_daily_risk_limit,
        }.get(action, 0)


def _parse_ints(raw: str) -> Iterable[int]:
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            yield int(part)
        except ValueError:
            continue


def _parse_strings(raw: str) -> Iterable[str]:
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part:
            yield part


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
