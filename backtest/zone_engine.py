"""Zone-based signal simulation for FVG / OB / IFVG indicators."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine import Trade, aggregate, BacktestResult
from indicators import atr_wilder, ema, sma, crossover, crossunder, true_range


@dataclass
class ZoneSignal:
    bar: int
    direction: str  # long | short
    entry: float
    sl: float | None = None
    tp: float | None = None
    meta: str = ""


def pivot_high(series: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(np.nan, index=series.index)
    vals = series.values
    n = len(series)
    for i in range(left + right, n):
        c = i - right
        w = vals[c - left : c + right + 1]
        if len(w) == left + right + 1 and vals[c] == w.max():
            out.iloc[i] = vals[c]
    return out


def pivot_low(series: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(np.nan, index=series.index)
    vals = series.values
    n = len(series)
    for i in range(left + right, n):
        c = i - right
        w = vals[c - left : c + right + 1]
        if len(w) == left + right + 1 and vals[c] == w.min():
            out.iloc[i] = vals[c]
    return out


def signals_to_df(df: pd.DataFrame, signals: list[ZoneSignal]) -> pd.DataFrame:
    out = df.copy()
    buy = np.zeros(len(df), dtype=bool)
    sell = np.zeros(len(df), dtype=bool)
    entry_p = np.full(len(df), np.nan)
    sl_p = np.full(len(df), np.nan)
    tp_p = np.full(len(df), np.nan)
    for s in signals:
        if s.direction == "long":
            buy[s.bar] = True
        else:
            sell[s.bar] = True
        entry_p[s.bar] = s.entry
        if s.sl is not None:
            sl_p[s.bar] = s.sl
        if s.tp is not None:
            tp_p[s.bar] = s.tp
    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = entry_p
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    return out


def simulate_zone_native(
    df: pd.DataFrame,
    signals: list[ZoneSignal],
    market: str,
    max_bars: int = 300,
    cost_pct: float = 0.001,
) -> list[Trade]:
    """Simulate trades using per-signal SL/TP when provided."""
    if not signals:
        return []
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    trades: list[Trade] = []
    position = 0
    entry_price = sl_price = tp_price = 0.0
    entry_bar = 0
    risk = 0.0

    sig_by_bar: dict[int, list[ZoneSignal]] = {}
    for s in signals:
        sig_by_bar.setdefault(s.bar, []).append(s)

    def close_trade(bar: int, price: float, reason: str):
        nonlocal position, entry_price, entry_bar, sl_price, tp_price, risk
        if position == 0:
            return
        if position == 1:
            r_mult = (price - entry_price) / risk if risk > 0 else 0
        else:
            r_mult = (entry_price - price) / risk if risk > 0 else 0
        trades.append(
            Trade(
                direction="long" if position == 1 else "short",
                entry_bar=entry_bar,
                entry_price=entry_price,
                exit_bar=bar,
                exit_price=price,
                outcome="win" if r_mult > 0 else "loss",
                bars_held=bar - entry_bar,
                r_multiple=r_mult,
                exit_reason=reason,
            )
        )
        position = 0

    for i in range(n):
        if position != 0:
            if position == 1:
                if lows[i] <= sl_price:
                    close_trade(i, sl_price, "sl")
                elif highs[i] >= tp_price:
                    close_trade(i, tp_price, "tp")
                elif i - entry_bar >= max_bars:
                    close_trade(i, closes[i], "timeout")
            else:
                if highs[i] >= sl_price:
                    close_trade(i, sl_price, "sl")
                elif lows[i] <= tp_price:
                    close_trade(i, tp_price, "tp")
                elif i - entry_bar >= max_bars:
                    close_trade(i, closes[i], "timeout")

        for s in sig_by_bar.get(i, []):
            if position != 0:
                close_trade(i, closes[i], "flip")
            position = 1 if s.direction == "long" else -1
            entry_bar = i
            entry_price = s.entry if s.entry > 0 else closes[i]
            if s.sl is not None and s.tp is not None:
                sl_price, tp_price = s.sl, s.tp
                risk = abs(entry_price - sl_price)
            else:
                risk = abs(entry_price * 0.05)
                sl_price = entry_price - risk if position == 1 else entry_price + risk
                tp_price = entry_price + risk if position == 1 else entry_price - risk
            if risk <= 0:
                risk = entry_price * 0.01

    return trades


def htf_ema_bias(df: pd.DataFrame, factor: int = 4, fast: int = 21, slow: int = 50) -> pd.Series:
    """Approximate HTF EMA bias by resampling."""
    if len(df) < slow * factor:
        return pd.Series(True, index=df.index)
    if "timestamp" in df.columns:
        idx = pd.to_datetime(df["timestamp"])
    else:
        idx = df.index
    tmp = df.copy()
    tmp.index = idx
    rule = f"{factor * 15}min" if len(df) > 500 else f"{factor}h"
    try:
        rs = tmp["close"].resample(rule).last().dropna()
    except Exception:
        rs = tmp["close"].iloc[::factor]
    bull = ema(rs, fast) > ema(rs, slow)
    aligned = bull.reindex(tmp.index, method="ffill").fillna(True)
    return pd.Series(aligned.values, index=df.index)


def extract_zone_signals_from_df(df: pd.DataFrame) -> list[ZoneSignal]:
    """Build ZoneSignal list from buy/sell + optional sl_price/tp_price columns."""
    signals: list[ZoneSignal] = []
    closes = df["close"].values
    has_entry = "entry_price" in df.columns
    for i in range(len(df)):
        if "buy" in df.columns and df["buy"].iloc[i]:
            sl = df["sl_price"].iloc[i] if "sl_price" in df.columns else np.nan
            tp = df["tp_price"].iloc[i] if "tp_price" in df.columns else np.nan
            ent = df["entry_price"].iloc[i] if has_entry and not np.isnan(df["entry_price"].iloc[i]) else closes[i]
            signals.append(
                ZoneSignal(
                    i,
                    "long",
                    float(ent),
                    None if np.isnan(sl) else float(sl),
                    None if np.isnan(tp) else float(tp),
                )
            )
        if "sell" in df.columns and df["sell"].iloc[i]:
            sl = df["sl_price"].iloc[i] if "sl_price" in df.columns else np.nan
            tp = df["tp_price"].iloc[i] if "tp_price" in df.columns else np.nan
            ent = df["entry_price"].iloc[i] if has_entry and not np.isnan(df["entry_price"].iloc[i]) else closes[i]
            signals.append(
                ZoneSignal(
                    i,
                    "short",
                    float(ent),
                    None if np.isnan(sl) else float(sl),
                    None if np.isnan(tp) else float(tp),
                )
            )
    return signals
