from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class BacktestStats:
    total_trades: int
    win_rate: float
    total_pnl: float
    return_pct: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    expectancy: float
    equity_curve: list[float]
    trade_results: list[float]


def load_mt5_rates(symbol: str, timeframe: str = "H1", days: int = 90) -> pd.DataFrame:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 Python package is required for MT5 loading. Use --csv as fallback.") from exc

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    tf = getattr(mt5, f"TIMEFRAME_{timeframe.upper()}")
    rates = mt5.copy_rates_from(symbol, tf, datetime.now(timezone.utc), days * 24 + 300)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No MT5 data returned for {symbol}.")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df.rename(columns={"tick_volume": "volume"}, inplace=True)
    return df[["time", "open", "high", "low", "close", "volume"]]


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    lower = {c.lower(): c for c in df.columns}
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in lower]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    time_col = lower.get("time") or lower.get("date") or df.columns[0]
    volume_col = lower.get("volume") or lower.get("tick_volume")
    out = pd.DataFrame(
        {
            "time": pd.to_datetime(df[time_col], errors="coerce", utc=True),
            "open": df[lower["open"]].astype(float),
            "high": df[lower["high"]].astype(float),
            "low": df[lower["low"]].astype(float),
            "close": df[lower["close"]].astype(float),
            "volume": df[volume_col].astype(float) if volume_col else 1.0,
        }
    )
    return out.dropna().reset_index(drop=True)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]), (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def calculate_signals(window: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    fast = int(params.get("ema_fast", 9))
    slow = int(params.get("ema_slow", 21))
    trend = int(params.get("ema_trend", 200))
    bb_period = int(params.get("bb_period", 20))
    bb_std = float(params.get("bb_stddev", 2.0))
    data = window.copy().reset_index(drop=True)
    data["ema_fast"] = data["close"].ewm(span=fast, adjust=False).mean()
    data["ema_slow"] = data["close"].ewm(span=slow, adjust=False).mean()
    data["ema_trend"] = data["close"].ewm(span=trend, adjust=False).mean()
    data["atr"] = atr(data, int(params.get("atr_period", 14)))
    data["rsi"] = rsi(data["close"], int(params.get("rsi_period", 14)))
    mid = data["close"].rolling(bb_period).mean()
    std = data["close"].rolling(bb_period).std()
    upper = mid + std * bb_std
    lower = mid - std * bb_std
    row = data.iloc[-1]
    prev = data.iloc[-2]
    score = 0
    direction = 0

    if row.ema_fast > row.ema_slow > row.ema_trend:
        score += 3
        direction += 1
    if row.ema_fast < row.ema_slow < row.ema_trend:
        score += 3
        direction -= 1
    if prev.ema_fast <= prev.ema_slow and row.ema_fast > row.ema_slow:
        score += 2
        direction += 1
    if prev.ema_fast >= prev.ema_slow and row.ema_fast < row.ema_slow:
        score += 2
        direction -= 1
    if row.rsi < 30:
        score += 1
        direction += 1
    if row.rsi > 70:
        score += 1
        direction -= 1
    if len(upper) and row.close > upper.iloc[-1]:
        score += 2
        direction += 1
    if len(lower) and row.close < lower.iloc[-1]:
        score += 2
        direction -= 1
    volume_ratio = row.volume / max(data["volume"].tail(20).mean(), 1)
    if volume_ratio > 1.3:
        score += 1
    swing_high = data["high"].tail(50).max()
    swing_low = data["low"].tail(50).min()
    if row.close > swing_high:
        score += 2
        direction += 1
    if row.close < swing_low:
        score += 2
        direction -= 1

    return {
        "total_score": int(score),
        "direction": 1 if direction > 0 else -1 if direction < 0 else 0,
        "atr": float(row.atr),
        "volume_ratio": float(volume_ratio),
    }


def run_backtest(
    symbol: str = "EURUSD",
    params: dict[str, Any] | None = None,
    days: int = 90,
    initial_balance: float = 10000,
    data: pd.DataFrame | None = None,
) -> dict[str, Any]:
    params = params or {}
    df = data.copy().reset_index(drop=True) if data is not None else load_mt5_rates(symbol, "H1", days)
    balance = initial_balance
    equity_curve = [initial_balance]
    trades: list[dict[str, Any]] = []
    open_trade: dict[str, Any] | None = None
    peak = initial_balance
    max_dd = 0.0
    min_score = int(params.get("min_score", 12))
    rr_ratio = float(params.get("rr_ratio", 2.0))
    atr_mult = float(params.get("atr_multiplier", 2.0))
    risk_pct = min(float(params.get("risk_per_trade", 2.0)), 2.0)

    for i in range(220, len(df)):
        window = df.iloc[: i + 1]
        row = df.iloc[i]
        if open_trade:
            direction = open_trade["type"]
            hit = None
            exit_price = row.close
            if direction == 1:
                if row.low <= open_trade["sl"]:
                    hit, exit_price = "sl", open_trade["sl"]
                elif row.high >= open_trade["tp"]:
                    hit, exit_price = "tp", open_trade["tp"]
            else:
                if row.high >= open_trade["sl"]:
                    hit, exit_price = "sl", open_trade["sl"]
                elif row.low <= open_trade["tp"]:
                    hit, exit_price = "tp", open_trade["tp"]
            if hit:
                pnl = (exit_price - open_trade["entry"]) * direction * open_trade["lot_units"]
                balance += pnl
                trades.append({"time": row.time, "result": pnl, "win": pnl > 0, "hit": hit})
                open_trade = None
        else:
            signals = calculate_signals(window, params)
            if signals["total_score"] >= min_score and signals["direction"] != 0:
                direction = int(signals["direction"])
                sl_distance = max(signals["atr"] * atr_mult, float(row.close) * 0.001)
                tp_distance = sl_distance * rr_ratio
                risk_money = balance * risk_pct / 100
                lot_units = risk_money / sl_distance
                entry = float(row.close)
                open_trade = {
                    "type": direction,
                    "entry": entry,
                    "sl": entry - direction * sl_distance,
                    "tp": entry + direction * tp_distance,
                    "lot_units": lot_units,
                }
        equity_curve.append(balance)
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100)

    results = [float(t["result"]) for t in trades]
    wins = [r for r in results if r > 0]
    losses = [r for r in results if r < 0]
    returns = pd.Series(equity_curve).pct_change().dropna()
    downside = returns[returns < 0]
    sharpe = float((returns.mean() / returns.std()) * np.sqrt(252 * 24)) if returns.std() and not np.isnan(returns.std()) else 0.0
    sortino = float((returns.mean() / downside.std()) * np.sqrt(252 * 24)) if len(downside) > 1 and downside.std() else 0.0
    stats = BacktestStats(
        total_trades=len(trades),
        win_rate=len(wins) / len(trades) if trades else 0.0,
        total_pnl=balance - initial_balance,
        return_pct=(balance - initial_balance) / initial_balance * 100,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        profit_factor=sum(wins) / abs(sum(losses)) if losses else float(len(wins) > 0),
        expectancy=float(np.mean(results)) if results else 0.0,
        equity_curve=[round(float(x), 2) for x in equity_curve],
        trade_results=results,
    )
    return asdict(stats)


def monte_carlo_simulation(base_results: dict[str, Any], n_simulations: int = 1000) -> dict[str, float]:
    trade_results = np.array(base_results.get("trade_results") or [0.0], dtype=float)
    simulations = []
    drawdowns = []
    for _ in range(n_simulations):
        shuffled = np.random.choice(trade_results, len(trade_results), replace=True)
        equity = np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        dd = np.max(peak - equity) if len(equity) else 0
        simulations.append(float(equity[-1]) if len(equity) else 0.0)
        drawdowns.append(float(dd))
    return {
        "expected_return": float(np.mean(simulations)),
        "return_5th_pct": float(np.percentile(simulations, 5)),
        "return_95th_pct": float(np.percentile(simulations, 95)),
        "max_dd_average": float(np.mean(drawdowns)),
        "max_dd_worst": float(np.percentile(drawdowns, 95)),
        "probability_profitable": float(np.mean(np.array(simulations) > 0)),
    }


def walk_forward(df: pd.DataFrame, params: dict[str, Any], folds: int = 4) -> list[dict[str, Any]]:
    size = len(df) // folds
    reports = []
    for fold in range(1, folds):
        test = df.iloc[fold * size : (fold + 1) * size].copy()
        reports.append(run_backtest(params=params, data=test))
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--csv")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--params", default="../Models/genetic_best_params.json")
    parser.add_argument("--output", default="../Logs/backtest_report.json")
    args = parser.parse_args()
    params = json.loads(Path(args.params).read_text()) if Path(args.params).exists() else {}
    df = load_csv(args.csv) if args.csv else load_mt5_rates(args.symbol, "H1", args.days)
    report = run_backtest(args.symbol, params=params, days=args.days, data=df)
    output = {"report": report, "monte_carlo": monte_carlo_simulation(report), "walk_forward": walk_forward(df, params)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
