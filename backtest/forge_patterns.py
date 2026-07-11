"""AlphaX FORGE — simplified pattern engine for offline backtest."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import atr_wilder, ema


@dataclass
class ForgeSignal:
    bar: int
    pattern: str
    bullish: bool
    entry: float
    stop: float
    target: float
    neckline: float
    confluence: int
    grade: str


def find_pivots(df: pd.DataFrame, left: int = 10, right: int = 10) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Return lists of (bar_index, price) for confirmed pivot highs/lows."""
    highs, lows = [], []
    h = df["high"].values
    l = df["low"].values
    n = len(df)
    for i in range(left + right, n):
        p = i - right
        window_h = h[p - left : p + right + 1]
        window_l = l[p - left : p + right + 1]
        if h[p] == window_h.max() and np.sum(window_h == h[p]) == 1:
            highs.append((p, h[p]))
        if l[p] == window_l.min() and np.sum(window_l == l[p]) == 1:
            lows.append((p, l[p]))
    return highs, lows


def _near(v1: float, v2: float, tol_pct: float) -> bool:
    return abs(v1 - v2) <= ((v1 + v2) / 2) * tol_pct


def _confluence(bullish: bool, rr: float, htf_bull: bool, htf_bear: bool, chop_ok: bool, min_rr: float = 1.5) -> int:
    score = 0
    score += 2 if rr >= min_rr else (1 if rr >= 1.0 else 0)
    if bullish and htf_bull:
        score += 2
    elif not bullish and htf_bear:
        score += 2
    score += 1 if chop_ok else 0
    score += 1 if rr >= 1.0 else 0
    return min(score, 10)


def _grade(score: int, min_conf: int = 5) -> str:
    if score >= 8:
        return "A"
    if score >= 6:
        return "B"
    if score >= min_conf:
        return "C"
    return "—"


def chop_index(df: pd.DataFrame, length: int = 14) -> pd.Series:
    atr1 = atr_wilder(df.assign(close=df["close"]), 1) if len(df) > 1 else pd.Series(0, index=df.index)
    ci_sum = atr1.rolling(length).sum()
    ci_hl = df["high"].rolling(length).max() - df["low"].rolling(length).min()
    return 100 * np.log10(ci_sum / ci_hl.replace(0, np.nan)) / np.log10(length)


def detect_double_patterns(
    df: pd.DataFrame,
    lvl_tol: float = 0.03,
    sym_tol: float = 0.10,
    min_size_pct: float = 0.005,
    min_atr_mult: float = 1.0,
    atr_len: int = 14,
    break_atr: float = 1.0,
    min_rr: float = 1.5,
    sl_pct_tgt: float = 0.25,
    min_conf: int = 5,
    htf_fast: int = 21,
    htf_slow: int = 55,
) -> list[ForgeSignal]:
    """Detect double top/bottom with breakout — core FORGE logic."""
    atr = atr_wilder(df, atr_len)
    chop = chop_index(df)
    # HTF proxy: resample to 1h if 15m etc.
    htf_bull = pd.Series(False, index=df.index)
    htf_bear = pd.Series(False, index=df.index)
    if len(df) > htf_slow:
        fast = ema(df["close"], htf_fast)
        slow = ema(df["close"], htf_slow)
        htf_bull = (fast > slow) & (df["close"] > fast)
        htf_bear = (fast < slow) & (df["close"] < fast)

    ph, pl = find_pivots(df)
    signals: list[ForgeSignal] = []
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    def valid_size(height: float, price: float, bar: int) -> bool:
        a = atr.iloc[bar] if bar < len(atr) else 0
        return height > max(price * min_size_pct, a * min_atr_mult)

    # scan for double bottoms / tops using last pivots at each bar
    for bar in range(600, n):
        # pivots confirmed before this bar
        ph_b = [(i, p) for i, p in ph if i < bar - 5]
        pl_b = [(i, p) for i, p in pl if i < bar - 5]
        if len(ph_b) < 1 or len(pl_b) < 2:
            continue
        chop_ok = chop.iloc[bar] < 62 if not pd.isna(chop.iloc[bar]) else True

        # Double bottom: pl[0] newest, pl[1] older, ph[0] middle
        if len(pl_b) >= 2 and len(ph_b) >= 1:
            p1b, p2b = pl_b[-1], pl_b[-2]
            mid_b = ph_b[-1]
            if p1b[0] > mid_b[0] > p2b[0] and _near(p1b[1], p2b[1], lvl_tol):
                neck = mid_b[1]
                height = neck - (p1b[1] + p2b[1]) / 2
                if valid_size(height, closes[bar], bar):
                    # breakout up through neckline + ATR margin
                    margin = atr.iloc[bar] * break_atr
                    if highs[bar] > neck + margin and closes[bar] > neck:
                        entry = df["open"].iloc[bar] if bar < n else closes[bar]
                        target = neck + height
                        stop = entry - abs(target - entry) * sl_pct_tgt
                        risk = abs(entry - stop)
                        reward = abs(target - entry)
                        if risk > 0 and reward / risk >= min_rr:
                            rr = reward / risk
                            conf = _confluence(True, rr, bool(htf_bull.iloc[bar]), bool(htf_bear.iloc[bar]), chop_ok, min_rr)
                            if conf >= min_conf:
                                signals.append(
                                    ForgeSignal(bar, "Double Bottom", True, entry, stop, target, neck, conf, _grade(conf, min_conf))
                                )

        # Double top
        if len(ph_b) >= 2 and len(pl_b) >= 1:
            p1, p2 = ph_b[-1], ph_b[-2]
            mid = pl_b[-1]
            if p1[0] > mid[0] > p2[0] and _near(p1[1], p2[1], lvl_tol):
                neck = mid[1]
                height = (p1[1] + p2[1]) / 2 - neck
                if valid_size(height, closes[bar], bar):
                    margin = atr.iloc[bar] * break_atr
                    if lows[bar] < neck - margin and closes[bar] < neck:
                        entry = df["open"].iloc[bar]
                        target = neck - height
                        stop = entry + abs(entry - target) * sl_pct_tgt
                        risk = abs(entry - stop)
                        reward = abs(entry - target)
                        if risk > 0 and reward / risk >= min_rr:
                            rr = reward / risk
                            conf = _confluence(False, rr, bool(htf_bull.iloc[bar]), bool(htf_bear.iloc[bar]), chop_ok, min_rr)
                            if conf >= min_conf:
                                signals.append(
                                    ForgeSignal(bar, "Double Top", False, entry, stop, target, neck, conf, _grade(conf, min_conf))
                                )

    return signals


