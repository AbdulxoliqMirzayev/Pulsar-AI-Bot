from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.utils.formatters import pulsar

LOCALE_DIR = Path(__file__).resolve().parents[1] / "locales"


@lru_cache(maxsize=8)
def load_locale(language: str) -> dict[str, Any]:
    path = LOCALE_DIR / f"{language}.json"
    if not path.exists():
        path = LOCALE_DIR / "uz.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(language: str | None, key: str, **kwargs: Any) -> str:
    data = load_locale(language or "uz")
    value: Any = data
    for part in key.split("."):
        value = value.get(part, {}) if isinstance(value, dict) else {}
    if not isinstance(value, str):
        value = key
    return value.format(**kwargs)


def pt(language: str | None, key: str, **kwargs: Any) -> str:
    return pulsar(t(language, key, **kwargs))
