from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_engine import atr, load_csv, load_mt5_rates, rsi


def macd(close: pd.Series) -> pd.Series:
    line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = line.ewm(span=9, adjust=False).mean()
    return line - signal


def build_dataset(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    data = df.copy().reset_index(drop=True)
    data["rsi"] = rsi(data["close"])
    data["macd_hist"] = macd(data["close"])
    data["atr"] = atr(data)
    mid = data["close"].rolling(20).mean()
    std = data["close"].rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    data["bb_pos"] = (data["close"] - lower) / (upper - lower)
    data["volume_ratio"] = data["volume"] / data["volume"].rolling(20).mean().replace(0, np.nan)
    data["ema_fast"] = data["close"].ewm(span=9, adjust=False).mean()
    data["ema_slow"] = data["close"].ewm(span=21, adjust=False).mean()
    data["ema_trend"] = data["close"].ewm(span=200, adjust=False).mean()
    rows = []
    labels = []
    for i in range(220, len(data) - 10):
        row = data.iloc[i]
        future = data.iloc[i + 10].close
        threshold = max(row.atr, row.close * 0.001)
        label = 1
        if future - row.close > threshold:
            label = 2
        elif row.close - future > threshold:
            label = 0
        hour = pd.Timestamp(row.time).hour if "time" in data.columns else 0
        htf_bias = 1 if row.ema_fast > row.ema_slow > row.ema_trend else -1 if row.ema_fast < row.ema_slow < row.ema_trend else 0
        swing_high = data["high"].iloc[max(0, i - 60) : i].max()
        swing_low = data["low"].iloc[max(0, i - 60) : i].min()
        fib_zone = (swing_high - row.close) / max(swing_high - swing_low, 1e-9)
        features = [
            row.rsi / 100,
            np.clip((row.macd_hist + 0.005) / 0.01, 0, 1),
            np.clip(row.bb_pos, 0, 1) if np.isfinite(row.bb_pos) else 0.5,
            row.atr / row.close,
            np.nan_to_num(row.volume_ratio, nan=1.0),
            1.0,
            htf_bias,
            1 if 7 <= hour < 10 else 2 if 13 <= hour < 16 else 0,
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
            0,
            0,
            abs(swing_high - row.close) / max(row.atr, 1e-9) / 20,
            abs(row.close - swing_low) / max(row.atr, 1e-9) / 20,
            np.clip(fib_zone, 0, 1),
        ]
        rows.append(features)
        labels.append(label)
    return np.array(rows, dtype=np.float64), np.array(labels, dtype=np.int64)


class TinyNN:
    def __init__(self, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.05, (15, 32))
        self.b1 = np.zeros(32)
        self.w2 = rng.normal(0, 0.04, (32, 16))
        self.b2 = np.zeros(16)
        self.w3 = rng.normal(0, 0.05, (16, 3))
        self.b3 = np.zeros(3)

    def forward(self, x: np.ndarray) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
        h1 = np.maximum(0, x @ self.w1 + self.b1)
        h2 = np.maximum(0, h1 @ self.w2 + self.b2)
        logits = h2 @ self.w3 + self.b3
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        return exp / exp.sum(axis=1, keepdims=True), (h1, h2)

    def fit(self, x: np.ndarray, y: np.ndarray, epochs: int = 100, lr: float = 0.001) -> dict[str, float]:
        if len(x) == 0:
            return {"accuracy": 0.0, "loss": 0.0}
        y_one = np.eye(3)[y]
        best_acc = 0.0
        last_loss = 0.0
        for _ in range(epochs):
            probs, (h1, h2) = self.forward(x)
            loss_grad = (probs - y_one) / len(x)
            last_loss = float(-(y_one * np.log(probs + 1e-9)).sum() / len(x))
            dw3 = h2.T @ loss_grad
            db3 = loss_grad.sum(axis=0)
            dh2 = loss_grad @ self.w3.T
            dh2[h2 <= 0] = 0
            dw2 = h1.T @ dh2
            db2 = dh2.sum(axis=0)
            dh1 = dh2 @ self.w2.T
            dh1[h1 <= 0] = 0
            dw1 = x.T @ dh1
            db1 = dh1.sum(axis=0)
            self.w3 -= lr * dw3
            self.b3 -= lr * db3
            self.w2 -= lr * dw2
            self.b2 -= lr * db2
            self.w1 -= lr * dw1
            self.b1 -= lr * db1
            pred = probs.argmax(axis=1)
            best_acc = max(best_acc, float((pred == y).mean()))
        return {"accuracy": best_acc, "loss": last_loss}

    def save_mql_binary(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        values = [
            *self.w1.ravel(),
            *self.b1.ravel(),
            *self.w2.ravel(),
            *self.b2.ravel(),
            *self.w3.ravel(),
            *self.b3.ravel(),
        ]
        with Path(path).open("wb") as fh:
            for value in values:
                fh.write(struct.pack("<d", float(value)))


def arima_forecast(close: pd.Series, horizon: int = 3) -> float:
    diff = close.diff().dropna().tail(200)
    if len(diff) < 20:
        return 0.0
    mean = diff.mean()
    ar1 = diff.autocorr(1) or 0
    ar2 = diff.autocorr(2) or 0
    last1 = diff.iloc[-1]
    last2 = diff.iloc[-2]
    forecast = 0.0
    for _ in range(horizon):
        nxt = mean + ar1 * last1 + ar2 * last2
        forecast += nxt
        last2, last1 = last1, nxt
    return float(forecast)


def train(symbol: str, csv: str | None, output: str) -> dict[str, float]:
    df = load_csv(csv) if csv else load_mt5_rates(symbol, "H1", 180)
    x, y = build_dataset(df)
    if len(x) < 50:
        model = TinyNN()
        model.save_mql_binary(output)
        return {"accuracy": 0.0, "loss": 0.0, "samples": float(len(x))}
    split = int(len(x) * 0.8)
    model = TinyNN()
    report = model.fit(x[:split], y[:split])
    probs, _ = model.forward(x[split:])
    report["validation_accuracy"] = float((probs.argmax(axis=1) == y[split:]).mean()) if len(x[split:]) else 0.0
    report["samples"] = float(len(x))
    report["arima_next_3_bars"] = arima_forecast(df["close"])
    model.save_mql_binary(output)
    Path(output).with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--csv")
    parser.add_argument("--output", default="../Models/nn_model_weights.bin")
    args = parser.parse_args()
    print(json.dumps(train(args.symbol, args.csv, args.output), indent=2))


if __name__ == "__main__":
    main()
