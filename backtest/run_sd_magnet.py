#!/usr/bin/env python3
"""
Backtest Strong SD Magnet (Supply/Demand + Magnet Pull) signals.

Signal modes:
  1) magnet   — on retest of strong zone, trade toward opposite zone (native)
  2) bounce   — first touch of strong fresh/tested zone (bounce away from zone)
  3) both     — magnet preferred, else bounce

Exits:
  - native: SL beyond source zone, TP at opposite zone mid (or ATR fallback)
  - atr / pct / pip: fixed risk rules
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)


def atr(df: pd.DataFrame, length: int = 20) -> pd.Series:
    prev = df["Close"].shift(1)
    tr = pd.concat(
        [
            (df["High"] - df["Low"]).abs(),
            (df["High"] - prev).abs(),
            (df["Low"] - prev).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


@dataclass
class Zone:
    kind: str  # Supply / Demand
    top: float
    bot: float
    mid: float
    born: int
    sess_id: int
    touches: int = 0
    broken: bool = False
    last_touch: int = 0
    in_prev: bool = False
    imp_f: float = 0.0
    vol_f: float = 0.0
    wick_f: float = 0.0
    score: float = 0.0


@dataclass
class Trade:
    symbol: str
    tf: str
    mode: str
    exit_mode: str
    direction: int
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    sl: float
    tp: float
    outcome: str
    bars_held: int
    score: float
    signal: str


def score_zone(z: Zone, n: int, touch_norm=3.0, w_imp=0.35, w_vol=0.20, w_wick=0.20, w_fresh=0.25,
               use_decay=True, decay_bars=600, decay_floor=0.6) -> float:
    fresh = max(0.0, 1.0 - z.touches / max(touch_norm, 1.0))
    wsum = w_imp + w_vol + w_wick + w_fresh
    raw = (z.imp_f * w_imp + z.vol_f * w_vol + z.wick_f * w_wick + fresh * w_fresh) / wsum if wsum else 0
    idle = n - z.last_touch
    age = 1.0 if not use_decay else max(1.0 - (1.0 - decay_floor) * min(idle / max(decay_bars, 1), 1.0), decay_floor)
    return float(min(max(raw * 10.0 * age, 0.0), 10.0))


def detect_and_trade(
    df: pd.DataFrame,
    symbol: str,
    tf: str,
    signal_mode: str = "magnet",
    exit_mode: str = "native",
    swing_len: int = 12,
    min_zone_dist: int = 15,
    uni_height: float = 0.5,
    min_swing_atr: float = 0.3,
    impulse_norm: float = 3.0,
    magnet_thr: float = 6.5,
    mag_min_touch: int = 1,
    mag_target_thr: float = 5.0,
    mag_max_reach: float = 25.0,
    bounce_thr: float = 6.5,
    inv_close: bool = True,
    sl_atr: float = 1.5,
    tp_atr: float = 2.0,
    sl_pct: float = 3.0,
    tp_pct: float = 5.0,
    sl_pips: float = 5.0,
    tp_pips: float = 5.0,
    pip_size: float = 0.0001,
    max_hold: int = 500,
) -> list[Trade]:
    o = df["Open"].values
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values
    v = df["Volume"].values.astype(float)
    idx = df.index
    nbar = len(df)
    a = atr(df, 20).values
    vol_base = pd.Series(v).rolling(20, min_periods=1).mean().values

    # session id by calendar day
    days = pd.Series(idx).dt.floor("D")
    sess_ids = (days != days.shift(1)).cumsum().values

    zones: list[Zone] = []
    last_sup = -10**9
    last_dem = -10**9
    trades: list[Trade] = []
    in_trade = False
    t_dir = 0
    t_entry = t_sl = t_tp = 0.0
    t_i = 0
    t_score = 0.0
    t_sig = ""

    def sl_tp(entry: float, direction: int, src: Zone | None, tgt_mid: float | None, i: int):
        aa = a[i] if not np.isnan(a[i]) and a[i] > 0 else abs(entry) * 0.002
        if exit_mode == "native" and src is not None:
            if direction == 1:  # long from demand
                sl = src.bot - aa * 0.1
                tp = tgt_mid if tgt_mid is not None else entry + aa * tp_atr
            else:
                sl = src.top + aa * 0.1
                tp = tgt_mid if tgt_mid is not None else entry - aa * tp_atr
            return sl, tp
        if exit_mode == "pct":
            d_sl, d_tp = entry * sl_pct / 100, entry * tp_pct / 100
        elif exit_mode == "pip":
            d_sl, d_tp = sl_pips * pip_size, tp_pips * pip_size
        else:
            d_sl, d_tp = aa * sl_atr, aa * tp_atr
        if direction == 1:
            return entry - d_sl, entry + d_tp
        return entry + d_sl, entry - d_tp

    def try_open(i: int, direction: int, src: Zone, tgt_mid: float | None, sig: str):
        nonlocal in_trade, t_dir, t_entry, t_sl, t_tp, t_i, t_score, t_sig
        if in_trade:
            return
        entry = float(c[i])
        sl, tp = sl_tp(entry, direction, src, tgt_mid, i)
        # sanity: TP must be on correct side
        if direction == 1 and tp <= entry:
            tp = entry + (a[i] if a[i] == a[i] else entry * 0.002) * tp_atr
        if direction == -1 and tp >= entry:
            tp = entry - (a[i] if a[i] == a[i] else entry * 0.002) * tp_atr
        in_trade = True
        t_dir, t_entry, t_sl, t_tp, t_i = direction, entry, sl, tp, i
        t_score, t_sig = src.score, sig

    def close_trade(j: int, outcome: str, px: float):
        nonlocal in_trade
        trades.append(
            Trade(
                symbol=symbol,
                tf=tf,
                mode=signal_mode,
                exit_mode=exit_mode,
                direction=t_dir,
                entry_time=str(idx[t_i]),
                exit_time=str(idx[j]),
                entry=t_entry,
                exit=px,
                sl=t_sl,
                tp=t_tp,
                outcome=outcome,
                bars_held=j - t_i,
                score=t_score,
                signal=t_sig,
            )
        )
        in_trade = False

    for i in range(swing_len * 2, nbar):
        aa = a[i]
        if np.isnan(aa) or aa <= 0:
            # manage open trade only
            if in_trade and i > t_i:
                if t_dir == 1:
                    hit_sl, hit_tp = l[i] <= t_sl, h[i] >= t_tp
                else:
                    hit_sl, hit_tp = h[i] >= t_sl, l[i] <= t_tp
                if hit_sl and hit_tp:
                    close_trade(i, "loss", t_sl)
                elif hit_sl:
                    close_trade(i, "loss", t_sl)
                elif hit_tp:
                    close_trade(i, "win", t_tp)
                elif i - t_i >= max_hold:
                    close_trade(i, "timeout", float(c[i]))
            continue

        sid = int(sess_ids[i])
        # pivot confirmation at i (center at i-swing_len)
        center = i - swing_len
        # pivot high: high[center] == max of window
        w_hi = h[center - swing_len : center + swing_len + 1]
        w_lo = l[center - swing_len : center + swing_len + 1]
        is_ph = h[center] >= np.max(w_hi)
        is_pl = l[center] <= np.min(w_lo)
        bar_range = h[center] - l[center]

        if is_ph and (i - last_sup) >= min_zone_dist and bar_range >= aa * min_swing_atr:
            lo_swing = np.min(l[center - swing_len + 1 : center + 1]) if swing_len > 0 else l[center]
            dep = h[center] - lo_swing
            imp_f = min(max(dep, 0.0) / max(aa * impulse_norm, 1e-9), 1.0)
            vol_f = min(v[center] / vol_base[center], 1.0) if vol_base[center] > 0 else 0.0
            rng = max(bar_range, 1e-9)
            wick_f = min(max(h[center] - max(o[center], c[center]), 0.0) / rng, 1.0)
            level = h[center]
            hh = aa * uni_height
            z = Zone("Supply", level + hh / 2, level - hh / 2, level, center, sid,
                     last_touch=center, imp_f=imp_f, vol_f=vol_f, wick_f=wick_f)
            z.score = score_zone(z, i)
            zones.append(z)
            last_sup = i

        if is_pl and (i - last_dem) >= min_zone_dist and bar_range >= aa * min_swing_atr:
            hi_swing = np.max(h[center - swing_len + 1 : center + 1]) if swing_len > 0 else h[center]
            dep = hi_swing - l[center]
            imp_f = min(max(dep, 0.0) / max(aa * impulse_norm, 1e-9), 1.0)
            vol_f = min(v[center] / vol_base[center], 1.0) if vol_base[center] > 0 else 0.0
            rng = max(bar_range, 1e-9)
            wick_f = min(max(min(o[center], c[center]) - l[center], 0.0) / rng, 1.0)
            level = l[center]
            hh = aa * uni_height
            z = Zone("Demand", level + hh / 2, level - hh / 2, level, center, sid,
                     last_touch=center, imp_f=imp_f, vol_f=vol_f, wick_f=wick_f)
            z.score = score_zone(z, i)
            zones.append(z)
            last_dem = i

        # update zones: touches / invalidation / scores
        magnet_fired = None  # (dir, src, tgt_mid)
        bounce_fired = None

        # keep recent zones only
        if len(zones) > 200:
            zones = zones[-200:]

        for z in zones:
            if z.broken:
                continue
            # invalidate
            if z.kind == "Supply":
                brk = (c[i] if inv_close else h[i]) > z.top
            else:
                brk = (c[i] if inv_close else l[i]) < z.bot
            if brk:
                z.broken = True
                continue

            in_zone = h[i] >= z.bot and l[i] <= z.top
            just_touched = in_zone and not z.in_prev
            if just_touched:
                z.touches += 1
                z.last_touch = i
                wk = (max(h[i] - max(o[i], c[i]), 0.0) if z.kind == "Supply"
                      else max(min(o[i], c[i]) - l[i], 0.0))
                rng = max(h[i] - l[i], 1e-9)
                z.wick_f = min(z.wick_f + wk / rng, 1.0)
            z.in_prev = in_zone
            z.score = score_zone(z, i)

            if not just_touched or in_trade:
                continue

            # MAGNET: strong retested source → opposite target same session
            if signal_mode in ("magnet", "both") and z.touches >= mag_min_touch and z.score >= magnet_thr:
                same = [x for x in zones if (not x.broken and x.sess_id == z.sess_id and x.kind != z.kind and x.score >= mag_target_thr)]
                tgt = None
                best_d = 1e18
                if z.kind == "Supply":
                    for d0 in same:
                        if d0.mid < z.mid:
                            dd = z.mid - d0.mid
                            if dd <= aa * mag_max_reach and dd < best_d:
                                best_d, tgt = dd, d0
                    if tgt is not None:
                        magnet_fired = (-1, z, tgt.mid)  # short toward demand
                else:
                    for s0 in same:
                        if s0.mid > z.mid:
                            dd = s0.mid - z.mid
                            if dd <= aa * mag_max_reach and dd < best_d:
                                best_d, tgt = dd, s0
                    if tgt is not None:
                        magnet_fired = (1, z, tgt.mid)  # long toward supply

            # BOUNCE: strong zone touch → fade (trade away from zone)
            if signal_mode in ("bounce", "both") and bounce_fired is None and z.score >= bounce_thr:
                if z.kind == "Demand":
                    bounce_fired = (1, z, None)
                else:
                    bounce_fired = (-1, z, None)

        # open from signals (magnet preferred)
        if not in_trade:
            if magnet_fired is not None:
                d, src, tgt = magnet_fired
                try_open(i, d, src, tgt, "magnet")
            elif bounce_fired is not None and signal_mode in ("bounce", "both"):
                d, src, tgt = bounce_fired
                try_open(i, d, src, tgt, "bounce")

        # manage open trade
        if in_trade and i > t_i:
            if t_dir == 1:
                hit_sl, hit_tp = l[i] <= t_sl, h[i] >= t_tp
            else:
                hit_sl, hit_tp = h[i] >= t_sl, l[i] <= t_tp
            if hit_sl and hit_tp:
                close_trade(i, "loss", t_sl)
            elif hit_sl:
                close_trade(i, "loss", t_sl)
            elif hit_tp:
                close_trade(i, "win", t_tp)
            elif i - t_i >= max_hold:
                close_trade(i, "timeout", float(c[i]))

    if in_trade:
        close_trade(nbar - 1, "timeout", float(c[-1]))
    return trades


def summarize(trades: list[Trade]) -> dict:
    if not trades:
        return dict(trades=0, wins=0, losses=0, timeouts=0, wr=None, wr_res=None, avg_bars=None, avg_score=None)
    w = sum(1 for t in trades if t.outcome == "win")
    l = sum(1 for t in trades if t.outcome == "loss")
    to = sum(1 for t in trades if t.outcome == "timeout")
    res = w + l
    return dict(
        trades=len(trades),
        wins=w,
        losses=l,
        timeouts=to,
        wr=round(100 * w / len(trades), 2),
        wr_res=round(100 * w / res, 2) if res else None,
        avg_bars=round(sum(t.bars_held for t in trades) / len(trades), 2),
        avg_score=round(sum(t.score for t in trades) / len(trades), 2),
    )


def load_df(symbol: str, tf: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"{symbol}_{tf}.csv", index_col=0, parse_dates=True)
    df.columns = [c.title() for c in df.columns]
    cutoff = df.index.max() - pd.Timedelta(days=90)
    return df[df.index >= cutoff]


def main():
    symbols = ["BTC", "EURUSD", "XAU"]
    tfs = ["5m", "15m", "1h", "4h"]
    rows = []
    all_trades = []

    combos = [
        # native magnet (zone-based SL/TP) — closest to indicator intent
        dict(signal_mode="magnet", exit_mode="native", tag="magnet_native"),
        dict(signal_mode="bounce", exit_mode="native", tag="bounce_native"),
        dict(signal_mode="both", exit_mode="native", tag="both_native"),
        # ATR exits
        dict(signal_mode="magnet", exit_mode="atr", tag="magnet_atr", sl_atr=1.5, tp_atr=2.0),
        dict(signal_mode="magnet", exit_mode="atr", tag="magnet_atr_hiWR", sl_atr=2.0, tp_atr=1.0),
        dict(signal_mode="bounce", exit_mode="atr", tag="bounce_atr_hiWR", sl_atr=2.0, tp_atr=1.0),
        # user risk rules
        dict(signal_mode="magnet", exit_mode="pct", tag="magnet_btc_pct", sl_pct=3, tp_pct=5),
        dict(signal_mode="magnet", exit_mode="pip", tag="magnet_fx_pip5", sl_pips=5, tp_pips=5),
    ]

    for symbol in symbols:
        for tf in tfs:
            df = load_df(symbol, tf)
            pip = 1.0 if symbol == "XAU" else 0.0001
            max_hold = {"5m": 288 * 2, "15m": 96 * 2, "1h": 24 * 5, "4h": 6 * 10}[tf]
            print(f"\n=== {symbol} {tf} bars={len(df)} ===")
            for cfg in combos:
                # skip irrelevant risk modes
                if cfg["exit_mode"] == "pct" and symbol != "BTC":
                    continue
                if cfg["exit_mode"] == "pip" and symbol == "BTC":
                    continue
                kw = {k: v for k, v in cfg.items() if k not in ("tag",)}
                kw["pip_size"] = pip
                kw["max_hold"] = max_hold
                trades = detect_and_trade(df, symbol, tf, **kw)
                st = summarize(trades)
                st.update(symbol=symbol, tf=tf, config=cfg["tag"], signal=cfg["signal_mode"], exit=cfg["exit_mode"])
                rows.append(st)
                all_trades.extend(asdict(t) for t in trades)
                print(
                    f"  {cfg['tag']:22s} n={st['trades']:4d} WR={st['wr']}% "
                    f"WRres={st['wr_res']}% W/L/T={st['wins']}/{st['losses']}/{st['timeouts']} "
                    f"avgBars={st['avg_bars']} score={st['avg_score']}"
                )

    sdf = pd.DataFrame(rows)
    sdf.to_csv(OUT / "sd_magnet_summary.csv", index=False)
    pd.DataFrame(all_trades).to_csv(OUT / "sd_magnet_trades.csv", index=False)

    # pivots for key configs
    for tag in ["magnet_native", "magnet_atr_hiWR", "bounce_atr_hiWR", "magnet_fx_pip5", "magnet_btc_pct"]:
        sub = sdf[sdf["config"] == tag]
        if sub.empty:
            continue
        print(f"\n--- WR pivot: {tag} ---")
        piv = sub.pivot_table(index="symbol", columns="tf", values="wr", aggfunc="first")
        print(piv.to_string())
        pivn = sub.pivot_table(index="symbol", columns="tf", values="trades", aggfunc="first")
        print("trades:")
        print(pivn.to_string())

    print("\nWrote sd_magnet_summary.csv / sd_magnet_trades.csv")


if __name__ == "__main__":
    main()
