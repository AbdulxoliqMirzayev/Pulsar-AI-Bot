# Pulsar Forex Analysis Bot

Pulsar is a Telegram bot and MT5 algo trading toolkit focused on:

- Fundamental analysis for USD, XAUUSD and BTC
- Technical analysis with SMC/ICT concepts
- GPT chart analysis through the OpenAI Responses API
- Trading journal and signal history
- MT5 Expert Advisor with 20 strategy modules

## Run Telegram Bot

```bash
cp .env.example .env
python main.py
```

Required:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY` for GPT chart/fundamental summaries

Optional but recommended:

- `ALPHA_VANTAGE_API_KEY`
- `FRED_API_KEY`
- `NEWSAPI_KEY`
- `CRYPTO_PANIC_API_KEY`

## Language Flow

On `/start`, the bot asks the user to choose:

- O'zbek
- Русский
- English

After that, menus and replies are served in the selected language.

## Analysis Flow

- Chart analysis pulls free OHLCV data where available, then checks market structure, key levels, order blocks, liquidity, FVG, volume profile, VWAP and indicator confluence. A user can also upload a chart screenshot for GPT-5.5 vision analysis.
- Fundamental analysis pulls RSS/news/calendar/macro data and scores USD, XAUUSD, BTC and risk mood.
- News analysis can generate a market-mood visual through OpenAI image generation, with a local Pulsar visual fallback.

## Railway

Set these Railway variables before deploy:

- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_TEXT_MODEL=gpt-5.5`
- `OPENAI_VISION_MODEL=gpt-5.5`
- `OPENAI_FALLBACK_MODELS=gpt-5.2,gpt-5.1,gpt-5`

Railway start command is already configured as:

```bash
python main.py
```

See `DATA_SOURCES.md` and `ALGO_TRADING.md` for provider and MT5 details.
