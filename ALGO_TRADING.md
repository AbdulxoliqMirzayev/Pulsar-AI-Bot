# Algo Trading Setup

## MT5 EA

File: `mql5/AlgoTradingBot_v1.mq5`

1. Open MetaTrader 5.
2. Open MetaEditor.
3. Copy or open `AlgoTradingBot_v1.mq5` inside `MQL5/Experts/Pulsar/`.
4. Compile.
5. In MT5, enable Algo Trading.
6. Attach the EA to a chart.
7. Test in Strategy Tester on demo data before live use.

## Built-In Strategy Modules

The EA scans 20 modules every 500 ms:

1. Fibonacci retracement
2. Gann levels
3. Order blocks
4. BOS/CHoCH
5. Liquidity zones
6. Fair value gaps
7. RSI divergence proxy
8. EMA crossover
9. Volume Profile + VWAP
10. Bollinger squeeze
11. MACD momentum
12. Support/resistance
13. ICT killzones
14. Stochastic oscillator
15. ATR trailing stop
16. Engulfing candle
17. Wick rejection
18. Premium/discount zones
19. Martingale safety guard
20. Multi-timeframe confluence

## Risk Rules

- EA input `RiskPercent` is capped at 5% in code.
- Daily exposure guard is 5% of balance.
- Trading pauses after 10% drawdown.
- All positions close after configured `MaxDrawdown`.
- Minimum RR is 1.5 by default.

## Backtesting

Python module: `backtest.py`

```bash
python backtest.py --csv your_mt5_export.csv --output backtest_report.json
```

On Windows with the `MetaTrader5` Python package installed:

```bash
python backtest.py --symbol XAUUSD --timeframe M15 --bars 5000
```

## Dashboard

Open `dashboard.html` in a browser. It expects WebSocket JSON updates at `ws://localhost:8765` by default.

Expected payload:

```json
{
  "balance": 10000,
  "daily_pl": 120.5,
  "risk_used": 2.1,
  "open_trades": 1,
  "equity": [10000, 10080, 10120],
  "strategies": {"EMA": 1.2, "SMC": 2.5},
  "trades": [{"time": "2026-05-07 10:00", "symbol": "XAUUSD", "side": "BUY", "lot": 0.1, "pl": 50, "score": 9}]
}
```
