from __future__ import annotations

from io import BytesIO
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.utils.formatters import price


def render_chart_card(report: dict[str, Any], language: str | None = "uz") -> bytes:
    bias = str(report.get("bias", "neutral"))
    accent = _bias_color(bias)
    img, draw = _canvas(accent)
    _title(draw, "Pulsar AI", _label(language, "chart"))

    symbol = str(report.get("symbol", "XAUUSD"))
    current_price = price(report.get("price"))
    confidence = int(report.get("confidence") or 0)
    draw.text((64, 145), symbol, font=_font(48, bold=True), fill=(245, 247, 255))
    draw.text((64, 205), f"{current_price}  |  {bias.replace('_', ' ').upper()}", font=_font(27), fill=accent)
    _confidence(draw, confidence, accent, top=260)

    indicators = report.get("indicators", {}) or {}
    metrics = [
        ("RSI", indicators.get("rsi14", "-")),
        ("MACD", indicators.get("macd_histogram", "-")),
        ("ATR", price(indicators.get("atr14"))),
        ("VOL", f"{indicators.get('volume_ratio', '-')}x"),
    ]
    for idx, (name, value) in enumerate(metrics):
        _metric(draw, 64 + idx * 235, 345, name, str(value), accent)

    structure = report.get("market_structure", {}) or {}
    draw.text((64, 515), "Market Structure", font=_font(28, bold=True), fill=(245, 247, 255))
    draw.text(
        (64, 560),
        f"{structure.get('trend', 'neutral')} | BOS: {structure.get('bos', 'none')} | CHoCH: {structure.get('choch', 'none')}",
        font=_font(24),
        fill=(206, 213, 231),
    )

    levels = report.get("support_resistance", [])[:3]
    y = 625
    draw.text((64, y), "Nearest Levels", font=_font(28, bold=True), fill=(245, 247, 255))
    for item in levels:
        y += 38
        low = price(item.get("low"))
        high = price(item.get("high"))
        draw.text((80, y), f"{item.get('kind', 'level')}: {low} - {high}", font=_font(22), fill=(206, 213, 231))

    summary = str(report.get("summary", ""))
    _paragraph(draw, summary, 64, 805, 82, _font(21), (238, 241, 249))
    _footer(draw, "Risk first. No signal is guaranteed.")
    return _png(img)


def render_news_card(report: dict[str, Any], language: str | None = "uz") -> bytes:
    xau_bias = str(report.get("xauusd_bias", "neutral"))
    usd_bias = str(report.get("usd_bias", "neutral"))
    risk = str(report.get("risk_mood", "mixed"))
    accent = _bias_color(xau_bias if xau_bias != "neutral" else usd_bias)
    img, draw = _canvas(accent)
    _title(draw, "Pulsar AI", _label(language, "news"))

    mood = _mood_title(xau_bias, risk)
    draw.text((64, 148), mood, font=_font(45, bold=True), fill=(245, 247, 255))
    draw.text((64, 210), "USD, XAUUSD, BTC macro pulse", font=_font(25), fill=(206, 213, 231))
    _confidence(draw, int(report.get("confidence") or 0), accent, top=270)

    badges = [
        ("USD", usd_bias),
        ("XAUUSD", xau_bias),
        ("BTC", str(report.get("btc_bias", "neutral"))),
        ("Risk", risk),
    ]
    for idx, (name, value) in enumerate(badges):
        _metric(draw, 64 + idx * 235, 355, name, value.replace("_", " "), accent)

    draw.text((64, 530), "Top Market Drivers", font=_font(30, bold=True), fill=(245, 247, 255))
    y = 585
    for item in (report.get("key_news", []) or [])[:4]:
        for line in wrap(str(item.get("title", "")), width=66)[:2]:
            draw.text((80, y), line, font=_font(22), fill=(219, 225, 240))
            y += 29
        y += 13

    draw.text((64, 835), "Visual sentiment", font=_font(24, bold=True), fill=accent)
    draw.text((64, 870), _visual_phrase(xau_bias, risk), font=_font(22), fill=(235, 238, 247))
    _footer(draw, "News image is generated from live market context.")
    return _png(img)


