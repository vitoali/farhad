#!/usr/bin/env python3
"""Offline ~1-month backtest of ICT Judas Dual (multi-session + M5/M1) on EURUSD M1.

Ports pine/ict_judas_dual_m5m1.pine defaults.
Data: HistData ASCII M1 (EST no-DST) + Yahoo Finance recent M1.
Sessions evaluated in America/New_York (DST-aware), matching Pine tz input.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_ict22_eurusd import (
    atr,
    detect_fvg,
    load_pair,
    pivots,
    resample_ohlc,
)

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "backtest_judas_dual_eurusd_results.json"

# ── parameters (match Pine defaults) ─────────────────────────────────────────
PIVOT_L = PIVOT_R = 5
SMT_LB = 20
DISP_ATR_MULT = 1.5
ATR_LEN = 10
OTE_LO, OTE_HI = 0.618, 0.705
MIN_RR = 2.5
SL_PIPS = 2.0
PIP = 0.0001
TP1_PCT = 0.50
LIMIT_EXPIRE = 40
REQUIRE_SMT = False
REQUIRE_CHOCH = True
REQUIRE_OTE = True
ENABLE_M5 = True
ENABLE_M1 = True
M5_PRIORITY = True
ALLOW_FILL_OUTSIDE_HUNT = True
ASIA_USES_PDH = True
DAY_RESET_HOUR = 17


def to_ny(df: pd.DataFrame) -> pd.DataFrame:
    """Convert loaded timestamps (Etc/GMT+5 HistData / UTC Yahoo) to America/New_York."""
    out = df.copy()
    ts = out["timestamp"]
    # Already tz-aware from loaders
    out["timestamp"] = ts.dt.tz_convert("America/New_York")
    return out


def hm(ts: pd.Timestamp) -> int:
    return ts.hour * 100 + ts.minute


def in_range_asia(ts: pd.Timestamp) -> bool:
    # 20:00-00:00
    return hm(ts) >= 2000


def in_range_lon(ts: pd.Timestamp) -> bool:
    # 02:00-07:00
    return 200 <= hm(ts) < 700


def in_range_ny(ts: pd.Timestamp) -> bool:
    # 07:00-12:00
    return 700 <= hm(ts) < 1200


def in_hunt_asia(ts: pd.Timestamp) -> bool:
    return hm(ts) >= 2000


def in_hunt_lon(ts: pd.Timestamp) -> bool:
    return 200 <= hm(ts) < 500


def in_hunt_ny(ts: pd.Timestamp) -> bool:
    return 700 <= hm(ts) < 1000


def fx_day_key(ts: pd.Timestamp) -> int:
    adj = ts - pd.Timedelta(hours=DAY_RESET_HOUR)
    return int(adj.strftime("%Y%m%d"))


def hunt_name(ts: pd.Timestamp) -> str:
    if in_hunt_asia(ts):
        return "Asia"
    if in_hunt_lon(ts):
        return "London"
    if in_hunt_ny(ts):
        return "New York"
    return "—"


@dataclass
class Trade:
    direction: int
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp1: float
    tp2: float
    tag: str = ""
    exit_time: pd.Timestamp | None = None
    exit: float | None = None
    result_R: float | None = None
    win: bool | None = None
    note: str = ""


def rr_ok(entry: float, sl: float, tp1: float, direction: int) -> bool:
    risk = abs(entry - sl)
    if risk <= 0 or np.isnan(tp1):
        return False
    reward = abs(tp1 - entry)
    if reward / risk < MIN_RR:
        return False
    if direction < 0:
        return tp1 < entry and sl > entry
    return tp1 > entry and sl < entry


def run_backtest(eur: pd.DataFrame, gbp: pd.DataFrame, start: str, end: str) -> dict:
    eur = to_ny(eur)
    gbp = to_ny(gbp)
    start_ts = pd.Timestamp(start, tz="America/New_York")
    end_ts = pd.Timestamp(end, tz="America/New_York")
    eur = eur[(eur["timestamp"] >= start_ts) & (eur["timestamp"] <= end_ts)].reset_index(drop=True)
    gbp = gbp[(gbp["timestamp"] >= start_ts) & (gbp["timestamp"] <= end_ts)].reset_index(drop=True)

    g = gbp.set_index("timestamp")[["open", "high", "low", "close"]].rename(
        columns=lambda c: "g_" + c
    )
    e = eur.set_index("timestamp")
    m = e.join(g, how="left").ffill().dropna().reset_index()

    h1 = resample_ohlc(m, "1h")
    m5 = resample_ohlc(m, "5min")

    def prep(htf: pd.DataFrame):
        o = htf["open"].to_numpy()
        h = htf["high"].to_numpy()
        l = htf["low"].to_numpy()
        c = htf["close"].to_numpy()
        ph, pl = pivots(h, l, PIVOT_L, PIVOT_R)
        bull, bear, bt, bb, st, sb = detect_fvg(o, h, l, c)
        a = atr(h, l, c, ATR_LEN)
        return {
            "index": htf.index,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "ph": ph,
            "pl": pl,
            "bull": bull,
            "bear": bear,
            "bt": bt,
            "bb": bb,
            "st": st,
            "sb": sb,
            "atr": a,
        }

    H1 = prep(h1)
    M5 = prep(m5)

    m1_ts = pd.DatetimeIndex(m["timestamp"])
    i1 = H1["index"].get_indexer(m1_ts, method="ffill")
    i5 = M5["index"].get_indexer(m1_ts, method="ffill")

    o = m["open"].to_numpy()
    h = m["high"].to_numpy()
    l = m["low"].to_numpy()
    c = m["close"].to_numpy()
    gh = m["g_high"].to_numpy()
    gl = m["g_low"].to_numpy()
    atr1 = atr(h, l, c, ATR_LEN)
    bull1, bear1, b1t, b1b, s1t, s1b = detect_fvg(o, h, l, c)
    m1_ph, m1_pl = pivots(h, l, 3, 2)

    trades: list[Trade] = []
    pending = None
    position = None
    funnel = {
        "sweep": 0,
        "smt": 0,
        "choch": 0,
        "ote": 0,
        "entry_m5": 0,
        "entry_m1": 0,
        "entry_signal": 0,
        "fills": 0,
        "rr_fail": 0,
        "pending_cancel": 0,
    }

    step_sweep = step_smt = step_choch = step_ote = step_entry = False
    sweep_dir = 0
    sweep_level = np.nan
    sweep_src = ""
    active_hunt = "—"
    state_day = None

    asia_h = asia_l = lon_h = lon_l = ny_h = ny_l = np.nan
    locked_asia_h = locked_asia_l = locked_lon_h = locked_lon_l = locked_ny_h = locked_ny_l = np.nan
    was_asia = was_lon = was_ny = False
    pd_high = pd_low = np.nan
    cur_day_hi = cur_day_lo = np.nan

    m5_last_hl = m5_last_lh = np.nan
    m5_leg_hi = m5_leg_lo = m5_choch_lvl = np.nan
    m5_trail_hi = m5_trail_lo = np.nan
    last_m1_sh = last_m1_sl = np.nan
    prev_h1_c = prev_m5_c = np.nan
    order_sent = False

    n = len(m)
    for i in range(n):
        ts = m1_ts[i]
        day = fx_day_key(ts)
        name = hunt_name(ts)
        is_asia_r = in_range_asia(ts)
        is_lon_r = in_range_lon(ts)
        is_ny_r = in_range_ny(ts)
        is_asia_h = in_hunt_asia(ts)
        is_lon_h = in_hunt_lon(ts)
        is_ny_h = in_hunt_ny(ts)
        in_hunt = is_asia_h or is_lon_h or is_ny_h

        new_fx_day = state_day is None or day != state_day
        if new_fx_day:
            if state_day is not None and not np.isnan(cur_day_hi):
                pd_high, pd_low = cur_day_hi, cur_day_lo
            state_day = day
            cur_day_hi, cur_day_lo = h[i], l[i]
        else:
            cur_day_hi = max(cur_day_hi, h[i])
            cur_day_lo = min(cur_day_lo, l[i])

        # live session ranges + lock on exit
        if is_asia_r:
            if not was_asia:
                asia_h, asia_l = h[i], l[i]
            else:
                asia_h = max(asia_h, h[i])
                asia_l = min(asia_l, l[i])
        if was_asia and not is_asia_r and not np.isnan(asia_h):
            locked_asia_h, locked_asia_l = asia_h, asia_l

        if is_lon_r:
            if not was_lon:
                lon_h, lon_l = h[i], l[i]
            else:
                lon_h = max(lon_h, h[i])
                lon_l = min(lon_l, l[i])
        if was_lon and not is_lon_r and not np.isnan(lon_h):
            locked_lon_h, locked_lon_l = lon_h, lon_l

        if is_ny_r:
            if not was_ny:
                ny_h, ny_l = h[i], l[i]
            else:
                ny_h = max(ny_h, h[i])
                ny_l = min(ny_l, l[i])
        if was_ny and not is_ny_r and not np.isnan(ny_h):
            locked_ny_h, locked_ny_l = ny_h, ny_l

        was_asia, was_lon, was_ny = is_asia_r, is_lon_r, is_ny_r

        # hunt targets
        target_high = target_low = alt_high = alt_low = np.nan
        if is_asia_h:
            target_high, target_low = locked_ny_h, locked_ny_l
            if ASIA_USES_PDH:
                alt_high, alt_low = pd_high, pd_low
            if np.isnan(target_high):
                target_high, target_low = pd_high, pd_low
        elif is_lon_h:
            target_high = locked_asia_h if not np.isnan(locked_asia_h) else asia_h
            target_low = locked_asia_l if not np.isnan(locked_asia_l) else asia_l
        elif is_ny_h:
            target_high = locked_lon_h if not np.isnan(locked_lon_h) else lon_h
            target_low = locked_lon_l if not np.isnan(locked_lon_l) else lon_l

        # reset setup on hunt change / new FX day
        do_reset = (name != active_hunt) or new_fx_day
        if do_reset:
            if order_sent and position is None:
                pending = None
            step_sweep = step_smt = step_choch = step_ote = step_entry = False
            sweep_dir = 0
            sweep_level = np.nan
            sweep_src = ""
            m5_leg_hi = m5_leg_lo = m5_choch_lvl = np.nan
            m5_trail_hi = m5_trail_lo = np.nan
            pending = None
            order_sent = False
            active_hunt = name

        j1 = i1[i]
        j5 = i5[i]
        if j1 >= 1:
            k = j1 - 1
            h1_c = H1["close"][k]
            h1_h = H1["high"][k]
            h1_l = H1["low"][k]
            h1_closed = (not np.isnan(prev_h1_c)) and (h1_c != prev_h1_c)
        else:
            h1_c = h1_h = h1_l = np.nan
            h1_closed = False

        if j5 >= 1:
            k = j5 - 1
            m5_o = M5["open"][k]
            m5_c = M5["close"][k]
            m5_h = M5["high"][k]
            m5_l = M5["low"][k]
            m5_a = M5["atr"][k]
            m5_bull = M5["bull"][k]
            m5_bear = M5["bear"][k]
            m5_bt, m5_bb = M5["bt"][k], M5["bb"][k]
            m5_st, m5_sb = M5["st"][k], M5["sb"][k]
            if not np.isnan(M5["ph"][k]):
                m5_last_lh = M5["ph"][k]
            if not np.isnan(M5["pl"][k]):
                m5_last_hl = M5["pl"][k]
            m5_closed = (not np.isnan(prev_m5_c)) and (m5_c != prev_m5_c)
        else:
            m5_o = m5_c = m5_h = m5_l = m5_a = np.nan
            m5_bull = m5_bear = False
            m5_bt = m5_bb = m5_st = m5_sb = np.nan
            m5_closed = False

        # manage open position
        if position is not None:
            hit_sl = (l[i] <= position.sl) if position.direction > 0 else (h[i] >= position.sl)
            hit_tp1 = (h[i] >= position.tp1) if position.direction > 0 else (l[i] <= position.tp1)
            hit_tp2 = (h[i] >= position.tp2) if position.direction > 0 else (l[i] <= position.tp2)
            if hit_sl:
                position.exit = position.sl
                position.exit_time = ts
                position.result_R = -1.0
                position.win = False
                position.note = "SL"
                trades.append(position)
                position = None
                order_sent = False
            elif hit_tp2:
                risk = abs(position.entry - position.sl)
                r1 = abs(position.tp1 - position.entry) / risk
                r2 = abs(position.tp2 - position.entry) / risk
                position.exit = position.tp2
                position.exit_time = ts
                position.result_R = 0.5 * r1 + 0.5 * r2
                position.win = True
                position.note = "TP2"
                trades.append(position)
                position = None
                order_sent = False
            elif hit_tp1 and not getattr(position, "tp1_done", False):
                position.tp1_done = True  # type: ignore[attr-defined]
                position.sl = position.entry  # BE

        # fill / cancel pending
        if pending is not None and position is None:
            pending["age"] += 1
            expire = pending["age"] > LIMIT_EXPIRE
            breach = (pending["dir"] < 0 and c[i] > pending["fvg_top"]) or (
                pending["dir"] > 0 and c[i] < pending["fvg_bot"]
            )
            hunt_ended = (not ALLOW_FILL_OUTSIDE_HUNT) and (not in_hunt)
            if expire or breach or hunt_ended:
                pending = None
                step_entry = False
                order_sent = False
                funnel["pending_cancel"] += 1
            else:
                filled = False
                if pending["dir"] < 0 and h[i] >= pending["limit"] and l[i] <= pending["limit"]:
                    filled = True
                if pending["dir"] > 0 and l[i] <= pending["limit"] and h[i] >= pending["limit"]:
                    filled = True
                if filled:
                    position = Trade(
                        direction=pending["dir"],
                        entry_time=ts,
                        entry=pending["limit"],
                        sl=pending["sl"],
                        tp1=pending["tp1"],
                        tp2=pending["tp2"],
                        tag=pending["tag"],
                    )
                    funnel["fills"] += 1
                    pending = None

        def swept_bear(lvl: float) -> bool:
            if np.isnan(lvl):
                return False
            return (h1_closed and h1_h > lvl and h1_c < lvl) or (
                m5_closed and m5_h > lvl and m5_c < lvl
            )

        def swept_bull(lvl: float) -> bool:
            if np.isnan(lvl):
                return False
            return (h1_closed and h1_l < lvl and h1_c > lvl) or (
                m5_closed and m5_l < lvl and m5_c > lvl
            )

        # Step 1 sweep
        if in_hunt and not step_sweep:
            bear_pri = swept_bear(target_high)
            bear_alt = swept_bear(alt_high)
            bull_pri = swept_bull(target_low)
            bull_alt = swept_bull(alt_low)
            if bear_pri or bear_alt:
                step_sweep = True
                sweep_dir = -1
                sweep_level = target_high if bear_pri else alt_high
                sweep_src = (
                    "H1"
                    if h1_closed and h1_h > sweep_level and h1_c < sweep_level
                    else "M5"
                )
                funnel["sweep"] += 1
            elif bull_pri or bull_alt:
                step_sweep = True
                sweep_dir = 1
                sweep_level = target_low if bull_pri else alt_low
                sweep_src = (
                    "H1"
                    if h1_closed and h1_l < sweep_level and h1_c > sweep_level
                    else "M5"
                )
                funnel["sweep"] += 1

        # Step 2 SMT (optional; default off → auto true)
        if step_sweep and not step_smt:
            if not REQUIRE_SMT:
                step_smt = True
                funnel["smt"] += 1
            elif j1 >= SMT_LB + 2:
                k = j1 - 1
                p_hiN = np.max(H1["high"][max(0, k - SMT_LB + 1) : k + 1])
                p_hiP = np.max(H1["high"][max(0, k - SMT_LB) : k])
                p_loN = np.min(H1["low"][max(0, k - SMT_LB + 1) : k + 1])
                p_loP = np.min(H1["low"][max(0, k - SMT_LB) : k])
                i0 = max(0, i - SMT_LB * 60)
                c_hiN = np.max(gh[i0 : i + 1])
                c_hiP = np.max(gh[i0:i]) if i > i0 else c_hiN
                c_loN = np.min(gl[i0 : i + 1])
                c_loP = np.min(gl[i0:i]) if i > i0 else c_loN
                smt_bear = p_hiN > p_hiP and not (c_hiN > c_hiP)
                smt_bull = p_loN < p_loP and not (c_loN < c_loP)
                step_smt = smt_bear if sweep_dir < 0 else smt_bull
                if step_smt:
                    funnel["smt"] += 1

        # Step 3 CHoCH
        if step_sweep and step_smt and not step_choch and m5_closed:
            if not REQUIRE_CHOCH:
                step_choch = True
                m5_choch_lvl = m5_last_hl if sweep_dir < 0 else m5_last_lh
                if np.isnan(m5_choch_lvl):
                    m5_choch_lvl = m5_l if sweep_dir < 0 else m5_h
                m5_leg_hi, m5_leg_lo = m5_h, m5_l
                m5_trail_hi, m5_trail_lo = m5_h, m5_l
                funnel["choch"] += 1
            else:
                if sweep_dir < 0 and not np.isnan(m5_last_hl) and m5_c < m5_last_hl:
                    step_choch = True
                    m5_choch_lvl = m5_last_hl
                    m5_leg_hi = max(m5_h, m5_choch_lvl)
                    m5_leg_lo = m5_l
                    m5_trail_hi, m5_trail_lo = m5_h, m5_l
                    funnel["choch"] += 1
                elif sweep_dir > 0 and not np.isnan(m5_last_lh) and m5_c > m5_last_lh:
                    step_choch = True
                    m5_choch_lvl = m5_last_lh
                    m5_leg_hi = m5_h
                    m5_leg_lo = min(m5_l, m5_choch_lvl)
                    m5_trail_hi, m5_trail_lo = m5_h, m5_l
                    funnel["choch"] += 1

        if step_choch and not step_ote and m5_closed:
            if sweep_dir < 0:
                m5_trail_lo = min(m5_trail_lo if not np.isnan(m5_trail_lo) else m5_l, m5_l)
                m5_leg_lo = m5_trail_lo
                m5_leg_hi = max(
                    m5_leg_hi if not np.isnan(m5_leg_hi) else m5_choch_lvl, m5_choch_lvl
                )
            else:
                m5_trail_hi = max(m5_trail_hi if not np.isnan(m5_trail_hi) else m5_h, m5_h)
                m5_leg_hi = m5_trail_hi
                m5_leg_lo = min(
                    m5_leg_lo if not np.isnan(m5_leg_lo) else m5_choch_lvl, m5_choch_lvl
                )

        # Step 4 OTE
        if (
            step_choch
            and not step_ote
            and not np.isnan(m5_leg_hi)
            and not np.isnan(m5_leg_lo)
            and m5_leg_hi > m5_leg_lo
        ):
            if not REQUIRE_OTE:
                step_ote = True
                funnel["ote"] += 1
            else:
                rng = m5_leg_hi - m5_leg_lo
                if sweep_dir < 0:
                    lo = m5_leg_lo + rng * OTE_LO
                    hi = m5_leg_lo + rng * OTE_HI
                else:
                    lo = m5_leg_hi - rng * OTE_HI
                    hi = m5_leg_hi - rng * OTE_LO
                if h[i] >= min(lo, hi) and l[i] <= max(lo, hi):
                    step_ote = True
                    funnel["ote"] += 1

        if not np.isnan(m1_ph[i]):
            last_m1_sh = m1_ph[i]
        if not np.isnan(m1_pl[i]):
            last_m1_sl = m1_pl[i]

        # Dual entry
        ready = step_ote and not step_entry and not order_sent and position is None and pending is None
        can_arm = in_hunt or ALLOW_FILL_OUTSIDE_HUNT
        if ready and can_arm:
            body = abs(c[i] - o[i])
            disp_dn_m1 = c[i] < o[i] and (not np.isnan(atr1[i])) and body >= atr1[i] * DISP_ATR_MULT
            disp_up_m1 = c[i] > o[i] and (not np.isnan(atr1[i])) and body >= atr1[i] * DISP_ATR_MULT
            m5_body = abs(m5_c - m5_o) if not np.isnan(m5_c) else 0.0
            disp_dn_m5 = (
                m5_closed
                and m5_c < m5_o
                and not np.isnan(m5_a)
                and m5_body >= m5_a * DISP_ATR_MULT
            )
            disp_up_m5 = (
                m5_closed
                and m5_c > m5_o
                and not np.isnan(m5_a)
                and m5_body >= m5_a * DISP_ATR_MULT
            )

            t1 = target_low if sweep_dir < 0 else target_high
            t2 = pd_low if sweep_dir < 0 else pd_high

            armed = False
            if ENABLE_M5 and not armed:
                if sweep_dir < 0 and disp_dn_m5 and m5_bear:
                    lim = m5_st
                    sl = (m5_h if not np.isnan(m5_h) else h[i]) + SL_PIPS * PIP
                    if not np.isnan(t1) and not np.isnan(t2) and rr_ok(lim, sl, t1, -1):
                        pending = {
                            "dir": -1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": m5_st,
                            "fvg_bot": m5_sb,
                            "age": 0,
                            "tag": "M5_Short",
                        }
                        armed = True
                        funnel["entry_m5"] += 1
                    else:
                        funnel["rr_fail"] += 1
                elif sweep_dir > 0 and disp_up_m5 and m5_bull:
                    lim = m5_bb
                    sl = (m5_l if not np.isnan(m5_l) else l[i]) - SL_PIPS * PIP
                    if not np.isnan(t1) and not np.isnan(t2) and rr_ok(lim, sl, t1, 1):
                        pending = {
                            "dir": 1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": m5_bt,
                            "fvg_bot": m5_bb,
                            "age": 0,
                            "tag": "M5_Long",
                        }
                        armed = True
                        funnel["entry_m5"] += 1
                    else:
                        funnel["rr_fail"] += 1

            allow_m1 = ENABLE_M1 and (not M5_PRIORITY or not ENABLE_M5 or not armed)
            if allow_m1 and not armed:
                if sweep_dir < 0 and disp_dn_m1 and bear1[i]:
                    lim = s1t[i]
                    sl = (last_m1_sh if not np.isnan(last_m1_sh) else h[i]) + SL_PIPS * PIP
                    if not np.isnan(t1) and not np.isnan(t2) and rr_ok(lim, sl, t1, -1):
                        pending = {
                            "dir": -1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": s1t[i],
                            "fvg_bot": s1b[i],
                            "age": 0,
                            "tag": "M1_Short",
                        }
                        armed = True
                        funnel["entry_m1"] += 1
                    else:
                        funnel["rr_fail"] += 1
                elif sweep_dir > 0 and disp_up_m1 and bull1[i]:
                    lim = b1b[i]
                    sl = (last_m1_sl if not np.isnan(last_m1_sl) else l[i]) - SL_PIPS * PIP
                    if not np.isnan(t1) and not np.isnan(t2) and rr_ok(lim, sl, t1, 1):
                        pending = {
                            "dir": 1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": b1t[i],
                            "fvg_bot": b1b[i],
                            "age": 0,
                            "tag": "M1_Long",
                        }
                        armed = True
                        funnel["entry_m1"] += 1
                    else:
                        funnel["rr_fail"] += 1

            if armed:
                step_entry = True
                order_sent = True
                funnel["entry_signal"] += 1

        if j1 >= 1:
            prev_h1_c = H1["close"][j1 - 1]
        if j5 >= 1:
            prev_m5_c = M5["close"][j5 - 1]

    if position is not None:
        position.exit = c[-1]
        position.exit_time = m1_ts[-1]
        risk = abs(position.entry - position.sl)
        position.result_R = (position.exit - position.entry) / risk * position.direction
        position.win = position.result_R > 0
        position.note = "EOD"
        trades.append(position)

    wins = [t for t in trades if t.win]
    losses = [t for t in trades if t.win is False]
    n_tr = len(trades)
    wr = (len(wins) / n_tr * 100) if n_tr else 0.0
    avg_R = float(np.mean([t.result_R for t in trades])) if trades else 0.0
    sum_R = float(np.sum([t.result_R for t in trades])) if trades else 0.0
    by_tag: dict[str, int] = {}
    for t in trades:
        by_tag[t.tag] = by_tag.get(t.tag, 0) + 1

    return {
        "symbol": "EURUSD",
        "strategy": "Judas Dual M5/M1",
        "corr": "GBPUSD",
        "period_start": str(m1_ts[0]),
        "period_end": str(m1_ts[-1]),
        "bars_m1": int(n),
        "timezone": "America/New_York",
        "params": {
            "disp_atr_mult": DISP_ATR_MULT,
            "min_rr": MIN_RR,
            "require_smt": REQUIRE_SMT,
            "require_choch": REQUIRE_CHOCH,
            "require_ote": REQUIRE_OTE,
            "enable_m5": ENABLE_M5,
            "enable_m1": ENABLE_M1,
            "limit_expire": LIMIT_EXPIRE,
        },
        "trades": n_tr,
        "wins": len(wins),
        "losses": len(losses),
        "winrate_pct": round(wr, 2),
        "avg_R": round(avg_R, 3),
        "sum_R": round(sum_R, 3),
        "by_tag": by_tag,
        "trade_log": [
            {
                "dir": "LONG" if t.direction > 0 else "SHORT",
                "tag": t.tag,
                "entry_time": str(t.entry_time),
                "entry": round(t.entry, 5),
                "sl": round(t.sl, 5),
                "tp1": round(t.tp1, 5),
                "tp2": round(t.tp2, 5) if t.tp2 == t.tp2 else None,
                "exit_time": str(t.exit_time),
                "exit": round(t.exit, 5) if t.exit is not None else None,
                "R": round(t.result_R, 3) if t.result_R is not None else None,
                "win": t.win,
                "note": t.note,
            }
            for t in trades
        ],
        "funnel": funnel,
        "notes": [
            "HistData EST-no-DST converted to America/New_York for session windows (DST-aware).",
            "Offline port of pine/ict_judas_dual_m5m1.pine — approximate vs TradingView ticks.",
            "Dual entry: M5 Disp+FVG preferred, else M1; one position max.",
        ],
    }


def main():
    print("Loading EURUSD / GBPUSD ...")
    eur = load_pair("EURUSD")
    gbp = load_pair("GBPUSD")
    print(f"EUR {len(eur)} {eur['timestamp'].min()} → {eur['timestamp'].max()}")
    print(f"GBP {len(gbp)} {gbp['timestamp'].min()} → {gbp['timestamp'].max()}")

    start = "2026-06-19"
    end = "2026-07-18"
    print(f"Backtest window {start} → {end} (America/New_York sessions)")

    # defaults
    res_default = run_backtest(eur, gbp, start, end)

    # sensitivity: looser displacement + RR (same as ICT22 sensitivity idea)
    global DISP_ATR_MULT, MIN_RR
    DISP_ATR_MULT = 1.0
    MIN_RR = 2.0
    res_loose = run_backtest(eur, gbp, start, end)
    DISP_ATR_MULT = 1.5
    MIN_RR = 2.5

    out = {
        "default_pine_params": res_default,
        "sensitivity_disp1_rr2": res_loose,
    }
    OUT.write_text(json.dumps(out, indent=2))

    def summarize(label: str, res: dict):
        print(f"\n=== {label} ===")
        print(
            json.dumps(
                {
                    k: res[k]
                    for k in res
                    if k not in ("trade_log", "notes")
                },
                indent=2,
            )
        )
        if res["trade_log"]:
            print("Trades:")
            for t in res["trade_log"]:
                print(
                    f"  {t['tag']:9} {t['dir']:5} {t['entry_time']} → {t['exit_time']}  "
                    f"R={t['R']}  {t['note']}  win={t['win']}"
                )

    summarize("DEFAULT (disp1.5, RR2.5, SMT off)", res_default)
    summarize("SENSITIVITY (disp1.0, RR2.0)", res_loose)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
