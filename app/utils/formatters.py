from __future__ import annotations

from html import escape
from typing import Any

PREFIX = "<b>Pulsar💎 :</b>"


def h(value: Any) -> str:
    return escape("" if value is None else str(value), quote=False)


def pulsar(text: str) -> str:
    text = (text or "").strip()
    if text.startswith(PREFIX):
        return text
    return f"{PREFIX} {text}"


def price(value: float | int | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    if abs(value) >= 1000:
        return f"{value:,.2f}".replace(",", " ")
    return f"{value:.5f}".rstrip("0").rstrip(".")


def rr_text(value: float | None) -> str:
    return "—" if value is None else f"1:{float(value):.2f}".rstrip("0").rstrip(".")


def money(value: float | int | None) -> str:
    return "—" if value is None else f"${float(value):,.2f}".replace(",", " ")
