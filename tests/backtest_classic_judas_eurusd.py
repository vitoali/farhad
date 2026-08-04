#!/usr/bin/env python3
"""Offline backtest: Classic Judas (Asia range → London Open) on EURUSD M1.

Ports Mode B from pine/ict_judas_dual_m5m1.pine:
  Asia 20:00–00:00 NY → London hunt 02:00–05:00
  Sweep Asia H/L → reclaim inside → 5m CHoCH → M5/M1 Disp+FVG
  SL @ sweep extreme | TP1 Asia mid | TP2 opposite Asia
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from backtest_ict22_eurusd import atr, detect_fvg, load_pair, pivots, resample_ohlc
from backtest_judas_dual_eurusd import fx_day_key, hm, in_hunt_lon, in_range_asia, to_ny

OUT = Path(__file__).parent / "backtest_classic_judas_eurusd_results.json"

DISP_ATR_MULT = 1.5
ATR_LEN = 10
OTE_LO, OTE_HI = 0.618, 0.705
CLASSIC_MIN_RR = 1.5  # match Pine Classic default
SL_PIPS = 2.0
PIP = 0.0001
LIMIT_EXPIRE = 60
REQUIRE_CHOCH = True
REQUIRE_OTE = False
REQUIRE_RECLAIM = True
ENABLE_M5 = True
ENABLE_M1 = True
M5_PRIORITY = True
ALLOW_FILL_OUTSIDE = True
PIVOT_L = PIVOT_R = 5


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


def rr_ok(entry, sl, tp1, direction, min_rr) -> bool:
    risk = abs(entry - sl)
    if risk <= 0 or np.isnan(tp1):
        return False
    reward = abs(tp1 - entry)
    if reward / risk < min_rr:
        return False
    if direction < 0:
        return tp1 < entry and sl > entry
    return tp1 > entry and sl < entry


def run_classic(eur: pd.DataFrame, start: str, end: str) -> dict:
    eur = to_ny(eur)
    start_ts = pd.Timestamp(start, tz="America/New_York")
    end_ts = pd.Timestamp(end, tz="America/New_York")
    m = eur[(eur["timestamp"] >= start_ts) & (eur["timestamp"] <= end_ts)].reset_index(drop=True)

    m5 = resample_ohlc(m, "5min")
    o5 = m5["open"].to_numpy()
    h5 = m5["high"].to_numpy()
    l5 = m5["low"].to_numpy()
    c5 = m5["close"].to_numpy()
    ph5, pl5 = pivots(h5, l5, PIVOT_L, PIVOT_R)
    bull5, bear5, bt5, bb5, st5, sb5 = detect_fvg(o5, h5, l5, c5)
    atr5 = atr(h5, l5, c5, ATR_LEN)

    m1_ts = pd.DatetimeIndex(m["timestamp"])
    i5 = m5.index.get_indexer(m1_ts, method="ffill")

    o = m["open"].to_numpy()
    h = m["high"].to_numpy()
    l = m["low"].to_numpy()
    c = m["close"].to_numpy()
    atr1 = atr(h, l, c, ATR_LEN)
    bull1, bear1, b1t, b1b, s1t, s1b = detect_fvg(o, h, l, c)

    trades: list[Trade] = []
    pending = None
    position = None
    funnel = {
        "sweep": 0,
        "reclaim": 0,
        "choch": 0,
        "ote": 0,
        "entry_m5": 0,
        "entry_m1": 0,
        "entry_signal": 0,
        "fills": 0,
        "rr_fail": 0,
        "pending_cancel": 0,
    }

    asia_h = asia_l = np.nan
    locked_h = locked_l = np.nan
    was_asia = False
    state_day = None

    cj_sweep = cj_reclaim = cj_choch = cj_ote = cj_entry = False
    cj_dir = 0
    cj_ext = cj_level = np.nan
    cj_leg_hi = cj_leg_lo = cj_choch_lvl = np.nan
    cj_trail_hi = cj_trail_lo = np.nan
    m5_last_hl = m5_last_lh = np.nan
    prev_m5_c = np.nan

    n = len(m)
    for i in range(n):
        ts = m1_ts[i]
        day = fx_day_key(ts)
        lon = in_hunt_lon(ts)
        asia_r = in_range_asia(ts)

        new_day = state_day is None or day != state_day
        if new_day:
            state_day = day
            cj_sweep = cj_reclaim = cj_choch = cj_ote = cj_entry = False
            cj_dir = 0
            cj_ext = cj_level = np.nan
            cj_leg_hi = cj_leg_lo = cj_choch_lvl = np.nan
            cj_trail_hi = cj_trail_lo = np.nan
            if pending is not None and position is None:
                pending = None
                funnel["pending_cancel"] += 1

        if asia_r:
            if not was_asia:
                asia_h, asia_l = h[i], l[i]
            else:
                asia_h = max(asia_h, h[i])
                asia_l = min(asia_l, l[i])
        if was_asia and not asia_r and not np.isnan(asia_h):
            locked_h, locked_l = asia_h, asia_l
        was_asia = asia_r

        asia_hi = locked_h if not np.isnan(locked_h) else asia_h
        asia_lo = locked_l if not np.isnan(locked_l) else asia_l
        asia_mid = (
            (asia_hi + asia_lo) / 2.0
            if not np.isnan(asia_hi) and not np.isnan(asia_lo)
            else np.nan
        )

        j5 = i5[i]
        if j5 >= 1:
            k = j5 - 1
            m5_o, m5_c, m5_h, m5_l = o5[k], c5[k], h5[k], l5[k]
            m5_a = atr5[k]
            m5_bull, m5_bear = bull5[k], bear5[k]
            m5_bt, m5_bb, m5_st, m5_sb = bt5[k], bb5[k], st5[k], sb5[k]
            if not np.isnan(ph5[k]):
                m5_last_lh = ph5[k]
            if not np.isnan(pl5[k]):
                m5_last_hl = pl5[k]
            m5_closed = (not np.isnan(prev_m5_c)) and (m5_c != prev_m5_c)
        else:
            m5_o = m5_c = m5_h = m5_l = m5_a = np.nan
            m5_bull = m5_bear = False
            m5_bt = m5_bb = m5_st = m5_sb = np.nan
            m5_closed = False

        # manage position
        if position is not None:
            hit_sl = (l[i] <= position.sl) if position.direction > 0 else (h[i] >= position.sl)
            hit_tp1 = (h[i] >= position.tp1) if position.direction > 0 else (l[i] <= position.tp1)
            hit_tp2 = (h[i] >= position.tp2) if position.direction > 0 else (l[i] <= position.tp2)
            if hit_sl:
                position.exit, position.exit_time = position.sl, ts
                position.result_R, position.win, position.note = -1.0, False, "SL"
                trades.append(position)
                position = None
            elif hit_tp2:
                risk = abs(position.entry - position.sl)
                r1 = abs(position.tp1 - position.entry) / risk
                r2 = abs(position.tp2 - position.entry) / risk
                position.exit, position.exit_time = position.tp2, ts
                position.result_R = 0.5 * r1 + 0.5 * r2
                position.win, position.note = True, "TP2"
                trades.append(position)
                position = None
            elif hit_tp1 and not getattr(position, "tp1_done", False):
                position.tp1_done = True  # type: ignore[attr-defined]
                position.sl = position.entry

        if pending is not None and position is None:
            pending["age"] += 1
            expire = pending["age"] > LIMIT_EXPIRE
            breach = (pending["dir"] < 0 and c[i] > pending["fvg_top"]) or (
                pending["dir"] > 0 and c[i] < pending["fvg_bot"]
            )
            hunt_ended = (not ALLOW_FILL_OUTSIDE) and (not lon)
            if expire or breach or hunt_ended:
                pending = None
                cj_entry = False
                funnel["pending_cancel"] += 1
            else:
                filled = (pending["dir"] < 0 and h[i] >= pending["limit"] >= l[i]) or (
                    pending["dir"] > 0 and l[i] <= pending["limit"] <= h[i]
                )
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

        # Sweep during London
        if lon and not np.isnan(asia_hi) and not np.isnan(asia_lo):
            sweep_hi = h[i] > asia_hi
            sweep_lo = l[i] < asia_lo
            if sweep_hi and sweep_lo:
                if (h[i] - asia_hi) >= (asia_lo - l[i]):
                    sweep_lo = False
                else:
                    sweep_hi = False
            if sweep_hi:
                if not cj_sweep or cj_dir != -1:
                    cj_sweep, cj_dir, cj_level, cj_ext = True, -1, asia_hi, h[i]
                    cj_reclaim = cj_choch = cj_ote = cj_entry = False
                    funnel["sweep"] += 1
                else:
                    cj_ext = max(cj_ext, h[i])
            if sweep_lo:
                if not cj_sweep or cj_dir != 1:
                    cj_sweep, cj_dir, cj_level, cj_ext = True, 1, asia_lo, l[i]
                    cj_reclaim = cj_choch = cj_ote = cj_entry = False
                    funnel["sweep"] += 1
                else:
                    cj_ext = min(cj_ext, l[i])
            if cj_sweep and cj_dir < 0 and h[i] > asia_hi:
                cj_ext = max(cj_ext, h[i])
            if cj_sweep and cj_dir > 0 and l[i] < asia_lo:
                cj_ext = min(cj_ext, l[i])

            if cj_sweep and not cj_reclaim:
                if not REQUIRE_RECLAIM:
                    cj_reclaim = True
                    funnel["reclaim"] += 1
                elif cj_dir < 0 and asia_lo < c[i] < asia_hi:
                    cj_reclaim = True
                    funnel["reclaim"] += 1
                elif cj_dir > 0 and asia_lo < c[i] < asia_hi:
                    cj_reclaim = True
                    funnel["reclaim"] += 1

        # CHoCH
        if cj_sweep and cj_reclaim and not cj_choch and m5_closed:
            if not REQUIRE_CHOCH:
                cj_choch = True
                funnel["choch"] += 1
            elif cj_dir < 0 and not np.isnan(m5_last_hl) and m5_c < m5_last_hl:
                cj_choch = True
                cj_choch_lvl = m5_last_hl
                cj_leg_hi = max(m5_h, cj_choch_lvl)
                cj_leg_lo = m5_l
                cj_trail_hi, cj_trail_lo = m5_h, m5_l
                funnel["choch"] += 1
            elif cj_dir > 0 and not np.isnan(m5_last_lh) and m5_c > m5_last_lh:
                cj_choch = True
                cj_choch_lvl = m5_last_lh
                cj_leg_hi = m5_h
                cj_leg_lo = min(m5_l, cj_choch_lvl)
                cj_trail_hi, cj_trail_lo = m5_h, m5_l
                funnel["choch"] += 1

        if cj_choch and not cj_ote and m5_closed:
            if cj_dir < 0:
                cj_trail_lo = min(cj_trail_lo if not np.isnan(cj_trail_lo) else m5_l, m5_l)
                cj_leg_lo = cj_trail_lo
                cj_leg_hi = max(
                    cj_leg_hi if not np.isnan(cj_leg_hi) else cj_choch_lvl, cj_choch_lvl
                )
            else:
                cj_trail_hi = max(cj_trail_hi if not np.isnan(cj_trail_hi) else m5_h, m5_h)
                cj_leg_hi = cj_trail_hi
                cj_leg_lo = min(
                    cj_leg_lo if not np.isnan(cj_leg_lo) else cj_choch_lvl, cj_choch_lvl
                )

        if (
            cj_choch
            and not cj_ote
            and not np.isnan(cj_leg_hi)
            and not np.isnan(cj_leg_lo)
            and cj_leg_hi > cj_leg_lo
        ):
            if not REQUIRE_OTE:
                cj_ote = True
                funnel["ote"] += 1
            else:
                rng = cj_leg_hi - cj_leg_lo
                if cj_dir < 0:
                    lo, hi = cj_leg_lo + rng * OTE_LO, cj_leg_lo + rng * OTE_HI
                else:
                    lo, hi = cj_leg_hi - rng * OTE_HI, cj_leg_hi - rng * OTE_LO
                if h[i] >= min(lo, hi) and l[i] <= max(lo, hi):
                    cj_ote = True
                    funnel["ote"] += 1

        ready = cj_ote and not cj_entry and pending is None and position is None
        can_arm = lon or ALLOW_FILL_OUTSIDE
        if ready and can_arm and not np.isnan(asia_mid) and not np.isnan(cj_ext):
            body = abs(c[i] - o[i])
            disp_dn_m1 = c[i] < o[i] and not np.isnan(atr1[i]) and body >= atr1[i] * DISP_ATR_MULT
            disp_up_m1 = c[i] > o[i] and not np.isnan(atr1[i]) and body >= atr1[i] * DISP_ATR_MULT
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
            t1, t2 = asia_mid, (asia_lo if cj_dir < 0 else asia_hi)
            armed = False
            if ENABLE_M5 and m5_closed:
                if cj_dir < 0 and disp_dn_m5 and m5_bear:
                    lim, sl = m5_st, cj_ext + SL_PIPS * PIP
                    if rr_ok(lim, sl, t1, -1, CLASSIC_MIN_RR):
                        pending = {
                            "dir": -1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": m5_st,
                            "fvg_bot": m5_sb,
                            "age": 0,
                            "tag": "CJ_M5_Short",
                        }
                        armed = True
                        funnel["entry_m5"] += 1
                    else:
                        funnel["rr_fail"] += 1
                elif cj_dir > 0 and disp_up_m5 and m5_bull:
                    lim, sl = m5_bb, cj_ext - SL_PIPS * PIP
                    if rr_ok(lim, sl, t1, 1, CLASSIC_MIN_RR):
                        pending = {
                            "dir": 1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": m5_bt,
                            "fvg_bot": m5_bb,
                            "age": 0,
                            "tag": "CJ_M5_Long",
                        }
                        armed = True
                        funnel["entry_m5"] += 1
                    else:
                        funnel["rr_fail"] += 1
            allow_m1 = ENABLE_M1 and (not M5_PRIORITY or not ENABLE_M5 or not armed)
            if allow_m1 and not armed:
                if cj_dir < 0 and disp_dn_m1 and bear1[i]:
                    lim, sl = s1t[i], cj_ext + SL_PIPS * PIP
                    if rr_ok(lim, sl, t1, -1, CLASSIC_MIN_RR):
                        pending = {
                            "dir": -1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": s1t[i],
                            "fvg_bot": s1b[i],
                            "age": 0,
                            "tag": "CJ_M1_Short",
                        }
                        armed = True
                        funnel["entry_m1"] += 1
                    else:
                        funnel["rr_fail"] += 1
                elif cj_dir > 0 and disp_up_m1 and bull1[i]:
                    lim, sl = b1b[i], cj_ext - SL_PIPS * PIP
                    if rr_ok(lim, sl, t1, 1, CLASSIC_MIN_RR):
                        pending = {
                            "dir": 1,
                            "limit": lim,
                            "sl": sl,
                            "tp1": t1,
                            "tp2": t2,
                            "fvg_top": b1t[i],
                            "fvg_bot": b1b[i],
                            "age": 0,
                            "tag": "CJ_M1_Long",
                        }
                        armed = True
                        funnel["entry_m1"] += 1
                    else:
                        funnel["rr_fail"] += 1
            if armed:
                cj_entry = True
                funnel["entry_signal"] += 1

        if j5 >= 1:
            prev_m5_c = c5[j5 - 1]

    if position is not None:
        position.exit, position.exit_time = c[-1], m1_ts[-1]
        risk = abs(position.entry - position.sl)
        position.result_R = (position.exit - position.entry) / risk * position.direction
        position.win = position.result_R > 0
        position.note = "EOD"
        trades.append(position)

    wins = [t for t in trades if t.win]
    losses = [t for t in trades if t.win is False]
    n_tr = len(trades)
    by_tag: dict[str, int] = {}
    for t in trades:
        by_tag[t.tag] = by_tag.get(t.tag, 0) + 1
    return {
        "symbol": "EURUSD",
        "strategy": "Classic Judas Asia→London",
        "period_start": str(m1_ts[0]),
        "period_end": str(m1_ts[-1]),
        "bars_m1": int(n),
        "timezone": "America/New_York",
        "params": {
            "disp_atr_mult": DISP_ATR_MULT,
            "classic_min_rr": CLASSIC_MIN_RR,
            "require_choch": REQUIRE_CHOCH,
            "require_ote": REQUIRE_OTE,
            "require_reclaim": REQUIRE_RECLAIM,
        },
        "trades": n_tr,
        "wins": len(wins),
        "losses": len(losses),
        "winrate_pct": round(len(wins) / n_tr * 100, 2) if n_tr else 0.0,
        "avg_R": round(float(np.mean([t.result_R for t in trades])), 3) if trades else 0.0,
        "sum_R": round(float(np.sum([t.result_R for t in trades])), 3) if trades else 0.0,
        "by_tag": by_tag,
        "funnel": funnel,
        "trade_log": [
            {
                "dir": "LONG" if t.direction > 0 else "SHORT",
                "tag": t.tag,
                "entry_time": str(t.entry_time),
                "entry": round(t.entry, 5),
                "sl": round(t.sl, 5),
                "tp1": round(t.tp1, 5),
                "tp2": round(t.tp2, 5),
                "exit_time": str(t.exit_time),
                "exit": round(t.exit, 5) if t.exit is not None else None,
                "R": round(t.result_R, 3) if t.result_R is not None else None,
                "win": t.win,
                "note": t.note,
            }
            for t in trades
        ],
        "notes": [
            "Classic Judas Mode B — Asia mid TP1, opposite Asia TP2, SL at sweep extreme.",
            "Offline approximate vs TradingView.",
        ],
    }


def main():
    print("Loading EURUSD ...")
    eur = load_pair("EURUSD")
    start, end = "2026-06-19", "2026-07-18"
    global DISP_ATR_MULT, CLASSIC_MIN_RR

    res_default = run_classic(eur, start, end)
    DISP_ATR_MULT = 1.0
    res_loose = run_classic(eur, start, end)
    DISP_ATR_MULT = 1.5

    out = {"default_classic": res_default, "sensitivity_disp1_rr2": res_loose}
    OUT.write_text(json.dumps(out, indent=2))

    for label, res in [("DEFAULT classic", res_default), ("SENS disp1.0", res_loose)]:
        print(f"\n=== {label} ===")
        print(
            json.dumps(
                {k: res[k] for k in res if k not in ("trade_log", "notes")},
                indent=2,
            )
        )
        for t in res["trade_log"]:
            print(
                f"  {t['tag']:12} {t['dir']:5} {t['entry_time']} → {t['exit_time']}  "
                f"R={t['R']}  {t['note']}"
            )
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
