from __future__ import annotations

import re


def parse_float(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", text.replace(" ", ""))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_price_triplet(text: str | None) -> tuple[float, float, float] | None:
    nums = re.findall(r"-?\d+(?:[.,]\d+)?", text or "")
    if len(nums) < 3:
        return None
    return tuple(float(n.replace(",", ".")) for n in nums[:3])  # type: ignore[return-value]
