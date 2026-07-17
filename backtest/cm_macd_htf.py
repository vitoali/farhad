"""CM MACD high-WR patterns: green below zero + HTF, 1h red hist + HTF."""
from __future__ import annotations

import numpy as np
import pandas as pd

from golden_combo_strategy import _align_bool, macd_cm_states
from indicators import ema

TF_RANK = {"5m": 0, "15m": 1, "1h": 2, "4h": 3}
TIMEFRAMES = ["5m", "15m", "1h", "4h"]

# From CM MACD study (70–80% WR patterns)
HW_LONG_HTF_MIN: dict[str, int] = {"default": 3, "BTCUSDT": 2, "EURUSD": 3}
HW_SHORT_HTF_MIN: dict[str, int] = {"default": 2, "BTCUSDT": 2}
HW_SHORT_RED_HIST_1H = frozenset({"BTCUSDT"})
HW_SHORT_ENABLED = frozenset({"BTCUSDT"})


def red_hist_start(hist: np.ndarray) -> np.ndarray:
    n = len(hist)
    out = np.zeros(n, dtype=bool)
    for i in range(2, n):
        red = hist[i] < hist[i - 1] and hist[i] <= 0
        red_prev = hist[i - 1] < hist[i - 2] and hist[i - 1] <= 0
        out[i] = red and not red_prev
    return out


def _ts_values(df: pd.DataFrame) -> np.ndarray:
    if "timestamp" in df.columns:
        return pd.to_datetime(df["timestamp"], utc=True).values
    return pd.to_datetime(df.index, utc=True).values


def precompute_cm_cache(data: dict, sym: str) -> dict:
    cache: dict = {}
    for tf in TIMEFRAMES:
        df = data.get(sym, {}).get(tf)
        if df is None or len(df) < 30:
            continue
        st = macd_cm_states(df)
        macd = ema(st["close"], 12) - ema(st["close"], 26)
        sig = ema(macd, 9)
        hist = (macd - sig).values
        cache[tf] = {
            "df": st,
            "macd": macd.values,
            "hist": hist,
            "ts": _ts_values(st),
        }
    return cache


def mtf_score_at(cache: dict, signal_tf: str, ts: np.datetime64, direction: str) -> int:
    sig_rank = TF_RANK[signal_tf]
    score = 0
    for tf in TIMEFRAMES:
        if TF_RANK[tf] <= sig_rank:
            continue
        c = cache.get(tf)
        if not c:
            continue
        idx = int(np.searchsorted(c["ts"], ts, side="right") - 1)
        if idx < 0:
            continue
        row = c["df"].iloc[idx]
        h = c["hist"]
        m = c["macd"][idx]
        if direction == "long":
            if row["macd_hist_aqua"] or row["macd_bull_above_zero"]:
                score += 1
            if row["macd_cross_bull"]:
                score += 2
        else:
            red = idx >= 1 and h[idx] < h[idx - 1] and h[idx] <= 0
            if red or not row["macd_bull_above_zero"]:
                score += 1
            if row["macd_cross_bear"]:
                score += 2
    return score


def build_hw_context(
    data: dict,
    sym: str,
    entry_df: pd.DataFrame,
    confirm_df: pd.DataFrame,
    *,
    selective: bool = False,
) -> dict:
    """Precompute high-WR CM MACD pattern flags aligned to 15m entry chart."""
    cache = precompute_cm_cache(data, sym)
    entry_st = macd_cm_states(entry_df)
    confirm_st = macd_cm_states(confirm_df)
    confirm_st = confirm_st.copy()
    macd_c = ema(confirm_st["close"], 12) - ema(confirm_st["close"], 26)
    confirm_st["red_hist_start"] = red_hist_start((macd_c - ema(macd_c, 9)).values)

    n = len(entry_df)
    ets = _ts_values(entry_df)
    htf_long_15m = np.zeros(n, dtype=np.int8)
    htf_short_15m = np.zeros(n, dtype=np.int8)
    htf_short_1h = np.zeros(n, dtype=np.int8)
    for i in range(n):
        ts = ets[i]
        htf_long_15m[i] = mtf_score_at(cache, "15m", ts, "long")
        htf_short_15m[i] = mtf_score_at(cache, "15m", ts, "short")
        htf_short_1h[i] = mtf_score_at(cache, "1h", ts, "short")

    entry_green_below = entry_st["macd_cross_bull_below"].fillna(False).values
    entry_red_above = entry_st["macd_cross_bear_above"].fillna(False).values
    confirm_red_hist = _align_bool(confirm_st, "red_hist_start", entry_df)

    long_min = HW_LONG_HTF_MIN.get(sym, HW_LONG_HTF_MIN["default"])
    short_min = HW_SHORT_HTF_MIN.get(sym, HW_SHORT_HTF_MIN["default"])

    hw_long = entry_green_below & (htf_long_15m >= long_min)
    if sym in HW_SHORT_RED_HIST_1H:
        hw_short = confirm_red_hist & (htf_short_1h >= short_min)
    elif selective or sym not in HW_SHORT_ENABLED:
        hw_short = np.zeros(n, dtype=bool)
    else:
        hw_short = entry_red_above & (htf_short_15m >= short_min)

    return {
        "hw_long_pattern": hw_long,
        "hw_short_pattern": hw_short,
        "entry_green_below": entry_green_below,
        "entry_red_above": entry_red_above,
        "confirm_red_hist": confirm_red_hist,
        "htf_long_15m": htf_long_15m,
        "htf_short_15m": htf_short_15m,
        "htf_short_1h": htf_short_1h,
        "long_htf_min": long_min,
        "short_htf_min": short_min,
        "selective": selective,
    }
