"""
Python mirror of Khakster MSE + EntryLib core logic for offline backtests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

PIP = 0.0001
PIVOT_REVERSE = 0
PIVOT_PULLBACK = 1
PIVOT_SETTLEMENT = 2
ENTRY_FTC = 1
ENTRY_RTP = 2


@dataclass
class MseSettings:
    len_h1: int = 24
    th_boost_h1: float = 1.154
    move_mult_min: float = 2.4
    move_mult_max: float = 3.6
    revert_mult: float = 1.0
    master_min_pct: float = 0.80
    master_max_pct: float = 1.20
    shape_pct: float = 0.80
    close_third_pct: float = 0.333
    zone_half_atr_pct: float = 0.50
    ftc_box_pct: float = 0.33
    pat_tr_ratio: float = 0.46
    spin_pct: float = 0.80
    std_pct: float = 1.20
    long_pct: float = 2.40
    pivot_lookback: int = 24


@dataclass
class EntrySettings:
    min_structure_score: int = 30
    sl_th_mult: float = 0.5
    tp_th_mult: float = 3.0
    use_ftc: bool = True
    use_rtp: bool = True


@dataclass
class StructureLevel:
    birth_time: pd.Timestamp
    pivot_price: float
    zone_top: float
    zone_bot: float
    ftc_top: float
    ftc_bot: float
    ftc_cred: bool
    is_high: bool
    th_pips: float
    score: int
    pivot_kind: int = PIVOT_REVERSE
    ftc_spent: bool = False
    rtp_top: float = np.nan
    rtp_bot: float = np.nan
    rtp_set: bool = False
    broken: bool = False
    traded_ftc: bool = False
    traded_rtp: bool = False


def to_pips(dist: float) -> float:
    return round(dist / PIP)


def tr_to_price(tr_pips: float) -> float:
    return PIP * tr_pips


def true_range(h: float, l: float, prev_c: float) -> float:
    return max(h - l, abs(h - prev_c), abs(l - prev_c))


def sma_tr_series(df: pd.DataFrame, length: int) -> pd.Series:
    trs = []
    prev_c = df["open"].iloc[0]
    for _, row in df.iterrows():
        trs.append(true_range(row["high"], row["low"], prev_c))
        prev_c = row["close"]
    return pd.Series(trs, index=df.index).rolling(length, min_periods=length).mean()


def candle_class(rng_pips: float, tr_pips: float, s: MseSettings) -> int:
    if tr_pips <= 0:
        return 0
    if rng_pips < tr_pips * s.spin_pct:
        return 1
    if rng_pips < tr_pips * s.std_pct:
        return 2
    if rng_pips < tr_pips * s.long_pct:
        return 3
    return 4


def is_master(o, h, l, c, tr_pips, s: MseSettings) -> bool:
    rng = h - l
    if rng <= 0 or tr_pips <= 0:
        return False
    tr_u = tr_to_price(tr_pips)
    size_ok = rng >= tr_u * s.master_min_pct and rng <= tr_u * s.master_max_pct
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    shape_ok = body / rng >= s.shape_pct or upper / rng >= s.shape_pct or lower / rng >= s.shape_pct
    return size_ok and shape_ok


def engulf_master(bear: bool, o0, h0, l0, c0, o1, h1, l1, c1) -> bool:
    return (c1 > max(o0, c0) and c1 > h0) if bear else (c1 < min(o0, c0) and c1 < l0)


def close_in_final_third(bear: bool, o, h, l, c, pct: float) -> bool:
    rng = h - l
    if rng <= 0:
        return False
    pos = (c - l) / rng
    return pos <= pct if bear else pos >= (1.0 - pct)


def leg_node_top(opens, closes, off: int, span: int) -> float:
    return max(max(opens[i], closes[i]) for i in range(off, off + span))


def leg_node_bot(opens, closes, off: int, span: int) -> float:
    return min(min(opens[i], closes[i]) for i in range(off, off + span))


def pivot_zones(is_high: bool, o1, h1, l1, c1, tr_pips, s: MseSettings):
    tr_u = tr_to_price(tr_pips)
    half = tr_u * s.zone_half_atr_pct
    ext_top = h1 if is_high else max(o1, c1)
    ext_bot = min(o1, c1) if is_high else l1
    in_top, in_bot = max(o1, c1), min(o1, c1)
    w = ext_top - ext_bot
    if w < half:
        mid = (ext_top + ext_bot) * 0.5
        ext_top = mid + half * 0.5
        ext_bot = mid - half * 0.5
    return ext_top, ext_bot, in_top, in_bot


def calc_ftc_bear(tip, o0, h0, l0, c0, o1, h1, l1, c1, opens, closes, tr_pips, s: MseSettings):
    pat_u = tr_to_price(tr_pips * s.pat_tr_ratio)
    box_top, box_bot = tip, min(l0, c0)
    box_mid = (box_top + box_bot) * 0.5
    half_box = (box_top - box_bot) * s.ftc_box_pct
    atr_mid = ((c0 + pat_u) + c0) * 0.5
    mid = (box_mid + atr_mid) * 0.5
    half = max(half_box, pat_u * 0.25)
    node_top = leg_node_top(opens, closes, 2, 3)
    cred = h0 > node_top and c0 < min(o1, c1)
    return mid + half, mid - half, cred


def calc_ftc_bull(tip, o0, h0, l0, c0, o1, h1, l1, c1, opens, closes, tr_pips, s: MseSettings):
    pat_u = tr_to_price(tr_pips * s.pat_tr_ratio)
    box_bot, box_top = tip, max(h0, c0)
    box_mid = (box_top + box_bot) * 0.5
    half_box = (box_top - box_bot) * s.ftc_box_pct
    atr_mid = ((c0 - pat_u) + c0) * 0.5
    mid = (box_mid + atr_mid) * 0.5
    half = max(half_box, pat_u * 0.25)
    node_bot = leg_node_bot(opens, closes, 2, 3)
    cred = l0 < node_bot and c0 > max(o1, c1)
    return mid + half, mid - half, cred


def kind_score_bonus(k: int) -> int:
    return 15 if k == PIVOT_REVERSE else -18 if k == PIVOT_PULLBACK else -28


def is_settlement_pivot(revert_pips: float, tr_pips: float, candle_cls: int) -> bool:
    return revert_pips <= tr_pips * 1.15 and candle_cls <= 1


def is_pullback_bear(h: np.ndarray, c: np.ndarray, tip_high: float, tr_pips: float, i: int, lookback: int) -> bool:
    tol = tr_to_price(tr_pips) * 0.6
    near = False
    broke = False
    for j in range(2, lookback + 1):
        if abs(h[i - j] - tip_high) <= tol:
            near = True
        if i - j - 1 >= 0 and h[i - j] > tip_high and c[i - j - 1] <= tip_high:
            broke = True
    return near and broke


def is_pullback_bull(l: np.ndarray, c: np.ndarray, tip_low: float, tr_pips: float, i: int, lookback: int) -> bool:
    tol = tr_to_price(tr_pips) * 0.6
    near = False
    broke = False
    for j in range(2, lookback + 1):
        if abs(l[i - j] - tip_low) <= tol:
            near = True
        if i - j - 1 >= 0 and l[i - j] < tip_low and c[i - j - 1] >= tip_low:
            broke = True
    return near and broke


def classify_pivot(is_high: bool, revert_pips: float, tr_pips: float, candle_cls: int, tip: float, h, l, c, i: int, s: MseSettings) -> int:
    lb = s.pivot_lookback
    pb = is_pullback_bear(h, c, tip, tr_pips, i, lb) if is_high else is_pullback_bull(l, c, tip, tr_pips, i, lb)
    st = is_settlement_pivot(revert_pips, tr_pips, candle_cls)
    if pb:
        return PIVOT_PULLBACK
    if st:
        return PIVOT_SETTLEMENT
    return PIVOT_REVERSE


def level_birth_score(ftc_cred: bool, candle_cls: int, pivot_kind: int) -> int:
    sc = 20  # H1 importance = 1 * 20
    sc += 25 if ftc_cred else 5
    sc += 8 if candle_cls == 2 else (4 if candle_cls >= 3 else 0)
    sc += kind_score_bonus(pivot_kind)
    return max(sc, 0)


def price_in_zone(hi, lo, z_top, z_bot) -> bool:
    return hi >= z_bot and lo <= z_top


def price_break_zone(is_high: bool, c, z_top, z_bot) -> bool:
    return c > z_top if is_high else c < z_bot


def close_below_img_line(c: float, tip_high: float, tr_pips: float) -> bool:
    return c < tip_high - tr_to_price(tr_pips)


def close_above_img_line(c: float, tip_low: float, tr_pips: float) -> bool:
    return c > tip_low + tr_to_price(tr_pips)


def detect_pivots_h1(df: pd.DataFrame, s: MseSettings) -> list[StructureLevel]:
    """Scan H1 bars for bear/bull pivots."""
    levels: list[StructureLevel] = []
    tr_s = sma_tr_series(df, s.len_h1)
    o = df["open"].values
    h = df["high"].values
    l = df["low"].values
    c = df["close"].values
    idx = df.index

    for i in range(5, len(df)):
        tr_val = tr_s.iloc[i]
        if pd.isna(tr_val) or tr_val <= 0:
            continue
        tr_p = to_pips(tr_val)
        th_p = to_pips(tr_val * s.th_boost_h1)
        move_p = sum(to_pips(true_range(h[i - j], l[i - j], c[i - j - 1])) for j in range(1, 4))
        opens = [o[i - k] for k in range(6)]
        closes = [c[i - k] for k in range(6)]

        # Bear pivot at bar i-1 confirmed by bar i
        masters = all(
            is_master(o[i - k], h[i - k], l[i - k], c[i - k], tr_p, s) and c[i - k] > o[i - k]
            for k in (1, 2, 3)
        )
        move_ok = move_p >= tr_p * s.move_mult_min and move_p <= tr_p * s.move_mult_max
        spike = candle_class(to_pips(h[i - 1] - l[i - 1]), tr_p, s) >= 3 and move_p >= tr_p * s.move_mult_min
        spike_close_b = spike and close_below_img_line(c[i], h[i - 1], tr_p)
        move_up = masters or move_ok or spike
        revert = to_pips(h[i - 1] - c[i]) >= tr_p * s.revert_mult
        engulf = close_below_img_line(c[i], h[i - 1], tr_p) if spike_close_b else engulf_master(
            True, o[i - 1], h[i - 1], l[i - 1], c[i - 1], o[i], h[i], l[i], c[i]
        )
        close_ok = True if spike_close_b else close_in_final_third(True, o[i], h[i], l[i], c[i], s.close_third_pct)
        master = is_master(o[i - 1], h[i - 1], l[i - 1], c[i - 1], tr_p, s)
        if move_up and revert and engulf and close_ok and (master or spike or revert):
            zt, zb, _, _ = pivot_zones(True, o[i - 1], h[i - 1], l[i - 1], c[i - 1], tr_p, s)
            cls = candle_class(to_pips(h[i - 1] - l[i - 1]), tr_p, s)
            rev_p = to_pips(h[i - 1] - c[i])
            kind = classify_pivot(True, rev_p, tr_p, cls, h[i - 1], h, l, c, i, s)
            ft, fb, fc = calc_ftc_bear(h[i - 1], o[i], h[i], l[i], c[i], o[i - 1], h[i - 1], l[i - 1], c[i - 1], opens, closes, tr_p, s)
            sc = level_birth_score(fc, cls, kind)
            levels.append(
                StructureLevel(idx[i - 1], h[i - 1], zt, zb, ft, fb, fc, True, th_p, sc, kind)
            )

        masters_b = all(
            is_master(o[i - k], h[i - k], l[i - k], c[i - k], tr_p, s) and c[i - k] < o[i - k]
            for k in (1, 2, 3)
        )
        spike_b = candle_class(to_pips(h[i - 1] - l[i - 1]), tr_p, s) >= 3 and move_p >= tr_p * s.move_mult_min
        spike_close_u = spike_b and close_above_img_line(c[i], l[i - 1], tr_p)
        move_dn = masters_b or move_ok or spike_b
        revert_b = to_pips(c[i] - l[i - 1]) >= tr_p * s.revert_mult
        engulf_b = close_above_img_line(c[i], l[i - 1], tr_p) if spike_close_u else engulf_master(
            False, o[i - 1], h[i - 1], l[i - 1], c[i - 1], o[i], h[i], l[i], c[i]
        )
        close_ok_b = True if spike_close_u else close_in_final_third(False, o[i], h[i], l[i], c[i], s.close_third_pct)
        if move_dn and revert_b and engulf_b and close_ok_b and (master or spike_b or revert_b):
            zt, zb, _, _ = pivot_zones(False, o[i - 1], h[i - 1], l[i - 1], c[i - 1], tr_p, s)
            cls = candle_class(to_pips(h[i - 1] - l[i - 1]), tr_p, s)
            rev_p = to_pips(c[i] - l[i - 1])
            kind = classify_pivot(False, rev_p, tr_p, cls, l[i - 1], h, l, c, i, s)
            ft, fb, fc = calc_ftc_bull(l[i - 1], o[i], h[i], l[i], c[i], o[i - 1], h[i - 1], l[i - 1], c[i - 1], opens, closes, tr_p, s)
            sc = level_birth_score(fc, cls, kind)
            levels.append(
                StructureLevel(idx[i - 1], l[i - 1], zt, zb, ft, fb, fc, False, th_p, sc, kind)
            )
    return levels


def ftc_touch(lv: StructureLevel, hi, lo, prev_hi, prev_lo) -> bool:
    if not lv.ftc_cred or lv.broken or lv.traded_ftc:
        return False
    return price_in_zone(hi, lo, lv.ftc_top, lv.ftc_bot) and not price_in_zone(prev_hi, prev_lo, lv.ftc_top, lv.ftc_bot)


def rtp_touch(lv: StructureLevel, hi, lo, prev_hi, prev_lo) -> bool:
    if not lv.ftc_spent or not lv.rtp_set or lv.broken or lv.traded_rtp:
        return False
    return price_in_zone(hi, lo, lv.rtp_top, lv.rtp_bot) and not price_in_zone(prev_hi, prev_lo, lv.rtp_top, lv.rtp_bot)


def rtp_from_bar(is_high: bool, o, h, l, c):
    if is_high:
        return max(o, c), min(l, min(o, c))
    return max(h, max(o, c)), min(o, c)


def entry_sl_tp(is_high: bool, z_top, z_bot, pivot, th_pips, e: EntrySettings):
    pad = tr_to_price(th_pips * e.sl_th_mult)
    tp_dist = tr_to_price(th_pips * e.tp_th_mult)
    sl = z_top + pad if is_high else z_bot - pad
    tp = pivot - tp_dist if is_high else pivot + tp_dist
    return sl, tp


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
    kind: str = "FTC"


def run_backtest(h1: pd.DataFrame, m5: pd.DataFrame, s: MseSettings, e: EntrySettings) -> tuple[list[Trade], list[StructureLevel]]:
    levels = detect_pivots_h1(h1, s)
    active: list[StructureLevel] = []
    trades: list[Trade] = []
    open_trade: Optional[Trade] = None
    level_idx = 0

    m5 = m5.sort_index()
    h1_times = sorted(h1.index)
    prev_h, prev_l = np.nan, np.nan

    for t, row in m5.iterrows():
        while level_idx < len(levels) and levels[level_idx].birth_time <= t:
            lv = levels[level_idx]
            if lv.score >= e.min_structure_score and lv.ftc_cred:
                active.append(lv)
            level_idx += 1

        hi, lo, o, c = row["high"], row["low"], row["open"], row["close"]

        if open_trade:
            ot = open_trade
            hit_sl = hi >= ot.sl if ot.side == "short" else lo <= ot.sl
            hit_tp = lo <= ot.tp if ot.side == "short" else hi >= ot.tp
            if hit_sl and hit_tp:
                # conservative: SL first
                ot.exit_price = ot.sl
            elif hit_sl:
                ot.exit_price = ot.sl
            elif hit_tp:
                ot.exit_price = ot.tp
            if ot.exit_price is not None:
                ot.exit_time = t
                ot.pnl_pips = to_pips(ot.entry - ot.exit_price) if ot.side == "short" else to_pips(ot.exit_price - ot.entry)
                trades.append(ot)
                open_trade = None

        if open_trade is None:
            for lv in active:
                if lv.broken:
                    continue
                ent = None
                if e.use_ftc and ftc_touch(lv, hi, lo, prev_h, prev_l):
                    ent = ENTRY_FTC
                elif e.use_rtp and rtp_touch(lv, hi, lo, prev_h, prev_l):
                    ent = ENTRY_RTP
                if ent:
                    sl, tp = entry_sl_tp(lv.is_high, lv.zone_top, lv.zone_bot, lv.pivot_price, lv.th_pips, e)
                    open_trade = Trade(t, None, "short" if lv.is_high else "long", c, sl, tp, kind="FTC" if ent == ENTRY_FTC else "RTP")
                    if ent == ENTRY_FTC:
                        lv.traded_ftc = True
                    else:
                        lv.traded_rtp = True
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
        open_trade.pnl_pips = (
            to_pips(open_trade.entry - open_trade.exit_price)
            if open_trade.side == "short"
            else to_pips(open_trade.exit_price - open_trade.entry)
        )
        trades.append(open_trade)

    return trades, levels
