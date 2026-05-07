from __future__ import annotations


def calc_rr(entry: float, sl: float, tp: float) -> float:
    risk = abs(float(entry) - float(sl))
    reward = abs(float(tp) - float(entry))
    if risk <= 0:
        return 0.0
    return round(reward / risk, 4)


def check_min_rr(rr: float, min_rr: float = 1.5) -> bool:
    return float(rr) >= float(min_rr)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
