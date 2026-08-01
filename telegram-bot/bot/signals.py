"""فرمت و پارس سیگنال‌های معاملاتی."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


SIDE_BUY = {"buy", "long", "خرید", "لانگ", "بای"}
SIDE_SELL = {"sell", "short", "فروش", "شورت", "سل"}


@dataclass
class Signal:
    symbol: str
    side: str  # BUY | SELL
    entry: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    timeframe: str | None = None
    note: str | None = None
    source: str = "manual"

    @property
    def side_fa(self) -> str:
        return "خرید 🟢" if self.side == "BUY" else "فروش 🔴"

    def format_message(self) -> str:
        lines = [
            "📡 *سیگنال جدید*",
            "",
            f"جفت‌ارز: `{_escape(self.symbol)}`",
            f"جهت: *{_escape(self.side_fa)}*",
        ]
        if self.timeframe:
            lines.append(f"تایم‌فریم: `{_escape(self.timeframe)}`")
        if self.entry:
            lines.append(f"ورود: `{_escape(self.entry)}`")
        if self.stop_loss:
            lines.append(f"حد ضرر: `{_escape(self.stop_loss)}`")
        if self.take_profit:
            lines.append(f"حد سود: `{_escape(self.take_profit)}`")
        if self.note:
            lines.extend(["", f"یادداشت: {_escape(self.note)}"])
        lines.extend(["", f"_منبع: {_escape(self.source)}_"])
        return "\n".join(lines)


def _escape(text: str) -> str:
    """Escape MarkdownV2 special characters for Telegram."""
    specials = r"_*[]()~`>#+-=|{}.!"
    out = []
    for ch in str(text):
        if ch in specials:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def normalize_side(raw: str) -> str | None:
    key = raw.strip().lower()
    if key in SIDE_BUY:
        return "BUY"
    if key in SIDE_SELL:
        return "SELL"
    return None


def parse_manual_signal(text: str) -> Signal | None:
    """
    فرمت دستی:
    EURUSD BUY
    entry: 1.0850
    sl: 1.0800
    tp: 1.0950
    tf: M15
    note: ICT Judas
    """
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None

    first = re.split(r"\s+", lines[0], maxsplit=1)
    if len(first) < 2:
        return None
    symbol, side_raw = first[0], first[1]
    side = normalize_side(side_raw)
    if not side:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()

    return Signal(
        symbol=symbol.upper(),
        side=side,
        entry=fields.get("entry") or fields.get("ورود"),
        stop_loss=fields.get("sl") or fields.get("stop") or fields.get("حد ضرر"),
        take_profit=fields.get("tp") or fields.get("target") or fields.get("حد سود"),
        timeframe=fields.get("tf") or fields.get("timeframe") or fields.get("تایم"),
        note=fields.get("note") or fields.get("یادداشت"),
        source="manual",
    )


def parse_tradingview_payload(payload: Any) -> Signal | None:
    """پشتیبانی از JSON یا متن ساده TradingView webhook."""
    if isinstance(payload, str):
        text = payload.strip()
        # مثال: XAUUSD,BUY,entry=2350,sl=2340,tp=2370,tf=M5
        if "," in text and "\n" not in text:
            parts = [p.strip() for p in text.split(",")]
            if len(parts) < 2:
                return None
            side = normalize_side(parts[1])
            if not side:
                return None
            fields: dict[str, str] = {}
            for part in parts[2:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    fields[k.strip().lower()] = v.strip()
            return Signal(
                symbol=parts[0].upper(),
                side=side,
                entry=fields.get("entry"),
                stop_loss=fields.get("sl") or fields.get("stop"),
                take_profit=fields.get("tp") or fields.get("target"),
                timeframe=fields.get("tf") or fields.get("timeframe"),
                note=fields.get("note"),
                source="tradingview",
            )
        return parse_manual_signal(text)

    if not isinstance(payload, dict):
        return None

    symbol = str(
        payload.get("symbol")
        or payload.get("ticker")
        or payload.get("pair")
        or ""
    ).strip()
    side_raw = str(payload.get("side") or payload.get("action") or "").strip()
    side = normalize_side(side_raw)
    if not symbol or not side:
        return None

    return Signal(
        symbol=symbol.upper(),
        side=side,
        entry=_as_str(payload.get("entry") or payload.get("price")),
        stop_loss=_as_str(payload.get("sl") or payload.get("stop") or payload.get("stop_loss")),
        take_profit=_as_str(payload.get("tp") or payload.get("target") or payload.get("take_profit")),
        timeframe=_as_str(payload.get("tf") or payload.get("timeframe") or payload.get("interval")),
        note=_as_str(payload.get("note") or payload.get("message") or payload.get("strategy")),
        source="tradingview",
    )


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
