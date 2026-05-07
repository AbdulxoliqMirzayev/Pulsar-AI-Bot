from __future__ import annotations

import csv
import json
import os
import socket
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


try:
    from transformers import pipeline
except Exception:  # noqa: BLE001
    pipeline = None


CURRENCY_KEYWORDS = {
    "USD": ["federal reserve", "fed", "fomc", "dollar", "us economy", "inflation", "cpi", "nfp", "treasury"],
    "EUR": ["ecb", "euro", "european central bank", "eurozone", "lagarde"],
    "GBP": ["bank of england", "boe", "pound", "sterling", "uk economy"],
    "JPY": ["bank of japan", "boj", "yen", "nikkei"],
    "XAU": ["gold", "safe haven", "risk off", "treasury yields"],
    "BTC": ["bitcoin", "btc", "crypto", "etf inflows", "halving"],
}

POSITIVE = {"strong", "beat", "hawkish", "higher yields", "growth", "rally", "surge", "risk-on", "inflows", "hot"}
NEGATIVE = {"weak", "miss", "dovish", "rate cut", "recession", "selloff", "risk-off", "war", "stress", "cooling"}


def load_finbert():
    if pipeline is None:
        return None
    try:
        return pipeline("text-classification", model="ProsusAI/finbert", top_k=None)
    except Exception:
        return None


SENTIMENT_MODEL = load_finbert()


def http_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AlgoBot/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def parse_symbol(symbol: str) -> tuple[str, str]:
    s = symbol.upper().replace("/", "")
    if s.startswith("XAU"):
        return "XAU", "USD"
    if s.startswith("BTC"):
        return "BTC", "USD"
    return s[:3], s[3:6] if len(s) >= 6 else "USD"


def is_about_currency(text: str, currency: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in CURRENCY_KEYWORDS.get(currency, [currency.lower()]))


def fetch_news(currency: str, limit: int = 20) -> list[dict]:
    newsapi_key = os.getenv("NEWSAPI_KEY", "")
    finnhub_key = os.getenv("FINNHUB_API_KEY", "")
    query = " OR ".join(CURRENCY_KEYWORDS.get(currency, [currency]))
    items: list[dict] = []
    if newsapi_key:
        url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(
            {
                "q": query,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": limit,
                "apiKey": newsapi_key,
            }
        )
        try:
            items.extend(http_json(url).get("articles", []))
        except Exception as exc:
            print(f"NewsAPI failed: {exc}")
    if finnhub_key:
        url = f"https://finnhub.io/api/v1/news?category=forex&token={finnhub_key}"
        try:
            items.extend(http_json(url)[:limit])
        except Exception as exc:
            print(f"Finnhub failed: {exc}")
    return items[:limit]


def score_text(text: str) -> float:
    if SENTIMENT_MODEL is not None:
        try:
            result = SENTIMENT_MODEL(text[:512])[0]
            pos = next((r["score"] for r in result if r["label"].lower() == "positive"), 0.0)
            neg = next((r["score"] for r in result if r["label"].lower() == "negative"), 0.0)
            return float(pos - neg)
        except Exception:
            pass
    lower = text.lower()
    pos = sum(term in lower for term in POSITIVE)
    neg = sum(term in lower for term in NEGATIVE)
    if pos + neg == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / max(pos + neg, 1)))


def write_sentiment_for_mt5(symbol: str, score: float) -> None:
    path = Path("../Config/sentiment.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, float] = {}
    if path.exists():
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if len(row) >= 2:
                    rows[row[0]] = float(row[1])
    rows[symbol.upper()] = round(score, 5)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for key, value in sorted(rows.items()):
            writer.writerow([key, value])


def get_sentiment_score(symbol: str) -> float:
    base, quote = parse_symbol(symbol)
    news_items = fetch_news(base) + fetch_news(quote)
    if not news_items:
        write_sentiment_for_mt5(symbol, 0.0)
        return 0.0
    scores = []
    for item in news_items:
        title = item.get("title") or item.get("headline") or ""
        desc = item.get("description") or item.get("summary") or ""
        text = f"{title} {desc}"
        score = score_text(text)
        if is_about_currency(text, quote):
            score = -score
        scores.append(score)
    final = max(-1.0, min(1.0, sum(scores) / len(scores)))
    write_sentiment_for_mt5(symbol, final)
    return final


def check_high_impact_news(minutes_ahead: int = 30) -> bool:
    key = os.getenv("TRADING_ECONOMICS_KEY", "guest:guest")
    now = datetime.now(timezone.utc)
    end = now + timedelta(minutes=minutes_ahead)
    url = "https://api.tradingeconomics.com/calendar/country/united%20states?" + urllib.parse.urlencode({"c": key, "importance": "3"})
    try:
        events = http_json(url)
    except Exception:
        return False
    for event in events:
        raw = event.get("Date") or event.get("date")
        if not raw:
            continue
        try:
            event_time = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if now <= event_time <= end:
            return True
    return False


def handle_client(conn: socket.socket) -> None:
    with conn:
        data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
        if not data:
            return
        if data.startswith("NEWS?"):
            minutes = int(data.split("?", 1)[1] or 30)
            conn.sendall(("1" if check_high_impact_news(minutes) else "0").encode())
            return
        score = get_sentiment_score(data)
        conn.sendall(str(score).encode())


def run_sentiment_server(host: str = "127.0.0.1", port: int = 9999) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(20)
    print(f"Sentiment server running on {host}:{port}")
    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    run_sentiment_server()