def _canvas(accent: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    width, height = 1080, 1080
    img = Image.new("RGB", (width, height), (8, 12, 24))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(8 + accent[0] * 0.18 * ratio)
        g = int(12 + accent[1] * 0.12 * ratio)
        b = int(24 + accent[2] * 0.18 * ratio)
        draw.line((0, y, width, y), fill=(r, g, b))
    draw.rounded_rectangle((36, 36, width - 36, height - 36), radius=38, outline=(56, 64, 92), width=3)
    draw.ellipse((820, -120, 1220, 280), fill=tuple(max(0, min(255, int(c * 0.32))) for c in accent))
    draw.ellipse((-160, 760, 210, 1130), fill=tuple(max(0, min(255, int(c * 0.23))) for c in accent))
    return img, draw


def _title(draw: ImageDraw.ImageDraw, brand: str, subtitle: str) -> None:
    draw.text((64, 64), brand, font=_font(34, bold=True), fill=(245, 247, 255))
    draw.text((64, 104), subtitle, font=_font(21), fill=(165, 174, 199))


def _confidence(draw: ImageDraw.ImageDraw, confidence: int, accent: tuple[int, int, int], top: int) -> None:
    confidence = max(0, min(100, confidence))
    draw.rounded_rectangle((64, top, 1016, top + 28), radius=14, fill=(35, 42, 64))
    draw.rounded_rectangle((64, top, 64 + int(952 * confidence / 100), top + 28), radius=14, fill=accent)
    draw.text((64, top + 42), f"Confidence: {confidence}%", font=_font(22), fill=(218, 225, 242))


def _metric(draw: ImageDraw.ImageDraw, x: int, y: int, name: str, value: str, accent: tuple[int, int, int]) -> None:
    draw.rounded_rectangle((x, y, x + 205, y + 120), radius=20, fill=(18, 24, 42), outline=(52, 61, 88), width=2)
    draw.text((x + 20, y + 20), name, font=_font(20), fill=(160, 171, 198))
    draw.text((x + 20, y + 58), value[:18], font=_font(24, bold=True), fill=accent)


def _paragraph(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int, font: ImageFont.ImageFont, fill: tuple[int, int, int]) -> None:
    for line in wrap(text, width=width)[:6]:
        draw.text((x, y), line, font=font, fill=fill)
        y += 29


def _footer(draw: ImageDraw.ImageDraw, text: str) -> None:
    draw.text((64, 1002), text, font=_font(19), fill=(151, 160, 184))


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _bias_color(bias: str) -> tuple[int, int, int]:
    lower = bias.lower()
    if "bull" in lower or "risk_on" in lower:
        return (25, 210, 132)
    if "bear" in lower or "risk_off" in lower:
        return (255, 83, 112)
    return (245, 188, 66)


def _mood_title(xau_bias: str, risk: str) -> str:
    if "bull" in xau_bias:
        return "Gold Bulls Hold the Tape"
    if "bear" in xau_bias:
        return "Pressure Builds on Gold"
    if risk == "risk_off":
        return "Markets Seek Shelter"
    if risk == "risk_on":
        return "Risk Appetite Improves"
    return "Markets Wait for Clarity"


def _visual_phrase(xau_bias: str, risk: str) -> str:
    if "bull" in xau_bias:
        return "Buyers are defending value while macro pressure favors safe-haven demand."
    if "bear" in xau_bias:
        return "Dollar/yield pressure keeps gold buyers careful and selective."
    if risk == "risk_off":
        return "Investors are cautious; liquidity prefers defensive positioning."
    if risk == "risk_on":
        return "Investors are more confident; growth assets attract attention."
    return "Conviction is mixed; patience around key levels matters."


def _label(language: str | None, kind: str) -> str:
    if language == "ru":
        return "Визуальный анализ графика" if kind == "chart" else "Визуальный фундаментальный обзор"
    if language == "en":
        return "Visual chart intelligence" if kind == "chart" else "Visual fundamental pulse"
    return "Vizual grafik razvedka" if kind == "chart" else "Vizual fundamental puls"


def _png(img: Image.Image) -> bytes:
    output = BytesIO()
    img.save(output, format="PNG", optimize=True)
    return output.getvalue()
