#!/usr/bin/env python3
"""Offline ~1-month backtest of ICT 2022 Silver Reversal on EURUSD M1.

Data: HistData ASCII M1 (EST no-DST) + Yahoo Finance recent M1.
Correlated SMT: GBPUSD.
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"
OUT = Path(__file__).parent / "backtest_ict22_eurusd_results.json"

# ── parameters (match Pine defaults) ─────────────────────────────────────────
PIVOT_L = PIVOT_R = 5
SMT_LB = 20
DISP_ATR_MULT = 1.5
ATR_LEN = 10
OTE_LO, OTE_HI = 0.618, 0.705
MIN_RR = 3.0
SL_PIPS = 2.0
PIP = 0.0001
TP1_PCT = 0.50
LIMIT_EXPIRE = 30
REQUIRE_SMT = True
REQUIRE_SETUP_KZ = True   # sweep must start in KZ
REQUIRE_ARM_IN_KZ = False  # Disp+FVG arm can be outside KZ (Gemini #1)
ALLOW_FILL_OUTSIDE_KZ = True


def load_histdata_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep=";",
        header=None,
        names=["dt", "open", "high", "low", "close", "volume"],
    )
    # HistData: EST without DST → treat as fixed UTC-5
    ts = pd.to_datetime(df["dt"], format="%Y%m%d %H%M%S")
    df["timestamp"] = ts.dt.tz_localize("UTC").dt.tz_convert(None)  # naive
    # Better: localize as Etc/GMT+5 (POSIX sign flip) = UTC-5
    df["timestamp"] = ts.dt.tz_localize("Etc/GMT+5")
    return df[["timestamp", "open", "high", "low", "close"]].astype(
        {"open": float, "high": float, "low": float, "close": float}
    )


def load_yf_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert("Etc/GMT+5")
    return df[["timestamp", "open", "high", "low", "close"]].astype(
        {"open": float, "high": float, "low": float, "close": float}
    )


def load_pair(prefix: str) -> pd.DataFrame:
    frames = []
    for p in sorted(DATA.glob(f"DAT_ASCII_{prefix}_M1_*.csv")):
        frames.append(load_histdata_csv(p))
    yf = DATA / f"{prefix}_yf_1m.csv"
    if yf.exists():
        frames.append(load_yf_csv(yf))
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    return df


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = df.set_index("timestamp")
    o = x["open"].resample(rule).first()
    h = x["high"].resample(rule).max()
    l = x["low"].resample(rule).min()
    c = x["close"].resample(rule).last()
    out = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    return out


def pivots(high: np.ndarray, low: np.ndarray, left: int, right: int):
    n = len(high)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(left, n - right):
        w_h = high[i - left : i + right + 1]
        w_l = low[i - left : i + right + 1]
        if high[i] == np.max(w_h) and np.sum(w_h == high[i]) == 1:
            ph[i + right] = high[i]  # confirm on bar i+right
        if low[i] == np.min(w_l) and np.sum(w_l == low[i]) == 1:
            pl[i + right] = low[i]
    return ph, pl


def detect_fvg(o, h, l, c, thr=0.0):
    n = len(c)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    b_top = np.full(n, np.nan)
    b_bot = np.full(n, np.nan)
    s_top = np.full(n, np.nan)
    s_bot = np.full(n, np.nan)
    for i in range(2, n):
        if l[i] > h[i - 2] and c[i - 1] > h[i - 2] and (l[i] - h[i - 2]) / h[i - 2] > thr:
            bull[i] = True
            b_top[i] = l[i]
            b_bot[i] = h[i - 2]
        if h[i] < l[i - 2] and c[i - 1] < l[i - 2] and (l[i - 2] - h[i]) / h[i] > thr:
            bear[i] = True
            s_top[i] = l[i - 2]
            s_bot[i] = h[i]
    return bull, bear, b_top, b_bot, s_top, s_bot


def atr(h, l, c, length=10):
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    out = np.full(len(c), np.nan)
    if len(c) < length:
        return out
    out[length - 1] = np.mean(tr[:length])
    for i in range(length, len(c)):
        out[i] = (out[i - 1] * (length - 1) + tr[i]) / length
    return out


def in_kz(ts: pd.Timestamp) -> tuple[bool, bool, bool]:
    # ts in Etc/GMT+5 (=UTC-5 fixed)
    hm = ts.hour * 100 + ts.minute
    lon = 200 <= hm < 500
    ny = 700 <= hm < 1000
    asia = hm >= 2000 or hm < 0  # 20:00-00:00
    asia = hm >= 2000
    return lon, ny, asia


def fx_day_key(ts: pd.Timestamp) -> int:
    # roll at 17:00
    adj = ts - pd.Timedelta(hours=17)
    return int(adj.strftime("%Y%m%d"))


@dataclass
class Trade:
    direction: int
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp1: float
    tp2: float
    exit_time: pd.Timestamp | None = None
    exit: float | None = None
    result_R: float | None = None
    win: bool | None = None
    note: str = ""


def run_backtest(eur: pd.DataFrame, gbp: pd.DataFrame, start: str, end: str) -> dict:
    eur = eur[(eur["timestamp"] >= start) & (eur["timestamp"] <= end)].reset_index(drop=True)
    gbp = gbp[(gbp["timestamp"] >= start) & (gbp["timestamp"] <= end)].reset_index(drop=True)

    # Align GBP onto EUR timestamps (forward-fill)
    g = gbp.set_index("timestamp")[["open", "high", "low", "close"]].rename(
        columns=lambda c: "g_" + c
    )
    e = eur.set_index("timestamp")
    m = e.join(g, how="left").ffill().dropna()
    m = m.reset_index()

    # HTF frames from full m
    h1 = resample_ohlc(m, "1h")
    h4 = resample_ohlc(m, "4h")
    m5 = resample_ohlc(m, "5min")

    # Precompute HTF features
    def prep_htf(htf: pd.DataFrame):
        h = htf["high"].to_numpy()
        l = htf["low"].to_numpy()
        c = htf["close"].to_numpy()
        o = htf["open"].to_numpy()
        ph, pl = pivots(h, l, PIVOT_L, PIVOT_R)
        bull, bear, bt, bb, st, sb = detect_fvg(o, h, l, c)
        return {
            "index": htf.index,
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
        }

    H1 = prep_htf(h1)
    H4 = prep_htf(h4)
    M5 = prep_htf(m5)

    # Map M1 bar -> last completed HTF bar index
    def map_htf(ts_index: pd.DatetimeIndex, htf_index: pd.DatetimeIndex):
        # for each ts, position of last htf bar that started <= ts and is completed
        pos = htf_index.get_indexer(ts_index, method="ffill")
        return pos

    m1_ts = pd.DatetimeIndex(m["timestamp"])
    i1 = map_htf(m1_ts, H1["index"])
    i4 = map_htf(m1_ts, H4["index"])
    i5 = map_htf(m1_ts, M5["index"])

    o = m["open"].to_numpy()
    h = m["high"].to_numpy()
    l = m["low"].to_numpy()
    c = m["close"].to_numpy()
    gh = m["g_high"].to_numpy()
    gl = m["g_low"].to_numpy()
    atr1 = atr(h, l, c, ATR_LEN)
    bull1, bear1, b1t, b1b, s1t, s1b = detect_fvg(o, h, l, c)

    # M1 swings for SL
    m1_ph, m1_pl = pivots(h, l, 3, 2)

    trades: list[Trade] = []
    pending = None  # dict
    position = None
    funnel = {
        "sweep": 0,
        "smt": 0,
        "fvg": 0,
        "choch": 0,
        "ote": 0,
        "entry_signal": 0,
        "fills": 0,
        "disp_in_ote_kz": 0,
        "rr_fail": 0,
    }

    step_sweep = step_smt = step_fvg = step_choch = step_ote = step_entry = False
    sweep_dir = 0
    sweep_tf = ""
    sweep_level = np.nan
    state_day = None
    h1_sh = h1_sl = h4_sh = h4_sl = np.nan
    last_h1_bear = last_h1_bull = last_h4_bear = last_h4_bull = None  # (top,bot)
    m5_last_hl = m5_last_lh = np.nan
    m5_leg_hi = m5_leg_lo = np.nan
    m5_choch_lvl = np.nan
    asia_hi = asia_lo = lon_hi = lon_lo = np.nan
    asia_day = lon_day = None
    pd_high = pd_low = np.nan
    cur_day_hi = cur_day_lo = np.nan
    last_m1_sh = last_m1_sl = np.nan
    prev_h1_c = prev_h4_c = prev_m5_c = np.nan

    n = len(m)
    for i in range(n):
        ts = m1_ts[i]
        day = fx_day_key(ts)
        lon_kz, ny_kz, asia = in_kz(ts)
        in_entry = lon_kz or ny_kz
        london_done = (ts.hour * 100 + ts.minute) >= 500

        # day reset
        if state_day is None or day != state_day:
            if state_day is not None and not np.isnan(cur_day_hi):
                pd_high, pd_low = cur_day_hi, cur_day_lo
            state_day = day
            step_sweep = step_smt = step_fvg = step_choch = step_ote = step_entry = False
            sweep_dir = 0
            sweep_tf = ""
            sweep_level = np.nan
            m5_leg_hi = m5_leg_lo = m5_choch_lvl = np.nan
            pending = None
            cur_day_hi, cur_day_lo = h[i], l[i]
        else:
            cur_day_hi = max(cur_day_hi, h[i])
            cur_day_lo = min(cur_day_lo, l[i])

        if asia:
            if asia_day != day:
                asia_day = day
                asia_hi, asia_lo = h[i], l[i]
            else:
                asia_hi = max(asia_hi, h[i])
                asia_lo = min(asia_lo, l[i])
        if lon_kz:
            if lon_day != day:
                lon_day = day
                lon_hi, lon_lo = h[i], l[i]
            else:
                lon_hi = max(lon_hi, h[i])
                lon_lo = min(lon_lo, l[i])

        # update HTF swings / FVGs from completed bars (use previous completed = idx-1 if forming)
        j1 = i1[i]
        j4 = i4[i]
        j5 = i5[i]
        if j1 >= 1:
            k = j1 - 1  # last completed H1
            if not np.isnan(H1["ph"][k]):
                h1_sh = H1["ph"][k]
            if not np.isnan(H1["pl"][k]):
                h1_sl = H1["pl"][k]
            if H1["bear"][k]:
                last_h1_bear = (H1["st"][k], H1["sb"][k])
            if H1["bull"][k]:
                last_h1_bull = (H1["bt"][k], H1["bb"][k])
            h1_c = H1["close"][k]
            h1_h = H1["high"][k]
            h1_l = H1["low"][k]
            h1_closed = (not np.isnan(prev_h1_c)) and (h1_c != prev_h1_c)
        else:
            h1_c = h1_h = h1_l = np.nan
            h1_closed = False

        if j4 >= 1:
            k = j4 - 1
            if not np.isnan(H4["ph"][k]):
                h4_sh = H4["ph"][k]
            if not np.isnan(H4["pl"][k]):
                h4_sl = H4["pl"][k]
            if H4["bear"][k]:
                last_h4_bear = (H4["st"][k], H4["sb"][k])
            if H4["bull"][k]:
                last_h4_bull = (H4["bt"][k], H4["bb"][k])
            h4_c = H4["close"][k]
            h4_h = H4["high"][k]
            h4_l = H4["low"][k]
            h4_closed = (not np.isnan(prev_h4_c)) and (h4_c != prev_h4_c)
        else:
            h4_c = h4_h = h4_l = np.nan
            h4_closed = False

        if j5 >= 1:
            k = j5 - 1
            if not np.isnan(M5["ph"][k]):
                m5_last_lh = M5["ph"][k]
            if not np.isnan(M5["pl"][k]):
                m5_last_hl = M5["pl"][k]
            m5_c = M5["close"][k]
            m5_h = M5["high"][k]
            m5_l = M5["low"][k]
            m5_closed = (not np.isnan(prev_m5_c)) and (m5_c != prev_m5_c)
        else:
            m5_c = m5_h = m5_l = np.nan
            m5_closed = False

        # manage open position
        if position is not None:
            hit_sl = (l[i] <= position.sl) if position.direction > 0 else (h[i] >= position.sl)
            hit_tp1 = (h[i] >= position.tp1) if position.direction > 0 else (l[i] <= position.tp1)
            hit_tp2 = (h[i] >= position.tp2) if position.direction > 0 else (l[i] <= position.tp2)
            if hit_sl:
                risk = abs(position.entry - position.sl)
                position.exit = position.sl
                position.exit_time = ts
                position.result_R = -1.0
                position.win = False
                position.note = "SL"
                trades.append(position)
                position = None
            elif hit_tp2:
                risk = abs(position.entry - position.sl)
                # approx: 50% at TP1 (3R+) + 50% at TP2
                r1 = abs(position.tp1 - position.entry) / risk
                r2 = abs(position.tp2 - position.entry) / risk
                position.exit = position.tp2
                position.exit_time = ts
                position.result_R = 0.5 * r1 + 0.5 * r2
                position.win = True
                position.note = "TP2"
                trades.append(position)
                position = None
            elif hit_tp1 and "tp1_done" not in position.__dict__:
                position.__dict__["tp1_done"] = True
                position.sl = position.entry  # BE
            # continue

        # fill pending limit
        if pending is not None and position is None:
            pending["age"] += 1
            if pending["age"] > LIMIT_EXPIRE:
                pending = None
                step_entry = False
            else:
                filled = False
                if pending["dir"] < 0 and h[i] >= pending["limit"] and l[i] <= pending["limit"]:
                    filled = True
                if pending["dir"] > 0 and l[i] <= pending["limit"] and h[i] >= pending["limit"]:
                    filled = True
                # invalidate
                if pending["dir"] < 0 and c[i] > pending["fvg_top"]:
                    pending = None
                    step_entry = False
                elif pending["dir"] > 0 and c[i] < pending["fvg_bot"]:
                    pending = None
                    step_entry = False
                elif filled:
                    position = Trade(
                        direction=pending["dir"],
                        entry_time=ts,
                        entry=pending["limit"],
                        sl=pending["sl"],
                        tp1=pending["tp1"],
                        tp2=pending["tp2"],
                    )
                    funnel["fills"] += 1
                    pending = None

        # Step 1 sweep (optionally only inside Killzone)
        if not step_sweep and j1 >= 1 and (not REQUIRE_SETUP_KZ or in_entry):
            bear_h1 = (not np.isnan(h1_sh)) and h1_h > h1_sh and h1_c < h1_sh
            bull_h1 = (not np.isnan(h1_sl)) and h1_l < h1_sl and h1_c > h1_sl
            bear_h4 = (not np.isnan(h4_sh)) and h4_h > h4_sh and h4_c < h4_sh
            bull_h4 = (not np.isnan(h4_sl)) and h4_l < h4_sl and h4_c > h4_sl
            if (bear_h4 and h4_closed) or (bear_h1 and h1_closed):
                step_sweep = True
                sweep_dir = -1
                h4s = bear_h4 and h4_closed
                h1s = bear_h1 and h1_closed
                sweep_tf = "H1+H4" if h4s and h1s else ("H4" if h4s else "H1")
                sweep_level = h4_sh if h4s else h1_sh
                funnel["sweep"] += 1
            elif (bull_h4 and h4_closed) or (bull_h1 and h1_closed):
                step_sweep = True
                sweep_dir = 1
                h4s = bull_h4 and h4_closed
                h1s = bull_h1 and h1_closed
                sweep_tf = "H1+H4" if h4s and h1s else ("H4" if h4s else "H1")
                sweep_level = h4_sl if h4s else h1_sl
                funnel["sweep"] += 1

        # Step 2 SMT (relative range vs lookback on H1 confirmed)
        if step_sweep and not step_smt and j1 >= SMT_LB + 2:
            k = j1 - 1
            p_hiN = np.max(H1["high"][max(0, k - SMT_LB + 1) : k + 1])
            p_hiP = np.max(H1["high"][max(0, k - SMT_LB) : k])
            p_loN = np.min(H1["low"][max(0, k - SMT_LB + 1) : k + 1])
            p_loP = np.min(H1["low"][max(0, k - SMT_LB) : k])
            # GBP proxy on same M1 window mapped roughly via last SMT_LB*60 minutes
            i0 = max(0, i - SMT_LB * 60)
            c_hiN = np.max(gh[i0 : i + 1])
            c_hiP = np.max(gh[i0:i]) if i > i0 else c_hiN
            c_loN = np.min(gl[i0 : i + 1])
            c_loP = np.min(gl[i0:i]) if i > i0 else c_loN
            smt_bear = p_hiN > p_hiP and not (c_hiN > c_hiP)
            smt_bull = p_loN < p_loP and not (c_loN < c_loP)
            if not REQUIRE_SMT:
                step_smt = True
            elif sweep_dir < 0:
                step_smt = smt_bear
            else:
                step_smt = smt_bull
            if step_smt:
                funnel["smt"] += 1

        # Step 3 FVG fill
        if step_sweep and step_smt and not step_fvg:
            allow_h4 = "H4" in sweep_tf
            if sweep_dir < 0:
                ok = False
                if last_h1_bear and l[i] <= max(last_h1_bear) and h[i] >= min(last_h1_bear):
                    ok = True
                if allow_h4 and last_h4_bear and l[i] <= max(last_h4_bear) and h[i] >= min(last_h4_bear):
                    ok = True
                step_fvg = ok
            else:
                ok = False
                if last_h1_bull and l[i] <= max(last_h1_bull) and h[i] >= min(last_h1_bull):
                    ok = True
                if allow_h4 and last_h4_bull and l[i] <= max(last_h4_bull) and h[i] >= min(last_h4_bull):
                    ok = True
                step_fvg = ok
            if step_fvg:
                funnel["fvg"] += 1

        # Step 4 M5 CHoCH
        if step_fvg and not step_choch and m5_closed:
            if sweep_dir < 0 and not np.isnan(m5_last_hl) and m5_c < m5_last_hl:
                step_choch = True
                m5_choch_lvl = m5_last_hl
                m5_leg_hi = max(m5_h, m5_choch_lvl)
                m5_leg_lo = m5_l
                funnel["choch"] += 1
            if sweep_dir > 0 and not np.isnan(m5_last_lh) and m5_c > m5_last_lh:
                step_choch = True
                m5_choch_lvl = m5_last_lh
                m5_leg_hi = m5_h
                m5_leg_lo = min(m5_l, m5_choch_lvl)
                funnel["choch"] += 1

        if step_choch and not step_ote and m5_closed:
            if sweep_dir < 0:
                m5_leg_lo = min(m5_leg_lo, m5_l)
                m5_leg_hi = max(m5_leg_hi, m5_choch_lvl)
            else:
                m5_leg_hi = max(m5_leg_hi, m5_h)
                m5_leg_lo = min(m5_leg_lo, m5_choch_lvl)

        # Step 5 OTE
        if step_choch and not step_ote and m5_leg_hi > m5_leg_lo:
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

        # Step 6 entry — arm without forcing current bar inside KZ (unless REQUIRE_ARM_IN_KZ)
        can_arm = (not REQUIRE_ARM_IN_KZ) or in_entry
        if (
            step_ote
            and not step_entry
            and can_arm
            and position is None
            and pending is None
            and not np.isnan(atr1[i])
        ):
            body = abs(c[i] - o[i])
            disp_dn = c[i] < o[i] and body >= atr1[i] * DISP_ATR_MULT
            disp_up = c[i] > o[i] and body >= atr1[i] * DISP_ATR_MULT

            def tp1(dir_):
                if london_done and not np.isnan(lon_hi):
                    return lon_lo if dir_ < 0 else lon_hi
                if not np.isnan(asia_hi):
                    return asia_lo if dir_ < 0 else asia_hi
                if not np.isnan(m5_last_hl):
                    return m5_last_hl if dir_ < 0 else m5_last_lh
                return np.nan

            def tp2(dir_):
                return pd_low if dir_ < 0 else pd_high

            if (sweep_dir < 0 and disp_dn) or (sweep_dir > 0 and disp_up):
                funnel["disp_in_ote_kz"] += 1

            if sweep_dir < 0 and disp_dn and bear1[i]:
                lim = s1t[i]
                sl = (last_m1_sh if not np.isnan(last_m1_sh) else h[i]) + SL_PIPS * PIP
                t1, t2 = tp1(-1), tp2(-1)
                risk = abs(lim - sl)
                rr_ok = risk > 0 and not np.isnan(t1) and not np.isnan(t2) and t1 < lim and (lim - t1) / risk >= MIN_RR
                if not rr_ok:
                    funnel["rr_fail"] += 1
                else:
                    pending = {
                        "dir": -1,
                        "limit": lim,
                        "sl": sl,
                        "tp1": t1,
                        "tp2": t2,
                        "fvg_top": s1t[i],
                        "fvg_bot": s1b[i],
                        "age": 0,
                    }
                    step_entry = True
                    funnel["entry_signal"] += 1
            elif sweep_dir > 0 and disp_up and bull1[i]:
                lim = b1b[i]
                sl = (last_m1_sl if not np.isnan(last_m1_sl) else l[i]) - SL_PIPS * PIP
                t1, t2 = tp1(1), tp2(1)
                risk = abs(lim - sl)
                rr_ok = risk > 0 and not np.isnan(t1) and not np.isnan(t2) and t1 > lim and (t1 - lim) / risk >= MIN_RR
                if not rr_ok:
                    funnel["rr_fail"] += 1
                else:
                    pending = {
                        "dir": 1,
                        "limit": lim,
                        "sl": sl,
                        "tp1": t1,
                        "tp2": t2,
                        "fvg_top": b1t[i],
                        "fvg_bot": b1b[i],
                        "age": 0,
                    }
                    step_entry = True
                    funnel["entry_signal"] += 1

        if j1 >= 1:
            prev_h1_c = H1["close"][j1 - 1]
        if j4 >= 1:
            prev_h4_c = H4["close"][j4 - 1]
        if j5 >= 1:
            prev_m5_c = M5["close"][j5 - 1]

    # close open at end
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

    return {
        "symbol": "EURUSD",
        "corr": "GBPUSD",
        "period_start": str(m1_ts[0]),
        "period_end": str(m1_ts[-1]),
        "bars_m1": int(n),
        "trades": n_tr,
        "wins": len(wins),
        "losses": len(losses),
        "winrate_pct": round(wr, 2),
        "avg_R": round(avg_R, 3),
        "sum_R": round(sum_R, 3),
        "trade_log": [
            {
                "dir": "LONG" if t.direction > 0 else "SHORT",
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
            "HistData M1 times treated as UTC-5 fixed (EST no DST), matching LuxAlgo-style session math.",
            "July gap filled with Yahoo Finance M1 where available.",
            "Offline port of Pine ICT22 logic — approximate vs TradingView ticks/broker feed.",
        ],
    }


def main():
    print("Loading EURUSD / GBPUSD ...")
    eur = load_pair("EURUSD")
    gbp = load_pair("GBPUSD")
    print(f"EUR {len(eur)} {eur['timestamp'].min()} → {eur['timestamp'].max()}")
    print(f"GBP {len(gbp)} {gbp['timestamp'].min()} → {gbp['timestamp'].max()}")

    # Last ~month relative to Jul 19 2026: Jun 19 → Jul 17 (available)
    start = "2026-06-19"
    end = "2026-07-18"
    print(f"Backtest window {start} → {end}")
    res = run_backtest(eur, gbp, start, end)
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: res[k] for k in res if k != "trade_log"}, indent=2))
    print(f"\nWrote {OUT}")
    if res["trade_log"]:
        print("\nTrades:")
        for t in res["trade_log"]:
            print(
                f"  {t['dir']:5} {t['entry_time']} → {t['exit_time']}  R={t['R']}  {t['note']}  win={t['win']}"
            )


if __name__ == "__main__":
    main()
