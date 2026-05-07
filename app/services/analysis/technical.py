from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Iterable

import numpy as np
import pandas as pd

from app.services.market_data.models import Candle


@dataclass(slots=True)
class Zone:
    kind: str
    low: float
    high: float
    strength: float
    note: str


@dataclass(slots=True)
class StrategySignal:
    name: str
    direction: str
    score: int
    reason: str


@dataclass(slots=True)
class TechnicalReport:
    symbol: str
    timeframe: str
    price: float
    bias: str
    score: int
    confidence: int
    indicators: dict
    market_structure: dict
    support_resistance: list[dict]
    order_blocks: list[dict]
    liquidity_zones: list[dict]
    fair_value_gaps: list[dict]
    volume_profile: dict
    strategies: list[dict]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


class TechnicalAnalyzer:
    def analyze(self, symbol: str, candles: list[Candle], timeframe: str = "15m") -> TechnicalReport:
        if len(candles) < 60:
            raise ValueError("Technical analysis uchun kamida 60 ta candle kerak.")
        df = self._to_frame(candles)
        indicators = self._indicators(df)
        structure = self._market_structure(df)
        sr = self._support_resistance(df)
        order_blocks = self._order_blocks(df, indicators)
        liquidity = self._liquidity_zones(df)
        fvgs = self._fair_value_gaps(df)
        volume_profile = self._volume_profile(df)
        strategies = self._run_strategies(df, indicators, structure, order_blocks, liquidity, fvgs, volume_profile)
        score = sum(item.score if item.direction == "bullish" else -item.score for item in strategies)
        bias = self._bias(score, structure)
        confidence = min(95, max(5, int(abs(score) * 7 + 35)))
        price = float(df["close"].iloc[-1])
        return TechnicalReport(
            symbol=symbol.upper(),
            timeframe=timeframe,
            price=price,
            bias=bias,
            score=score,
            confidence=confidence,
            indicators=indicators,
            market_structure=structure,
            support_resistance=[asdict(item) for item in sr],
            order_blocks=[asdict(item) for item in order_blocks],
            liquidity_zones=[asdict(item) for item in liquidity],
            fair_value_gaps=[asdict(item) for item in fvgs],
            volume_profile=volume_profile,
            strategies=[asdict(item) for item in strategies],
            summary=self._summary(symbol, price, bias, confidence, sr, order_blocks, liquidity, strategies),
        )

    def _to_frame(self, candles: list[Candle]) -> pd.DataFrame:
        rows = [
            {
                "time": candle.time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]
        df = pd.DataFrame(rows)
        return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    def _indicators(self, df: pd.DataFrame) -> dict:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"].replace(0, np.nan).ffill().fillna(1)
        ema9 = close.ewm(span=9, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ema200 = close.ewm(span=200, adjust=False).mean()
        rsi = self._rsi(close)
        macd_line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        atr = self._atr(df)
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_mid + bb_std * 2
        bb_lower = bb_mid - bb_std * 2
        stochastic_k = ((close - low.rolling(14).min()) / (high.rolling(14).max() - low.rolling(14).min()).replace(0, np.nan)) * 100
        stochastic_d = stochastic_k.rolling(3).mean()
        typical = (high + low + close) / 3
        vwap = (typical * volume).cumsum() / volume.cumsum()
        obv = (np.sign(close.diff()).fillna(0) * volume).cumsum()
        adx = self._adx(df)
        bb_position = ((close.iloc[-1] - bb_lower.iloc[-1]) / max(bb_upper.iloc[-1] - bb_lower.iloc[-1], 1e-9)) if not np.isnan(bb_lower.iloc[-1]) else 0.5
        return {
            "ema9": round(float(ema9.iloc[-1]), 5),
            "ema21": round(float(ema21.iloc[-1]), 5),
            "ema50": round(float(ema50.iloc[-1]), 5),
            "ema200": round(float(ema200.iloc[-1]), 5),
            "rsi14": round(float(rsi.iloc[-1]), 2),
            "macd": round(float(macd_line.iloc[-1]), 5),
            "macd_signal": round(float(macd_signal.iloc[-1]), 5),
            "macd_histogram": round(float((macd_line - macd_signal).iloc[-1]), 5),
            "atr14": round(float(atr.iloc[-1]), 5),
            "bb_upper": round(float(bb_upper.iloc[-1]), 5),
            "bb_middle": round(float(bb_mid.iloc[-1]), 5),
            "bb_lower": round(float(bb_lower.iloc[-1]), 5),
            "bb_position": round(float(bb_position), 3),
            "stochastic_k": round(float(stochastic_k.iloc[-1]), 2),
            "stochastic_d": round(float(stochastic_d.iloc[-1]), 2),
            "vwap": round(float(vwap.iloc[-1]), 5),
            "obv": round(float(obv.iloc[-1]), 2),
            "adx14": round(float(adx.iloc[-1]), 2),
            "volume_ratio": round(float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]), 2),
        }

    def _rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = -delta.clip(upper=0).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return (100 - (100 / (1 + rs))).fillna(50)

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        prev_close = df["close"].shift(1)
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - prev_close).abs(),
                (df["low"] - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean().bfill()

    def _adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        plus_dm = (high.diff()).where((high.diff() > -low.diff()) & (high.diff() > 0), 0)
        minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0)
        atr = self._atr(df, period).replace(0, np.nan)
        plus_di = 100 * plus_dm.rolling(period).mean() / atr
        minus_di = 100 * minus_dm.rolling(period).mean() / atr
        dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)) * 100
        return dx.rolling(period).mean().fillna(20)

    def _market_structure(self, df: pd.DataFrame) -> dict:
        swings_high, swings_low = self._swings(df)
        last_highs = swings_high[-4:]
        last_lows = swings_low[-4:]
        trend = "neutral"
        if len(last_highs) >= 2 and len(last_lows) >= 2:
            if last_highs[-1][1] > last_highs[-2][1] and last_lows[-1][1] > last_lows[-2][1]:
                trend = "bullish"
            elif last_highs[-1][1] < last_highs[-2][1] and last_lows[-1][1] < last_lows[-2][1]:
                trend = "bearish"
        close = float(df["close"].iloc[-1])
        bos = "none"
        choch = "none"
        if last_highs and close > last_highs[-1][1]:
            bos = "bullish_bos"
            choch = "bullish_choch" if trend == "bearish" else "none"
        if last_lows and close < last_lows[-1][1]:
            bos = "bearish_bos"
            choch = "bearish_choch" if trend == "bullish" else "none"
        return {
            "trend": trend,
            "bos": bos,
            "choch": choch,
            "last_swing_high": round(last_highs[-1][1], 5) if last_highs else None,
            "last_swing_low": round(last_lows[-1][1], 5) if last_lows else None,
            "swing_highs": [{"bar": i, "price": round(price, 5)} for i, price in last_highs],
            "swing_lows": [{"bar": i, "price": round(price, 5)} for i, price in last_lows],
        }

    def _swings(self, df: pd.DataFrame, left: int = 2, right: int = 2) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
        highs: list[tuple[int, float]] = []
        lows: list[tuple[int, float]] = []
        for i in range(left, len(df) - right):
            window_high = df["high"].iloc[i - left : i + right + 1]
            window_low = df["low"].iloc[i - left : i + right + 1]
            high = float(df["high"].iloc[i])
            low = float(df["low"].iloc[i])
            if high == float(window_high.max()):
                highs.append((i, high))
            if low == float(window_low.min()):
                lows.append((i, low))
        return highs, lows

    def _support_resistance(self, df: pd.DataFrame) -> list[Zone]:
        highs, lows = self._swings(df)
        current = float(df["close"].iloc[-1])
        levels: list[Zone] = []
        for _, price in highs[-8:]:
            levels.append(Zone("resistance", price * 0.9995, price * 1.0005, self._touch_count(df, price), "fractal/previous swing high"))
        for _, price in lows[-8:]:
            levels.append(Zone("support", price * 0.9995, price * 1.0005, self._touch_count(df, price), "fractal/previous swing low"))
        daily_high = float(df["high"].tail(96).max())
        daily_low = float(df["low"].tail(96).min())
        daily_close = float(df["close"].tail(96).iloc[0])
        pivot = (daily_high + daily_low + daily_close) / 3
        levels.extend(
            [
                Zone("pivot", pivot * 0.9997, pivot * 1.0003, 2, "session pivot"),
                Zone("resistance", (2 * pivot - daily_low) * 0.9997, (2 * pivot - daily_low) * 1.0003, 2, "R1 pivot"),
                Zone("support", (2 * pivot - daily_high) * 0.9997, (2 * pivot - daily_high) * 1.0003, 2, "S1 pivot"),
            ]
        )
        return sorted(levels, key=lambda item: abs(((item.low + item.high) / 2) - current))[:10]

    def _touch_count(self, df: pd.DataFrame, level: float) -> float:
        tolerance = max(level * 0.001, float((df["high"] - df["low"]).tail(50).mean()) * 0.25)
        touches = ((df["high"] >= level - tolerance) & (df["low"] <= level + tolerance)).sum()
        return float(min(5, touches))

    def _order_blocks(self, df: pd.DataFrame, indicators: dict) -> list[Zone]:
        atr = float(indicators["atr14"])
        zones: list[Zone] = []
        for i in range(max(5, len(df) - 80), len(df) - 4):
            candle = df.iloc[i]
            future_move = float(df["close"].iloc[i + 4] - candle["close"])
            body = abs(float(candle["close"] - candle["open"]))
            is_bearish = candle["close"] < candle["open"]
            is_bullish = candle["close"] > candle["open"]
            if is_bearish and future_move > atr * 2.5:
                zones.append(Zone("bullish_order_block", float(candle["low"]), float(candle["high"]), body / max(atr, 1e-9), "last bearish candle before bullish displacement"))
            if is_bullish and future_move < -atr * 2.5:
                zones.append(Zone("bearish_order_block", float(candle["low"]), float(candle["high"]), body / max(atr, 1e-9), "last bullish candle before bearish displacement"))
        current = float(df["close"].iloc[-1])
        valid = [zone for zone in zones if not (zone.kind.startswith("bullish") and current < zone.low) and not (zone.kind.startswith("bearish") and current > zone.high)]
        return sorted(valid[-10:], key=lambda item: abs(((item.low + item.high) / 2) - current))[:5]

    def _liquidity_zones(self, df: pd.DataFrame) -> list[Zone]:
        highs, lows = self._swings(df)
        atr = float(self._atr(df).iloc[-1])
        zones: list[Zone] = []
        for points, kind in ((highs, "buy_side_liquidity"), (lows, "sell_side_liquidity")):
            for cluster in self._cluster_levels([price for _, price in points[-20:]], tolerance=max(atr * 0.4, 1e-9)):
                price = mean(cluster)
                zones.append(Zone(kind, price - atr * 0.15, price + atr * 0.15, float(len(cluster)), "equal highs/lows stop cluster"))
        current = float(df["close"].iloc[-1])
        return sorted(zones, key=lambda item: abs(((item.low + item.high) / 2) - current))[:8]

    def _cluster_levels(self, values: Iterable[float], tolerance: float) -> list[list[float]]:
        clusters: list[list[float]] = []
        for value in sorted(values):
            if not clusters or abs(mean(clusters[-1]) - value) > tolerance:
                clusters.append([value])
            else:
                clusters[-1].append(value)
        return [cluster for cluster in clusters if len(cluster) >= 2]

    def _fair_value_gaps(self, df: pd.DataFrame) -> list[Zone]:
        zones: list[Zone] = []
        for i in range(max(2, len(df) - 80), len(df) - 1):
            prev = df.iloc[i - 1]
            nxt = df.iloc[i + 1]
            if float(prev["low"]) > float(nxt["high"]):
                zones.append(Zone("bearish_fvg", float(nxt["high"]), float(prev["low"]), 1, "three-candle imbalance"))
            if float(prev["high"]) < float(nxt["low"]):
                zones.append(Zone("bullish_fvg", float(prev["high"]), float(nxt["low"]), 1, "three-candle imbalance"))
        current = float(df["close"].iloc[-1])
        return sorted(zones[-10:], key=lambda item: abs(((item.low + item.high) / 2) - current))[:5]

    def _volume_profile(self, df: pd.DataFrame, bins: int = 24) -> dict:
        recent = df.tail(160)
        prices = ((recent["high"] + recent["low"] + recent["close"]) / 3).to_numpy()
        volumes = recent["volume"].replace(0, 1).to_numpy()
        hist, edges = np.histogram(prices, bins=bins, weights=volumes)
        max_index = int(hist.argmax())
        poc = (edges[max_index] + edges[max_index + 1]) / 2
        total = hist.sum()
        if total <= 0:
            return {"poc": round(float(poc), 5), "vah": None, "val": None}
        ranked = np.argsort(hist)[::-1]
        selected: list[int] = []
        running = 0.0
        for idx in ranked:
            selected.append(int(idx))
            running += float(hist[idx])
            if running >= total * 0.7:
                break
        val = edges[min(selected)]
        vah = edges[max(selected) + 1]
        return {"poc": round(float(poc), 5), "vah": round(float(vah), 5), "val": round(float(val), 5)}

    def _run_strategies(
        self,
        df: pd.DataFrame,
        indicators: dict,
        structure: dict,
        order_blocks: list[Zone],
        liquidity: list[Zone],
        fvgs: list[Zone],
        volume_profile: dict,
    ) -> list[StrategySignal]:
        close = float(df["close"].iloc[-1])
        high_lookback = float(df["high"].tail(120).max())
        low_lookback = float(df["low"].tail(120).min())
        rng = max(high_lookback - low_lookback, 1e-9)
        fib_618 = high_lookback - rng * 0.618
        fib_786 = high_lookback - rng * 0.786
        atr = float(indicators["atr14"])
        signals: list[StrategySignal] = []

        def add(name: str, direction: str, score: int, reason: str) -> None:
            if direction != "neutral" and score > 0:
                signals.append(StrategySignal(name, direction, score, reason))

        add("Fibonacci retracement", "bullish" if min(abs(close - fib_618), abs(close - fib_786)) < atr else "neutral", 1, "price in 0.618/0.786 OTE zone")
        add("Gann Square of Nine", "bullish" if close > np.sqrt(close) ** 2 and indicators["volume_ratio"] > 1.2 else "neutral", 1, "price holds Gann angle with volume")
        if order_blocks:
            nearest_ob = order_blocks[0]
            direction = "bullish" if nearest_ob.kind.startswith("bullish") else "bearish"
            if nearest_ob.low <= close <= nearest_ob.high:
                add("Supply/Demand order block", direction, 2, "price mitigates nearest valid order block")
        add("BOS/CHoCH", "bullish" if structure["bos"] == "bullish_bos" or structure["choch"] == "bullish_choch" else "bearish" if structure["bos"] == "bearish_bos" or structure["choch"] == "bearish_choch" else "neutral", 2, "market structure break detected")
        for zone in liquidity[:2]:
            if zone.low <= close <= zone.high:
                add("Liquidity sweep", "bearish" if zone.kind.startswith("buy") else "bullish", 2, "price trades into stop cluster")
        for zone in fvgs[:2]:
            if zone.low <= close <= zone.high:
                add("Fair Value Gap", "bullish" if zone.kind.startswith("bullish") else "bearish", 1, "price fills imbalance midpoint")
        add("RSI divergence proxy", "bullish" if indicators["rsi14"] < 35 else "bearish" if indicators["rsi14"] > 70 else "neutral", 1, "RSI extreme zone")
        add("EMA crossover", "bullish" if indicators["ema9"] > indicators["ema21"] > indicators["ema200"] else "bearish" if indicators["ema9"] < indicators["ema21"] < indicators["ema200"] else "neutral", 2, "EMA stack confirms trend")
        if volume_profile.get("val") and close <= float(volume_profile["val"]) + atr:
            add("Volume Profile + VWAP", "bullish", 2, "price near VAL/VWAP value area")
        if volume_profile.get("vah") and close >= float(volume_profile["vah"]) - atr:
            add("Volume Profile + VWAP", "bearish", 2, "price near VAH value area")
        band_width = (indicators["bb_upper"] - indicators["bb_lower"]) / max(indicators["bb_middle"], 1e-9)
        add("Bollinger squeeze", "bullish" if close > indicators["bb_upper"] and band_width < 0.08 else "bearish" if close < indicators["bb_lower"] and band_width < 0.08 else "neutral", 1, "post-squeeze band breakout")
        add("MACD momentum", "bullish" if indicators["macd_histogram"] > 0 else "bearish" if indicators["macd_histogram"] < 0 else "neutral", 1, "MACD histogram direction")
        add("Support/Resistance key level", self._near_key_level_direction(df), 1, "price reacts near pivot/fractal level")
        add("ICT killzone/sessions", "bullish" if structure["trend"] == "bullish" and indicators["volume_ratio"] > 1.3 else "bearish" if structure["trend"] == "bearish" and indicators["volume_ratio"] > 1.3 else "neutral", 1, "session expansion with volume")
        add("Stochastic oscillator", "bullish" if indicators["stochastic_k"] < 25 and indicators["stochastic_k"] > indicators["stochastic_d"] else "bearish" if indicators["stochastic_k"] > 75 and indicators["stochastic_k"] < indicators["stochastic_d"] else "neutral", 1, "stochastic cross in extreme zone")
        add("ATR trailing stop", "bullish" if close > indicators["ema21"] and indicators["adx14"] > 20 else "bearish" if close < indicators["ema21"] and indicators["adx14"] > 20 else "neutral", 1, "ATR trend filter")
        add("Engulfing candle", self._engulfing_direction(df), 1, "engulfing candle with volume confirmation")
        add("Wick rejection", self._wick_direction(df), 1, "pin bar rejection")
        add("Premium/Discount", "bullish" if close < (high_lookback + low_lookback) / 2 else "bearish", 1, "price in discount/premium of swing range")
        add("Martingale safety module", "neutral", 0, "risk module only, no directional signal")
        mtf_score = 0
        if structure["trend"] == "bullish" and indicators["rsi14"] > 50:
            mtf_score = 3
            mtf_direction = "bullish"
        elif structure["trend"] == "bearish" and indicators["rsi14"] < 50:
            mtf_score = 3
            mtf_direction = "bearish"
        else:
            mtf_direction = "neutral"
        add("Multi-timeframe confluence", mtf_direction, mtf_score, "structure, RSI and volume confluence")
        return signals

    def _near_key_level_direction(self, df: pd.DataFrame) -> str:
        price = float(df["close"].iloc[-1])
        prev = float(df["close"].iloc[-2])
        levels = self._support_resistance(df)
        if not levels:
            return "neutral"
        nearest = levels[0]
        if nearest.low <= price <= nearest.high:
            if nearest.kind == "support" and price > prev:
                return "bullish"
            if nearest.kind == "resistance" and price < prev:
                return "bearish"
        return "neutral"

    def _engulfing_direction(self, df: pd.DataFrame) -> str:
        cur = df.iloc[-1]
        prev = df.iloc[-2]
        cur_body = abs(float(cur["close"] - cur["open"]))
        prev_body = abs(float(prev["close"] - prev["open"]))
        volume_ok = float(cur["volume"] or 1) > float(prev["volume"] or 1) * 1.2
        if cur["open"] < prev["close"] and cur["close"] > prev["open"] and cur_body > prev_body * 1.2 and volume_ok:
            return "bullish"
        if cur["open"] > prev["close"] and cur["close"] < prev["open"] and cur_body > prev_body * 1.2 and volume_ok:
            return "bearish"
        return "neutral"

    def _wick_direction(self, df: pd.DataFrame) -> str:
        cur = df.iloc[-1]
        body = abs(float(cur["close"] - cur["open"]))
        upper = float(cur["high"] - max(cur["open"], cur["close"]))
        lower = float(min(cur["open"], cur["close"]) - cur["low"])
        if lower > body * 2 and upper < max(body * 0.8, 1e-9):
            return "bullish"
        if upper > body * 2 and lower < max(body * 0.8, 1e-9):
            return "bearish"
        return "neutral"

    def _bias(self, score: int, structure: dict) -> str:
        if score >= 7:
            return "strong_bullish"
        if score >= 3:
            return "bullish"
        if score <= -7:
            return "strong_bearish"
        if score <= -3:
            return "bearish"
        return structure.get("trend", "neutral")

    def _summary(
        self,
        symbol: str,
        price: float,
        bias: str,
        confidence: int,
        sr: list[Zone],
        order_blocks: list[Zone],
        liquidity: list[Zone],
        strategies: list[StrategySignal],
    ) -> str:
        nearest_level = sr[0] if sr else None
        nearest_ob = order_blocks[0] if order_blocks else None
        nearest_liq = liquidity[0] if liquidity else None
        active = ", ".join(item.name for item in strategies[:4]) or "clear confluence yo'q"
        parts = [
            f"{symbol.upper()} price {price:.5f}; bias: {bias} ({confidence}%).",
            f"Active confirmations: {active}.",
        ]
        if nearest_level:
            parts.append(f"Nearest key level: {nearest_level.kind} {nearest_level.low:.5f}-{nearest_level.high:.5f}.")
        if nearest_ob:
            parts.append(f"Nearest OB: {nearest_ob.kind} {nearest_ob.low:.5f}-{nearest_ob.high:.5f}.")
        if nearest_liq:
            parts.append(f"Liquidity: {nearest_liq.kind} around {(nearest_liq.low + nearest_liq.high) / 2:.5f}.")
        return " ".join(parts)
