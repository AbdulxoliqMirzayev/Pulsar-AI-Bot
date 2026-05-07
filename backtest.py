from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(slots=True)
class BacktestReport:
    trades: int
    total_return: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    monte_carlo_var_95: float


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {col.lower(): col for col in df.columns}
    required = ["open", "high", "low", "close"]
    missing = [col for col in required if col not in cols]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")
    return pd.DataFrame(
        {
            "time": df[cols.get("time", df.columns[0])],
            "open": df[cols["open"]].astype(float),
            "high": df[cols["high"]].astype(float),
            "low": df[cols["low"]].astype(float),
            "close": df[cols["close"]].astype(float),
            "volume": df[cols.get("volume", cols.get("tick_volume", df.columns[-1]))].astype(float),
        }
    )


def load_mt5(symbol: str, timeframe: str = "M15", bars: int = 5000) -> pd.DataFrame:
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed. Use --csv or install MetaTrader5 on Windows.") from exc
    tf = getattr(mt5, f"TIMEFRAME_{timeframe.upper()}")
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    mt5.shutdown()
    if rates is None:
        raise RuntimeError("No MT5 rates returned.")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.rename(columns={"tick_volume": "volume"}, inplace=True)
    return df[["time", "open", "high", "low", "close", "volume"]]


def run_strategy(df: pd.DataFrame, risk_per_trade: float = 0.02, min_rr: float = 1.5) -> pd.DataFrame:
    data = df.copy().reset_index(drop=True)
    data["ema9"] = data["close"].ewm(span=9, adjust=False).mean()
    data["ema21"] = data["close"].ewm(span=21, adjust=False).mean()
    data["ema200"] = data["close"].ewm(span=200, adjust=False).mean()
    data["atr"] = atr(data)
    trades = []
    equity = 1.0
    for i in range(220, len(data) - 10):
        row = data.iloc[i]
        prev = data.iloc[i - 1]
        direction = 0
        if prev.ema9 <= prev.ema21 and row.ema9 > row.ema21 and row.close > row.ema200:
            direction = 1
        elif prev.ema9 >= prev.ema21 and row.ema9 < row.ema21 and row.close < row.ema200:
            direction = -1
        if not direction:
            continue
        entry = float(row.close)
        sl_distance = max(float(row.atr) * 1.5, entry * 0.002)
        tp_distance = sl_distance * min_rr
        future = data.iloc[i + 1 : i + 11]
        if direction == 1:
            hit_tp = (future.high >= entry + tp_distance).idxmax() if (future.high >= entry + tp_distance).any() else None
            hit_sl = (future.low <= entry - sl_distance).idxmax() if (future.low <= entry - sl_distance).any() else None
        else:
            hit_tp = (future.low <= entry - tp_distance).idxmax() if (future.low <= entry - tp_distance).any() else None
            hit_sl = (future.high >= entry + sl_distance).idxmax() if (future.high >= entry + sl_distance).any() else None
        if hit_tp is not None and (hit_sl is None or hit_tp <= hit_sl):
            r = min_rr
        elif hit_sl is not None:
            r = -1.0
        else:
            exit_price = float(future.close.iloc[-1])
            raw = (exit_price - entry) / sl_distance * direction
            r = max(-1.0, min(min_rr, raw))
        equity *= 1 + r * risk_per_trade
        trades.append({"time": row.time, "direction": direction, "r": r, "equity": equity})
    return pd.DataFrame(trades)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]), (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean().bfill()


def metrics(trades: pd.DataFrame) -> BacktestReport:
    if trades.empty:
        return BacktestReport(0, 0, 0, 0, 0, 0, 0)
    returns = trades["equity"].pct_change().fillna(trades["equity"].iloc[0] - 1)
    downside = returns[returns < 0]
    equity = trades["equity"]
    drawdown = (equity.cummax() - equity) / equity.cummax()
    mc = monte_carlo(returns.to_numpy(), 1000)
    return BacktestReport(
        trades=len(trades),
        total_return=round((equity.iloc[-1] - 1) * 100, 2),
        sharpe=round(float(returns.mean() / (returns.std() or 1e-9) * np.sqrt(252)), 2),
        sortino=round(float(returns.mean() / (downside.std() or 1e-9) * np.sqrt(252)), 2),
        max_drawdown=round(float(drawdown.max() * 100), 2),
        win_rate=round(float((trades["r"] > 0).mean() * 100), 2),
        monte_carlo_var_95=round(float(np.percentile(mc, 5) * 100), 2),
    )


def monte_carlo(returns: np.ndarray, runs: int = 1000) -> np.ndarray:
    if len(returns) == 0:
        return np.array([0.0])
    outcomes = []
    for _ in range(runs):
        sample = np.random.choice(returns, size=len(returns), replace=True)
        outcomes.append(np.prod(1 + sample) - 1)
    return np.array(outcomes)


def walk_forward(df: pd.DataFrame, windows: int = 4) -> list[dict]:
    size = max(len(df) // windows, 1)
    splits = [df.iloc[i * size : (i + 1) * size].copy() for i in range(windows - 1)]
    splits.append(df.iloc[(windows - 1) * size :].copy())
    reports = []
    for i in range(1, len(splits)):
        test = splits[i]
        trades = run_strategy(test)
        reports.append(asdict(metrics(trades)))
    return reports


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--bars", type=int, default=5000)
    parser.add_argument("--output", default="backtest_report.json")
    args = parser.parse_args()
    df = load_csv(args.csv) if args.csv else load_mt5(args.symbol, args.timeframe, args.bars)
    trades = run_strategy(df)
    report = metrics(trades)
    output = {"main": asdict(report), "walk_forward": walk_forward(df)}
    Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
