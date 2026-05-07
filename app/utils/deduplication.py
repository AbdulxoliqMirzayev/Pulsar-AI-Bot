from __future__ import annotations

import hashlib
from urllib.parse import urlparse


def news_hash(title: str, url: str | None = None, source: str | None = None) -> str:
    domain = urlparse(url or "").netloc or (source or "")
    return hashlib.sha256(f"{title.strip().lower()}|{domain.lower()}".encode()).hexdigest()[:16]


def deduplicate_news(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    output: list[dict] = []
    for item in items:
        title = item.get("title") or ""
        if not title:
            continue
        key = news_hash(title, item.get("url"), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        output.append({**item, "hash_key": key})
    return output
