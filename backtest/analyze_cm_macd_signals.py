#!/usr/bin/env python3
"""Analyze CM MACD aqua/red + cross dots — MTF confluence (optimized)."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from config import FOREX_SL_PIPS, FOREX_TP_RR
from fetch_data import fetch_all
from golden_combo_strategy import macd_cm_states
from indicators import atr_wilder, ema, rsi, sma
from run_forex_three_indicators import pip_size

RESULTS = Path(__file__).parent / "results"
SYMBOLS = ["EURUSD", "XAUUSD", "USDJPY", "BTCUSDT", "SOLUSDT"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]
HOLD_BARS = {"5m": 48, "15m": 32, "1h": 24, "4h": 12}
TF_RANK = {"5m": 0, "15m": 1, "1h": 2, "4h": 3}


@dataclass
class SignalOutcome:
    symbol: str
    tf: str
    ts: str
    signal_type: str
    direction: str
    win: bool
    rsi_val: float
    macd_dist_zero: float
    hist_slope: float
    mtf_aligned: int
    extra: dict = field(default_factory=dict)


def precompute_states(data: dict) -> dict:
    cache: dict = {}
    for sym in SYMBOLS:
        cache[sym] = {}
        for tf in TIMEFRAMES:
            df = data.get(sym, {}).get(tf)
            if df is None or df.empty:
                continue
            st = macd_cm_states(df)
            macd = ema(st["close"], 12) - ema(st["close"], 26)
            sig = ema(macd, 9)
            hist = (macd - sig).values
            cache[sym][tf] = {
                "df": st,
                "macd": macd.values,
                "hist": hist,
                "ts": pd.to_datetime(st["timestamp"], utc=True).values if "timestamp" in st.columns else None,
            }
    return cache


def lookup_state(cache: dict, sym: str, tf: str, ts: np.datetime64) -> dict | None:
    c = cache.get(sym, {}).get(tf)
    if not c or c["ts"] is None:
        return None
    idx = int(np.searchsorted(c["ts"], ts, side="right") - 1)
    if idx < 0:
        return None
    row = c["df"].iloc[idx]
    h = c["hist"]
    m = c["macd"][idx]
    return {
        "aqua": bool(row["macd_hist_aqua"]),
        "red": bool(idx >= 1 and h[idx] < h[idx - 1] and h[idx] <= 0),
        "cross_bull": bool(row["macd_cross_bull"]),
        "cross_bear": bool(row["macd_cross_bear"]),
        "below_zero": m < 0,
        "above_zero": m > 0,
        "macd_above_sig": bool(row["macd_bull_above_zero"] or m > 0),
        "hist_slope": float(h[idx] - h[idx - 1]) if idx > 0 else 0,
    }


def mtf_score(cache: dict, sym: str, signal_tf: str, ts: np.datetime64, direction: str) -> int:
    sig_rank = TF_RANK[signal_tf]
    score = 0
    for tf in TIMEFRAMES:
        if TF_RANK[tf] <= sig_rank:
            continue
        st = lookup_state(cache, sym, tf, ts)
        if not st:
            continue
        if direction == "long":
            if st["aqua"] or st["macd_above_sig"]:
                score += 1
            if st["cross_bull"]:
                score += 2
        else:
            if st["red"] or not st["macd_above_sig"]:
                score += 1
            if st["cross_bear"]:
                score += 2
    return score


def simulate_direction(df, i, direction, symbol, max_bars) -> bool:
    closes, highs, lows = df["close"].values, df["high"].values, df["low"].values
    entry = closes[i]
    pip = pip_size(symbol, entry)
    risk = FOREX_SL_PIPS * pip
    if "JPY" not in symbol and entry > 50:
        risk = entry * 0.002
    if symbol.endswith("USDT"):
        risk = entry * 0.005
    tp = risk * FOREX_TP_RR
    sl = entry - risk if direction == 1 else entry + risk
    tp_p = entry + tp if direction == 1 else entry - tp
    end = min(len(df) - 1, i + max_bars)
    for j in range(i + 1, end + 1):
        if direction == 1:
            if lows[j] <= sl:
                return False
            if highs[j] >= tp_p:
                return True
        else:
            if highs[j] >= sl:
                return False
            if lows[j] <= tp_p:
                return True
    return (closes[end] - entry) * direction > 0


def collect_signals(cache: dict) -> list[SignalOutcome]:
    out: list[SignalOutcome] = []
    for sym in SYMBOLS:
        for tf in TIMEFRAMES:
            c = cache.get(sym, {}).get(tf)
            if not c:
                continue
            df = c["df"]
            hist, macd = c["hist"], c["macd"]
            n = len(df)
            max_bars = HOLD_BARS[tf]
            rsi_v = rsi(df["close"], 14).values
            ma50 = sma(df["close"], 50).values
            closes = df["close"].values

            for i in range(3, n - max_bars):
                ts = c["ts"][i] if c["ts"] is not None else np.datetime64(i, "s")
                ts_s = str(ts)
                feats = {
                    "rsi": float(rsi_v[i]) if not np.isnan(rsi_v[i]) else 50,
                    "above_ma50": bool(closes[i] > ma50[i]) if not np.isnan(ma50[i]) else False,
                    "hist_slope": float(hist[i] - hist[i - 1]) if i > 0 else 0,
                }

                if df["macd_cross_bull"].iloc[i]:
                    sc = mtf_score(cache, sym, tf, ts, "long")
                    out.append(SignalOutcome(sym, tf, ts_s, "cross_bull_dot", "long",
                        simulate_direction(df, i, 1, sym, max_bars), feats["rsi"], float(macd[i]), feats["hist_slope"], sc,
                        {"below_zero": macd[i] < 0, "above_ma50": feats["above_ma50"]}))

                if df["macd_cross_bear"].iloc[i]:
                    sc = mtf_score(cache, sym, tf, ts, "short")
                    out.append(SignalOutcome(sym, tf, ts_s, "cross_bear_dot", "short",
                        simulate_direction(df, i, -1, sym, max_bars), feats["rsi"], float(macd[i]), feats["hist_slope"], sc,
                        {"above_zero": macd[i] > 0, "above_ma50": feats["above_ma50"]}))

                aqua = bool(df["macd_hist_aqua"].iloc[i]) and not bool(df["macd_hist_aqua"].iloc[i - 1])
                if aqua:
                    sc = mtf_score(cache, sym, tf, ts, "long")
                    out.append(SignalOutcome(sym, tf, ts_s, "aqua_start", "long",
                        simulate_direction(df, i, 1, sym, max_bars), feats["rsi"], float(macd[i]), feats["hist_slope"], sc,
                        {"macd_above_zero": macd[i] > 0, "above_ma50": feats["above_ma50"]}))

                red = i > 0 and hist[i] < hist[i - 1] and hist[i] <= 0
                red_prev = i > 1 and hist[i - 1] < hist[i - 2] and hist[i - 1] <= 0
                if red and not red_prev:
                    sc = mtf_score(cache, sym, tf, ts, "short")
                    out.append(SignalOutcome(sym, tf, ts_s, "red_hist_start", "short",
                        simulate_direction(df, i, -1, sym, max_bars), feats["rsi"], float(macd[i]), feats["hist_slope"], sc,
                        {"macd_below_zero": macd[i] < 0, "above_ma50": feats["above_ma50"]}))
    return out


def analyze_patterns(outcomes: list[SignalOutcome]) -> tuple[list, list]:
    filters = [
        ("100% candidates", lambda o: True),
        ("green dot زیر صفر", lambda o: o.signal_type == "cross_bull_dot" and o.extra.get("below_zero")),
        ("green زیر صفر + HTF>=2", lambda o: o.signal_type == "cross_bull_dot" and o.extra.get("below_zero") and o.mtf_aligned >= 2),
        ("green زیر صفر + HTF>=3", lambda o: o.signal_type == "cross_bull_dot" and o.extra.get("below_zero") and o.mtf_aligned >= 3),
        ("green زیر صفر + RSI<40", lambda o: o.signal_type == "cross_bull_dot" and o.extra.get("below_zero") and o.rsi_val < 40),
        ("red dot بالای صفر", lambda o: o.signal_type == "cross_bear_dot" and o.extra.get("above_zero")),
        ("red بالای صفر + HTF>=2", lambda o: o.signal_type == "cross_bear_dot" and o.extra.get("above_zero") and o.mtf_aligned >= 2),
        ("red بالای صفر + HTF>=3", lambda o: o.signal_type == "cross_bear_dot" and o.extra.get("above_zero") and o.mtf_aligned >= 3),
        ("red بالای صفر + RSI>60", lambda o: o.signal_type == "cross_bear_dot" and o.extra.get("above_zero") and o.rsi_val > 60),
        ("aqua شروع + MACD>0", lambda o: o.signal_type == "aqua_start" and o.extra.get("macd_above_zero")),
        ("aqua + HTF>=2", lambda o: o.signal_type == "aqua_start" and o.mtf_aligned >= 2),
        ("red hist + MACD<0", lambda o: o.signal_type == "red_hist_start" and o.extra.get("macd_below_zero")),
        ("red hist + HTF>=2", lambda o: o.signal_type == "red_hist_start" and o.mtf_aligned >= 2),
    ]
    perfect, high = [], []
    for tf in TIMEFRAMES:
        for name, fn in filters[1:]:
            for sym in SYMBOLS + ["ALL"]:
                sub = [o for o in outcomes if o.tf == tf and (sym == "ALL" or o.symbol == sym) and fn(o)]
                if len(sub) < 3:
                    continue
                wr = sum(1 for o in sub if o.win) / len(sub)
                entry = {
                    "pattern": f"{tf} {sym} {name}",
                    "n": len(sub),
                    "wr": round(wr * 100, 1),
                    "avg_rsi": round(float(np.mean([o.rsi_val for o in sub])), 1),
                    "avg_mtf": round(float(np.mean([o.mtf_aligned for o in sub])), 1),
                    "traits": _common_traits(sub),
                    "examples": [{"sym": o.symbol, "ts": o.ts, "win": o.win} for o in sub if o.win][:3],
                }
                if wr == 1.0:
                    perfect.append(entry)
                elif wr >= 0.70 and len(sub) >= 4:
                    high.append(entry)
    return sorted(perfect, key=lambda x: -x["n"]), sorted(high, key=lambda x: (-x["wr"], -x["n"]))


def _common_traits(sub: list[SignalOutcome]) -> dict:
    wins = [o for o in sub if o.win]
    if not wins:
        return {}
    return {
        "avg_rsi_wins": round(float(np.mean([o.rsi_val for o in wins])), 1),
        "avg_mtf_wins": round(float(np.mean([o.mtf_aligned for o in wins])), 1),
        "pct_below_zero": round(100 * sum(1 for o in wins if o.extra.get("below_zero")) / len(wins), 0),
        "pct_above_zero": round(100 * sum(1 for o in wins if o.extra.get("above_zero")) / len(wins), 0),
        "pct_above_ma50": round(100 * sum(1 for o in wins if o.extra.get("above_ma50")) / len(wins), 0),
        "avg_hist_slope": round(float(np.mean([o.hist_slope for o in wins])), 5),
    }


def main():
    print("Loading + precomputing...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    cache = precompute_states(data)
    outcomes = collect_signals(cache)
    perfect, high = analyze_patterns(outcomes)

    by_tf: dict = {}
    for tf in TIMEFRAMES:
        by_tf[tf] = {}
        for st in ["cross_bull_dot", "cross_bear_dot", "aqua_start", "red_hist_start"]:
            sub = [o for o in outcomes if o.tf == tf and o.signal_type == st]
            if sub:
                by_tf[tf][st] = {"n": len(sub), "wr": round(100 * sum(1 for o in sub if o.win) / len(sub), 1)}

    result = {
        "period_days": 31,
        "by_timeframe": by_tf,
        "perfect_100wr": perfect[:25],
        "high_wr_70plus": high[:25],
        "conclusions": _conclusions(outcomes, perfect, high, by_tf),
    }
    path = RESULTS / "cm_macd_signal_analysis.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Saved {path}\n")
    print("=== Win rate by TF ===")
    for tf, d in by_tf.items():
        print(f"  {tf}: {d}")
    print(f"\n=== 100% WR patterns: {len(perfect)} ===")
    for p in perfect[:10]:
        print(f"  {p['pattern']} n={p['n']} traits={p['traits']}")
    print(f"\n=== 70%+ WR patterns: {len(high)} ===")
    for p in high[:10]:
        print(f"  {p['pattern']} WR={p['wr']}% n={p['n']} traits={p['traits']}")


def _conclusions(outcomes, perfect, high, by_tf) -> list[str]:
    c = []
    bull_below = [o for o in outcomes if o.signal_type == "cross_bull_dot" and o.extra.get("below_zero")]
    bull_htf = [o for o in bull_below if o.mtf_aligned >= 2]
    if bull_below:
        c.append(f"نقطه سبز زیر صفر: WR پایه {100*sum(o.win for o in bull_below)/len(bull_below):.1f}% (n={len(bull_below)})")
    if bull_htf:
        c.append(f"نقطه سبز زیر صفر + HTF هم‌جهت: WR {100*sum(o.win for o in bull_htf)/len(bull_htf):.1f}% (n={len(bull_htf)})")
    bear_above = [o for o in outcomes if o.signal_type == "cross_bear_dot" and o.extra.get("above_zero")]
    bear_htf = [o for o in bear_above if o.mtf_aligned >= 2]
    if bear_above:
        c.append(f"نقطه قرمز بالای صفر: WR پایه {100*sum(o.win for o in bear_above)/len(bear_above):.1f}% (n={len(bear_above)})")
    if bear_htf:
        c.append(f"نقطه قرمز بالای صفر + HTF هم‌جهت: WR {100*sum(o.win for o in bear_htf)/len(bear_htf):.1f}% (n={len(bear_htf)})")
    if perfect:
        c.append(f"الگوهای 100%: بیشترین نمونه = {perfect[0]['pattern']} (n={perfect[0]['n']})")
    best_tf = max(by_tf.items(), key=lambda x: max((v.get("wr", 0) for v in x[1].values()), default=0))
    c.append(f"بهترین TF کلی: {best_tf[0]}")
    return c


if __name__ == "__main__":
    main()
