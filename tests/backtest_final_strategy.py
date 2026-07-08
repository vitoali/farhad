#!/usr/bin/env python3
"""Offline backtest — Khakster Final Strategy (1 week, BTC + EURUSD)."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from mse_engine_py import (
    ENTRY_FTC,
    ENTRY_RTP,
    EntrySettings,
    MseSettings,
    StructureLevel,
    detect_pivots_h1,
    entry_sl_tp,
    ftc_touch,
    price_break_zone,
    price_in_zone,
    rtp_from_bar,
    rtp_touch,
    run_backtest,
)

try:
    from test_smart_money_lib import volume_confirms, zones_overlap
except ImportError:
    def zones_overlap(t1, b1, t2, b2):
        return not (b1 > t2 or t1 < b2)

    def volume_confirms(z_top, z_bot, poc, va_top, va_bot, min_ratio=0.15):
        poc_in = z_bot <= poc <= z_top
        h1 = z_top - z_bot
        top, bot = min(z_top, va_top), max(z_bot, va_bot)
        va_hit = zones_overlap(va_top, va_bot, z_top, z_bot) and (max(top - bot, 0) / h1 if h1 > 0 else 0) >= min_ratio
        return poc_in or va_hit


PIP_FX = 0.0001


@dataclass
class FinalSettings:
    min_sm: int = 2
    min_score: int = 40
    min_score_crypto: int = 50
    use_ftc: bool = True
    use_candle: bool = True
    use_session_filter: bool = True
    london_start: int = 7
    london_end: int = 16
    ny_start: int = 13
    ny_end: int = 21
    structure_minutes: int = 60
    trigger_minutes: int = 5


def pip_unit(price: float, symbol: str) -> float:
    if "BTC" in symbol.upper():
        # کالیبره مشابه trex.settingsForSymbol: ۱ پیپ ≈ ۰.۰۱٪ قیمت
        return max(price * 0.0001, 0.01)
    return PIP_FX


def effective_min_score(symbol: str, fs: FinalSettings) -> int:
    if "BTC" in symbol.upper():
        return max(fs.min_score, fs.min_score_crypto)
    return fs.min_score


def in_trading_session(ts: pd.Timestamp, symbol: str, fs: FinalSettings) -> bool:
    if not fs.use_session_filter or "BTC" in symbol.upper():
        return True
    h = ts.hour
    in_lon = fs.london_start <= h < fs.london_end
    in_ny = fs.ny_start <= h < fs.ny_end
    return in_lon or in_ny


def to_pips(dist: float, unit: float) -> float:
    return round(dist / unit) if unit > 0 else round(dist)


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        df.resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )


def calc_poc_va(df: pd.DataFrame, lookback: int = 150, rows: int = 24, pct: float = 70.0):
    sub = df.tail(lookback)
    if len(sub) < 10:
        return np.nan, np.nan, np.nan
    top, bot = sub["high"].max(), sub["low"].min()
    if top <= bot:
        return np.nan, np.nan, np.nan
    step = (top - bot) / rows
    totals = np.zeros(rows)
    for _, row in sub.iterrows():
        bt, bb = max(row["open"], row["close"]), min(row["open"], row["close"])
        body = bt - bb
        vol = row.get("volume", 1.0) or 1.0
        for i in range(rows):
            lb, lt = bot + step * i, bot + step * (i + 1)
            if lt > bb and lb < bt:
                totals[i] += vol * (min(lt, bt) - max(lb, bb)) / max(body, step * 0.01)
    poc = int(np.argmax(totals))
    target = totals.sum() * pct / 100
    va, up, dn = totals[poc], poc, poc
    for _ in range(rows):
        if va >= target:
            break
        uv = totals[up + 1] if up < rows - 1 else 0
        lv = totals[dn - 1] if dn > 0 else 0
        if uv >= lv and up < rows - 1:
            va += uv
            up += 1
        elif dn > 0:
            va += lv
            dn -= 1
        else:
            break
    poc_lvl = bot + step * (poc + 0.5)
    return poc_lvl, bot + step * (up + 1), bot + step * dn


def sm_confirms(z_top: float, z_bot: float, is_high: bool, df: pd.DataFrame, i: int) -> tuple[bool, int]:
    """Simplified SM: volume POC/VA + liquidity wick proxy."""
    win = df.iloc[max(0, i - 150) : i + 1]
    poc, va_t, va_b = calc_poc_va(win)
    vol_ok = False if np.isnan(poc) else volume_confirms(z_top, z_bot, poc, va_t, va_b)
    # liquidity proxy: recent sweep wick through zone edge
    liq_ok = False
    if i >= 5:
        edge = z_top if is_high else z_bot
        for j in range(1, 6):
            row = df.iloc[i - j]
            if is_high and row["high"] > edge and row["close"] < edge:
                liq_ok = True
            if not is_high and row["low"] < edge and row["close"] > edge:
                liq_ok = True
    # OB proxy: last impulse body overlaps zone
    ob_ok = False
    if i >= 3:
        r = df.iloc[i - 1]
        bt, bb = max(r["open"], r["close"]), min(r["open"], r["close"])
        ob_ok = zones_overlap(bt, bb, z_top, z_bot)
    cnt = sum([liq_ok, ob_ok, vol_ok])
    return cnt >= 2, cnt


def simple_engulfing(df: pd.DataFrame, i: int, bullish: bool) -> bool:
    if i < 1:
        return False
    c, p = df.iloc[i], df.iloc[i - 1]
    if bullish:
        return p["close"] < p["open"] and c["close"] > c["open"] and c["close"] > p["open"] and c["open"] < p["close"]
    return p["close"] > p["open"] and c["close"] < c["open"] and c["close"] < p["open"] and c["open"] > p["close"]


def detect_pivots_on_df(h1: pd.DataFrame, s: MseSettings) -> list[StructureLevel]:
    return detect_pivots_h1(h1, s)


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    side: str
    entry: float
    sl: float
    tp: float
    exit_price: Optional[float] = None
    pnl_pips: Optional[float] = None
    kind: str = ""


def run_final_backtest(
    m5: pd.DataFrame,
    h1: pd.DataFrame,
    symbol: str,
    fs: FinalSettings,
    es: EntrySettings,
    ms: MseSettings,
) -> tuple[list[Trade], list[StructureLevel]]:
    unit = pip_unit(m5["close"].iloc[-1], symbol)
    min_sc = effective_min_score(symbol, fs)
    levels_raw = detect_pivots_on_df(h1, ms)
    active: list[StructureLevel] = []
    trades: list[Trade] = []
    open_trade: Optional[Trade] = None
    level_idx = 0
    prev_h, prev_l = np.nan, np.nan

    for t, row in m5.iterrows():
        while level_idx < len(levels_raw) and levels_raw[level_idx].birth_time <= t:
            lv = levels_raw[level_idx]
            idx = m5.index.get_indexer([t], method="pad")[0]
            sm_ok, _ = sm_confirms(lv.zone_top, lv.zone_bot, lv.is_high, m5, max(idx, 0))
            if lv.score >= min_sc and lv.ftc_cred and sm_ok and in_trading_session(t, symbol, fs):
                active.append(lv)
            level_idx += 1

        hi, lo, o, c = row["high"], row["low"], row["open"], row["close"]

        if open_trade:
            ot = open_trade
            hit_sl = hi >= ot.sl if ot.side == "short" else lo <= ot.sl
            hit_tp = lo <= ot.tp if ot.side == "short" else hi >= ot.tp
            if hit_sl:
                ot.exit_price = ot.sl
            elif hit_tp:
                ot.exit_price = ot.tp
            if ot.exit_price is not None:
                ot.exit_time = t
                d = ot.entry - ot.exit_price if ot.side == "short" else ot.exit_price - ot.entry
                ot.pnl_pips = to_pips(d, unit)
                trades.append(ot)
                open_trade = None

        if open_trade is None and in_trading_session(t, symbol, fs):
            i = m5.index.get_loc(t)
            for lv in active:
                if lv.broken or lv.traded_ftc or lv.traded_rtp:
                    continue
                ent = None
                if fs.use_ftc and ftc_touch(lv, hi, lo, prev_h, prev_l):
                    ent = ENTRY_FTC
                elif fs.use_ftc and rtp_touch(lv, hi, lo, prev_h, prev_l):
                    ent = ENTRY_RTP
                in_zone = price_in_zone(hi, lo, lv.zone_top, lv.zone_bot) or price_in_zone(hi, lo, lv.ftc_top, lv.ftc_bot)
                pat = fs.use_candle and in_zone and (
                    (not lv.is_high and simple_engulfing(m5, i, True))
                    or (lv.is_high and simple_engulfing(m5, i, False))
                )
                if ent or pat:
                    sl, tp = entry_sl_tp(lv.is_high, lv.zone_top, lv.zone_bot, lv.pivot_price, lv.th_pips, es)
                    open_trade = Trade(t, None, "short" if lv.is_high else "long", c, sl, tp, kind="FTC" if ent == ENTRY_FTC else "RTP" if ent == ENTRY_RTP else "PAT")
                    lv.traded_ftc = True
                    break

        for lv in active:
            if lv.broken:
                continue
            if not lv.ftc_spent and price_in_zone(hi, lo, lv.ftc_top, lv.ftc_bot) and not price_in_zone(prev_h, prev_l, lv.ftc_top, lv.ftc_bot):
                lv.ftc_spent = True
                rt, rb = rtp_from_bar(lv.is_high, o, hi, lo, c)
                lv.rtp_top, lv.rtp_bot, lv.rtp_set = rt, rb, True
            if price_break_zone(lv.is_high, c, lv.zone_top, lv.zone_bot):
                lv.broken = True

        prev_h, prev_l = hi, lo

    if open_trade:
        open_trade.exit_time = m5.index[-1]
        open_trade.exit_price = m5["close"].iloc[-1]
        d = open_trade.entry - open_trade.exit_price if open_trade.side == "short" else open_trade.exit_price - open_trade.entry
        open_trade.pnl_pips = to_pips(d, unit)
        trades.append(open_trade)

    return trades, levels_raw


def fetch(symbol: str, days: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    import yfinance as yf

    m5 = yf.download(symbol, interval="5m", period=f"{days}d", progress=False, auto_adjust=True)
    if m5.empty:
        raise RuntimeError(f"No data for {symbol}")
    if isinstance(m5.columns, pd.MultiIndex):
        m5.columns = m5.columns.get_level_values(0)
    m5 = m5.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    m5.index = pd.to_datetime(m5.index, utc=True).tz_convert(None)
    h1 = resample_ohlc(m5, "1h")
    return h1, m5


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return {"trades": 0, "win_rate": 0.0, "total_pips": 0.0, "avg_pips": 0.0}
    pnls = [t.pnl_pips for t in trades if t.pnl_pips is not None]
    wins = sum(1 for p in pnls if p > 0)
    return {
        "trades": len(pnls),
        "wins": wins,
        "losses": len(pnls) - wins,
        "win_rate": round(100 * wins / len(pnls), 1),
        "total_pips": round(sum(pnls), 1),
        "avg_pips": round(sum(pnls) / len(pnls), 1),
    }


def main():
    print("=== Khakster Final Strategy — 1 Week Backtest ===\n")
    fs, es, ms = FinalSettings(), EntrySettings(), MseSettings()
    results = {}

    for sym in ("EURUSD=X", "BTC-USD"):
        label = "EURUSD" if "EUR" in sym else "BTCUSD"
        print(f"--- {label} (H1 structure + M5 trigger) ---")
        h1, m5 = fetch(sym, days=7)
        print(f"  M5 bars: {len(m5)}  range: {m5.index[0].date()} → {m5.index[-1].date()}")
        trades, pivots = run_final_backtest(m5, h1, sym, fs, es, ms)
        stats = summarize(trades)
        stats["pivots"] = len(pivots)
        stats["sm_min"] = fs.min_sm
        stats["min_score"] = effective_min_score(sym, fs)
        stats["session_filter"] = fs.use_session_filter and "EUR" in sym
        results[label] = stats
        print(json.dumps(stats, indent=2))
        if trades:
            print("  Last trade:", trades[-1].side, trades[-1].kind, f"pnl={trades[-1].pnl_pips:+.0f}")
        print()

    out = ROOT / "tests" / "backtest_final_1w_results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
