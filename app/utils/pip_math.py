from __future__ import annotations


def calc_pips(symbol: str, entry: float, stop_loss: float) -> float:
    symbol = symbol.upper()
    multiplier = 1 if "XAU" in symbol or "GOLD" in symbol or "GC=" in symbol else 100
    return round(abs(float(entry) - float(stop_loss)) * multiplier, 2)


def validate_sl_pips(symbol: str, entry: float, stop_loss: float, max_pips: float = 70) -> bool:
    return calc_pips(symbol, entry, stop_loss) <= max_pips