def simulate_forge_signals(
    df: pd.DataFrame,
    signals: list[ForgeSignal],
    max_bars: int = 100,
    use_fixed_sl_pct: float | None = None,
    use_fixed_tp_pct: float | None = None,
) -> list[dict]:
    """Track each pattern signal to TP/SL outcome."""
    results = []
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    n = len(df)

    for sig in signals:
        entry = sig.entry
        if use_fixed_sl_pct is not None:
            stop = entry * (1 - use_fixed_sl_pct) if sig.bullish else entry * (1 + use_fixed_sl_pct)
        else:
            stop = sig.stop
        if use_fixed_tp_pct is not None:
            target = entry * (1 + use_fixed_tp_pct) if sig.bullish else entry * (1 - use_fixed_tp_pct)
        else:
            target = sig.target

        outcome = "open"
        exit_bar = sig.bar
        exit_price = entry
        max_fav, max_adv = 0.0, 0.0
        risk = abs(entry - stop)

        for j in range(sig.bar + 1, min(n, sig.bar + max_bars)):
            h, l = highs[j], lows[j]
            if sig.bullish:
                fav = (h - entry) / risk if risk else 0
                adv = (entry - l) / risk if risk else 0
                max_fav = max(max_fav, fav)
                max_adv = max(max_adv, adv)
                if l <= stop:
                    outcome, exit_bar, exit_price = "loss", j, stop
                    break
                if h >= target:
                    outcome, exit_bar, exit_price = "win", j, target
                    break
            else:
                fav = (entry - l) / risk if risk else 0
                adv = (h - entry) / risk if risk else 0
                max_fav = max(max_fav, fav)
                max_adv = max(max_adv, adv)
                if h >= stop:
                    outcome, exit_bar, exit_price = "loss", j, stop
                    break
                if l <= target:
                    outcome, exit_bar, exit_price = "win", j, target
                    break
        else:
            outcome = "timeout"
            exit_bar = min(n - 1, sig.bar + max_bars)
            exit_price = closes[exit_bar]

        r_mult = ((exit_price - entry) / risk if sig.bullish else (entry - exit_price) / risk) if risk else 0
        results.append(
            {
                "pattern": sig.pattern,
                "bullish": sig.bullish,
                "grade": sig.grade,
                "confluence": sig.confluence,
                "entry_bar": sig.bar,
                "outcome": outcome,
                "r_multiple": round(r_mult, 3),
                "max_favorable_R": round(max_fav, 3),
                "max_adverse_R": round(max_adv, 3),
                "bars_to_outcome": exit_bar - sig.bar,
            }
        )
    return results
