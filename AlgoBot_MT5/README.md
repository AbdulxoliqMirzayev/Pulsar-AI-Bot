# AlgoBot MT5 v3.0 Ultra

This package is a modular MetaTrader 5 algorithmic trading suite.

## Files

- `MQL5/Experts/AlgoBot_Master.mq5`: main EA.
- `MQL5/Experts/AlgoBot_Slave.mq5`: account copier receiver.
- `MQL5/Include/*.mqh`: strategy, SMC, ML, risk, grid, prop firm, copier and dashboard modules.
- `Python/*.py`: sentiment, ML training, genetic optimizer, backtesting, Telegram control, copier and dashboard servers.
- `Config/*.json`: risk, prop firm and symbol settings.
- `Models/*`: ML weights and GA params.
- `Logs/*`: trade, signal and error logs.

## MT5 Install

1. Copy `AlgoBot_MT5/MQL5/Experts/*` into your terminal `MQL5/Experts/`.
2. Copy `AlgoBot_MT5/MQL5/Include/*` into `MQL5/Include/`.
3. Copy `Config`, `Models`, and `Logs` into the terminal common `Files` directory if you want EA file sharing with Python.
4. Open `AlgoBot_Master.mq5` in MetaEditor and compile.
5. Run Strategy Tester before any demo or live use.

## Python Services

From `AlgoBot_MT5/Python`:

```bash
python sentiment_engine.py
python account_copier_server.py
python dashboard_server.py
python ml_trainer.py --symbol EURUSD
python genetic_optimizer.py --symbol EURUSD --generations 20
python backtest_engine.py --symbol EURUSD --days 365
```

## Safety

- The EA hard-caps daily risk at 5%.
- `RiskPerTrade` is capped at 2% in lot sizing.
- Every main trade requires SL and TP.
- Martingale and latency arbitrage are off by default.
- MT5 Strategy Tester validation is mandatory before live use.
