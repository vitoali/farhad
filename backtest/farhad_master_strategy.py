"""
Farhad Master Strategy — maximum confluence from top backtest performers.

Core (#1 PF): rsi_advanced (2.96)
SMC zones: liquidity_shift (2.67), supply_demand (1.70), ifvg (1.63)
Structure: strong_pullback (1.41), smart_money_structure (1.48)
OB/retest: volume_ob_retest (1.29), mirage_lsp (1.04), fvg_retest (1.13)
Technical filters: AlphaTrend, UT Bot, Zero-Lag, Bj Bot structure
SL/TP: PF-weighted aggregate from all firing zone engines
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import alpha_trend_signals, atr_wilder, bj_bot_signals, ema, true_range, ut_bot_signals
from zone_engine import ZoneSignal, signals_to_df
from zone_indicators import (
    ifvg_signals,
    rsi_advanced_signals,
    strong_pullback_signals,
    supply_demand_signals,
)

from extra_indicators import (
    fvg_retest_signals,
    liquidity_shift_signals,
    mirage_lsp_signals,
    multi_div_signals,
    smart_money_structure_signals,
    volume_ob_retest_signals,
)

# Backtest-derived influence weights (avg PF scaled)
SOURCE_WEIGHT: dict[str, float] = {
    "rsi_advanced": 3.0,
    "liquidity_shift": 2.7,
    "supply_demand": 1.7,
    "ifvg": 1.6,
    "smart_money_structure": 1.5,
    "strong_pullback": 1.4,
    "volume_ob_retest": 1.3,
    "multi_div": 1.17,
    "bj_bot": 1.15,
    "fvg_retest": 1.13,
    "mirage_lsp": 1.04,
}

TIER1 = {"rsi_advanced", "liquidity_shift", "strong_pullback"}
TIER2_ZONE = {
    "supply_demand", "ifvg", "volume_ob_retest", "mirage_lsp",
    "fvg_retest", "multi_div", "smart_money_structure",
}


@dataclass
class _Vote:
    source: str
    direction: str  # long | short
    weight: float
    sl: float | None = None
    tp: float | None = None


def _zero_lag_trend(df: pd.DataFrame, length: int = 70, mult: float = 1.2) -> pd.Series:
    close = df["close"]
    lag = (length - 1) // 2
    zlema = ema(close + (close - close.shift(lag)), length)
    atr_v = true_range(df).ewm(alpha=1 / length, adjust=False).mean()
    volatility = atr_v.rolling(length * 3).max() * mult
    trend = pd.Series(0, index=close.index, dtype=int)
    for i in range(1, len(df)):
        if close.iloc[i] > zlema.iloc[i] + volatility.iloc[i] and close.iloc[i - 1] <= zlema.iloc[i - 1] + volatility.iloc[i - 1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < zlema.iloc[i] - volatility.iloc[i] and close.iloc[i - 1] >= zlema.iloc[i - 1] - volatility.iloc[i - 1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]
    return trend


def _recent(series: pd.Series, bar: int, lb: int) -> bool:
    lo = max(0, bar - lb)
    return bool(series.iloc[lo:bar].any())


def _votes_from_df(name: str, sig: pd.DataFrame, bar: int, lb: int) -> list[_Vote]:
    w = SOURCE_WEIGHT.get(name, 1.0)
    votes: list[_Vote] = []
    has_sl = "sl_price" in sig.columns and "tp_price" in sig.columns
    for i in range(max(0, bar - lb), bar + 1):
        if sig["buy"].iloc[i]:
            sl = float(sig["sl_price"].iloc[i]) if has_sl and not np.isnan(sig["sl_price"].iloc[i]) else None
            tp = float(sig["tp_price"].iloc[i]) if has_sl and not np.isnan(sig["tp_price"].iloc[i]) else None
            votes.append(_Vote(name, "long", w, sl, tp))
        if sig["sell"].iloc[i]:
            sl = float(sig["sl_price"].iloc[i]) if has_sl and not np.isnan(sig["sl_price"].iloc[i]) else None
            tp = float(sig["tp_price"].iloc[i]) if has_sl and not np.isnan(sig["tp_price"].iloc[i]) else None
            votes.append(_Vote(name, "short", w, sl, tp))
    return votes


def _aggregate_sl_tp(entry: float, direction: str, votes: list[_Vote], atr_v: float, bj_sl: float, bj_tp: float) -> tuple[float, float]:
    """PF-weighted blend of structural SL/TP from all agreeing sources."""
    aligned = [v for v in votes if v.direction == direction]
    if not aligned:
        return bj_sl, bj_tp

    w_sum = sum(v.weight for v in aligned)
    sl_cands = [(v.sl, v.weight) for v in aligned if v.sl is not None and not np.isnan(v.sl)]
    tp_cands = [(v.tp, v.weight) for v in aligned if v.tp is not None and not np.isnan(v.tp)]

    if direction == "long":
        sl_list = sl_cands + [(bj_sl, SOURCE_WEIGHT["bj_bot"])]
        sl = sum(s * w for s, w in sl_list) / sum(w for _, w in sl_list)
        sl = min(sl, entry - atr_v * 0.25)  # cap: not too tight
        risk = max(entry - sl, atr_v * 0.35)
        if tp_cands:
            rr = sum(((t - entry) / risk) * w for t, w in tp_cands if risk > 0) / sum(w for _, w in tp_cands)
            rr = float(np.clip(rr, 1.0, 3.0))
        else:
            rr = 1.5
        tp = entry + risk * rr
        tp = max(tp, bj_tp) if bj_tp > entry else tp
    else:
        sl_list = sl_cands + [(bj_sl, SOURCE_WEIGHT["bj_bot"])]
        sl = sum(s * w for s, w in sl_list) / sum(w for _, w in sl_list)
        sl = max(sl, entry + atr_v * 0.25)
        risk = max(sl - entry, atr_v * 0.35)
        if tp_cands:
            rr = sum(((entry - t) / risk) * w for t, w in tp_cands if risk > 0) / sum(w for _, w in tp_cands)
            rr = float(np.clip(rr, 1.0, 3.0))
        else:
            rr = 1.5
        tp = entry - risk * rr
        tp = min(tp, bj_tp) if bj_tp < entry else tp
    return sl, tp


def farhad_master_signals(
    df: pd.DataFrame,
    mode: str = "master",
    lookback: int = 10,
    novolumedata: bool = False,
) -> pd.DataFrame:
    """
    Modes:
      master        — min score 5.5, 1 tier1 trigger, 1 zone, 2 tech filters
      master_strict — min score 8.0, tier1 + 2 zones, all tech filters
    """
    out = df.copy()
    bj = bj_bot_signals(df)
    ut = ut_bot_signals(df)
    alpha = alpha_trend_signals(df, novolumedata=novolumedata)
    zl = _zero_lag_trend(df)
    atr_s = atr_wilder(out, 14)

    sources: dict[str, pd.DataFrame] = {
        "rsi_advanced": rsi_advanced_signals(df),
        "liquidity_shift": liquidity_shift_signals(df),
        "supply_demand": supply_demand_signals(df),
        "ifvg": ifvg_signals(df),
        "strong_pullback": strong_pullback_signals(df),
        "smart_money_structure": smart_money_structure_signals(df),
        "volume_ob_retest": volume_ob_retest_signals(df),
        "mirage_lsp": mirage_lsp_signals(df),
        "fvg_retest": fvg_retest_signals(df),
        "multi_div": multi_div_signals(df),
    }

    min_score = 5.5 if mode == "master" else 8.0
    min_zone = 1 if mode == "master" else 2
    require_all_tech = mode == "master_strict"

    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    score_l = np.zeros(n, dtype=float)
    score_s = np.zeros(n, dtype=float)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    entry_p = np.full(n, np.nan)
    meta = [""] * n

    closes = out["close"].values

    for i in range(lookback + 5, n):
        a = float(atr_s.iloc[i]) if not np.isnan(atr_s.iloc[i]) else closes[i] * 0.005
        ut_bull = closes[i] > ut["tsl"].iloc[i]
        ut_bear = closes[i] < ut["tsl"].iloc[i]
        alpha_bull = closes[i] > alpha["alpha_trend"].iloc[i]
        alpha_bear = closes[i] < alpha["alpha_trend"].iloc[i]
        zl_bull = zl.iloc[i] == 1
        zl_bear = zl.iloc[i] == -1
        bj_bull = bj["ma1"].iloc[i] > bj["ma2"].iloc[i]
        bj_bear = bj["ma1"].iloc[i] < bj["ma2"].iloc[i]

        tech_long = sum([ut_bull, alpha_bull, zl_bull, bj_bull])
        tech_short = sum([ut_bear, alpha_bear, zl_bear, bj_bear])
        tech_ok_long = tech_long >= (4 if require_all_tech else 2)
        tech_ok_short = tech_short >= (4 if require_all_tech else 2)

        votes_l: list[_Vote] = []
        votes_s: list[_Vote] = []
        tier1_l = tier1_s = 0
        zone_l = zone_s = 0.0

        for name, sig in sources.items():
            w = SOURCE_WEIGHT.get(name, 1.0)
            if _recent(sig["buy"], i, lookback):
                votes_l.extend(_votes_from_df(name, sig, i, 0))
                if name in TIER1:
                    tier1_l += 1
                if name in TIER2_ZONE:
                    zone_l += w
                else:
                    zone_l += w * 0.5
            if _recent(sig["sell"], i, lookback):
                votes_s.extend(_votes_from_df(name, sig, i, 0))
                if name in TIER1:
                    tier1_s += 1
                if name in TIER2_ZONE:
                    zone_s += w
                else:
                    zone_s += w * 0.5
            # current bar trigger bonus
            if sig["buy"].iloc[i]:
                votes_l.append(_Vote(name, "long", w * 1.5,
                    float(sig["sl_price"].iloc[i]) if "sl_price" in sig.columns and not np.isnan(sig["sl_price"].iloc[i]) else None,
                    float(sig["tp_price"].iloc[i]) if "tp_price" in sig.columns and not np.isnan(sig["tp_price"].iloc[i]) else None))
                if name in TIER1:
                    tier1_l += 2
                zone_l += w
            if sig["sell"].iloc[i]:
                votes_s.append(_Vote(name, "short", w * 1.5,
                    float(sig["sl_price"].iloc[i]) if "sl_price" in sig.columns and not np.isnan(sig["sl_price"].iloc[i]) else None,
                    float(sig["tp_price"].iloc[i]) if "tp_price" in sig.columns and not np.isnan(sig["tp_price"].iloc[i]) else None))
                if name in TIER1:
                    tier1_s += 2
                zone_s += w

        score_l[i] = zone_l + tech_long * 0.5
        score_s[i] = zone_s + tech_short * 0.5

        bj_sl_l = float(bj["long_stop"].iloc[i])
        bj_tp_l = float(bj["long_target"].iloc[i])
        bj_sl_s = float(bj["short_stop"].iloc[i])
        bj_tp_s = float(bj["short_target"].iloc[i])

        if tier1_l >= 1 and zone_l >= min_zone and score_l[i] >= min_score and tech_ok_long:
            buy[i] = True
            entry = closes[i]
            sl, tp = _aggregate_sl_tp(entry, "long", votes_l, a, bj_sl_l, bj_tp_l)
            sl_p[i], tp_p[i], entry_p[i] = sl, tp, entry
            top = sorted({v.source for v in votes_l}, key=lambda x: -SOURCE_WEIGHT.get(x, 0))[:4]
            meta[i] = "+".join(top)

        if tier1_s >= 1 and zone_s >= min_zone and score_s[i] >= min_score and tech_ok_short:
            sell[i] = True
            entry = closes[i]
            sl, tp = _aggregate_sl_tp(entry, "short", votes_s, a, bj_sl_s, bj_tp_s)
            sl_p[i], tp_p[i], entry_p[i] = sl, tp, entry
            top = sorted({v.source for v in votes_s}, key=lambda x: -SOURCE_WEIGHT.get(x, 0))[:4]
            meta[i] = "+".join(top)

    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = entry_p
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    out["score_long"] = score_l
    out["score_short"] = score_s
    out["confluence"] = meta
    return out
