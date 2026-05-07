# Pulsar Free Data Sources

Use a layered data approach so the bot keeps working when a provider is rate-limited.

## Market Data

- MEXC public Spot API: crypto and tokenized gold pairs such as BTCUSDT and XAUTUSDT. Used for `/api/v3/klines` and `/api/v3/ticker/24hr`.
- Binance public Spot API: fallback for BTCUSDT, XAUTUSDT and PAXGUSDT OHLCV when MEXC does not list a symbol.
- CoinGecko API: fallback crypto spot prices through `/simple/price`.
- Alpha Vantage: FX daily OHLC through `FX_DAILY`; requires a free API key.
- Yahoo Finance chart endpoint: best-effort no-key fallback for commodities/FX chart candles; this is not treated as the execution source.

## Fundamental And Calendar

- Trading Economics calendar: USD macro calendar through `calendar/country/united states`, with `guest:guest` usable for development.
- ForexFactory/Faireconomy XML: fallback weekly economic calendar feed.
- FRED: official US macro time series; requires a free FRED API key.

## News

- RSS: FXStreet, CoinDesk, Cointelegraph.
- NewsAPI: optional broader article search through `/v2/everything`; free for development but requires an API key.
- CryptoPanic: optional crypto news feed when an API key is provided.

## Notes

- For XAUUSD intraday without a paid broker feed, the app uses XAUTUSDT/PAXGUSDT as a free proxy. For institutional-grade XAUUSD execution, MT5 broker data should be the source of truth.
- News and macro data can be delayed or rate-limited on free plans. Live trading decisions should be confirmed in MT5 Strategy Tester and on demo before real capital.
