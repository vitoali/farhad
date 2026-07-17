#!/usr/bin/env python3
"""Full backtest: Cardwell alone vs Cardwell + SD Magnet gate."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from run_backtest import adx, atr, ema, load_df, rsi, sma
from run_sd_magnet import Zone, atr as atr_fn, score_zone

OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)


def cardwell_signals(df: pd.DataFrame, confirm: int = 3) -> pd.Series:
    r = rsi(df["Close"], 14)
    ma = sma(df["Close"], 50)
    bull_raw = (df["Close"] > ma) & (r >= 40) & (r <= 80)
    bear_raw = (df["Close"] < ma) & (r >= 20) & (r <= 60)
    bc = bull_raw.astype(int).groupby((~bull_raw).cumsum()).cumsum()
    ec = bear_raw.astype(int).groupby((~bear_raw).cumsum()).cumsum()
    bull = bull_raw & (bc >= confirm)
    bear = bear_raw & (ec >= confirm)
    regime = pd.Series(0, index=df.index)
    regime = regime.mask(bull, 1).mask(bear, -1)
    prev = regime.shift(1).fillna(0)
    ml = ema(df["Close"], 12) - ema(df["Close"], 26)
    sig = sma(ml, 9)
    ewo = sma((df["High"] + df["Low"]) / 2, 5) - sma((df["High"] + df["Low"]) / 2, 34)
    a = adx(df, 14)
    long = (regime == 1) & (prev != 1) & (ml > sig) & (ewo > ewo.shift(1)) & (a >= 20)
    short = (regime == -1) & (prev != -1) & (ml < sig) & (ewo < ewo.shift(1)) & (a >= 20)
    out = pd.Series(0, index=df.index)
    return out.mask(long, 1).mask(short, -1).fillna(0).astype(int)


def sd_masks(df: pd.DataFrame, lookback: int = 20, thr: float = 5.0):
    h = df["High"].values
    l = df["Low"].values
    c = df["Close"].values
    o = df["Open"].values
    v = df["Volume"].values.astype(float)
    a = atr_fn(df, 20).values
    vol_base = pd.Series(v).rolling(20, min_periods=1).mean().values
    nbar = len(df)
    zones: list[Zone] = []
    last_sup = last_dem = -10**9
    near_d = np.zeros(nbar, dtype=bool)
    near_s = np.zeros(nbar, dtype=bool)
    mag_up = np.zeros(nbar, dtype=bool)
    mag_dn = np.zeros(nbar, dtype=bool)
    last_nd = last_ns = -10**9
    swing = 12

    for i in range(swing * 2, nbar):
        aa = a[i]
        if np.isnan(aa) or aa <= 0:
            continue
        center = i - swing
        w_hi = h[center - swing : center + swing + 1]
        w_lo = l[center - swing : center + swing + 1]
        is_ph = h[center] >= np.max(w_hi)
        is_pl = l[center] <= np.min(w_lo)
        br = h[center] - l[center]

        if is_ph and i - last_sup >= 15 and br >= aa * 0.3:
            lo = np.min(l[center - swing + 1 : center + 1])
            imp = min(max(h[center] - lo, 0) / (aa * 3 + 1e-9), 1)
            vol = min(v[center] / vol_base[center], 1) if vol_base[center] > 0 else 0
            wick = min(max(h[center] - max(o[center], c[center]), 0) / max(br, 1e-9), 1)
            hh = aa * 0.5
            z = Zone(
                "Supply",
                h[center] + hh / 2,
                h[center] - hh / 2,
                h[center],
                center,
                0,
                last_touch=center,
                imp_f=imp,
                vol_f=vol,
                wick_f=wick,
            )
            z.score = score_zone(z, i)
            zones.append(z)
            last_sup = i

        if is_pl and i - last_dem >= 15 and br >= aa * 0.3:
            hi = np.max(h[center - swing + 1 : center + 1])
            imp = min(max(hi - l[center], 0) / (aa * 3 + 1e-9), 1)
            vol = min(v[center] / vol_base[center], 1) if vol_base[center] > 0 else 0
            wick = min(max(min(o[center], c[center]) - l[center], 0) / max(br, 1e-9), 1)
            hh = aa * 0.5
            z = Zone(
                "Demand",
                l[center] + hh / 2,
                l[center] - hh / 2,
                l[center],
                center,
                0,
                last_touch=center,
                imp_f=imp,
                vol_f=vol,
                wick_f=wick,
            )
            z.score = score_zone(z, i)
            zones.append(z)
            last_dem = i

        if len(zones) > 120:
            zones = zones[-120:]

        nd = ns = False
        mu = md = False
        for z in zones:
            if z.broken:
                continue
            if (c[i] > z.top) if z.kind == "Supply" else (c[i] < z.bot):
                z.broken = True
                continue
            in_zone = h[i] >= z.bot and l[i] <= z.top
            if in_zone and not z.in_prev:
                z.touches += 1
                z.last_touch = i
            z.in_prev = in_zone
            z.score = score_zone(z, i)
            if (abs(c[i] - z.mid) <= aa * 0.35 or in_zone) and z.score >= thr:
                if z.kind == "Demand":
                    nd = True
                    last_nd = i
                else:
                    ns = True
                    last_ns = i

        for z in zones:
            if z.broken or z.touches < 1 or z.score < 6.5:
                continue
            op = [x for x in zones if not x.broken and x.kind != z.kind and x.score >= 5]
            if z.kind == "Supply" and any(x.mid < z.mid and z.mid - x.mid <= aa * 25 for x in op):
                md = True
            if z.kind == "Demand" and any(x.mid > z.mid and x.mid - z.mid <= aa * 25 for x in op):
                mu = True

        near_d[i] = nd or (i - last_nd <= lookback)
        near_s[i] = ns or (i - last_ns <= lookback)
        mag_up[i] = mu
        mag_dn[i] = md

    idx = df.index
    return (
        pd.Series(near_d, idx),
        pd.Series(near_s, idx),
        pd.Series(mag_up, idx),
        pd.Series(mag_dn, idx),
    )


def apply_gate(cw: pd.Series, nd, ns, mu, md, mode: str) -> pd.Series:
    if mode == "cardwell_only":
        return cw.copy()
    out = pd.Series(0, index=cw.index, dtype=int)
    long_ok = {
        "near": nd,
        "magnet": mu,
        "near_or_magnet": nd | mu,
        "near_and_magnet": nd & mu,
    }[mode]
    short_ok = {
        "near": ns,
        "magnet": md,
        "near_or_magnet": ns | md,
        "near_and_magnet": ns & md,
    }[mode]
    out[(cw == 1) & long_ok] = 1
    out[(cw == -1) & short_ok] = -1
    return out


def backtest(df: pd.DataFrame, sig: pd.Series, exit_mode: str, symbol: str, max_hold: int):
    a = atr(df, 14).values
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values
    trades = []
    i = 0
    n = len(df)
    pip = 1.0 if symbol == "XAU" else 0.0001

    while i < n:
        s = int(sig.iloc[i])
        if s == 0:
            i += 1
            continue
        entry = float(c[i])
        aa = a[i] if a[i] == a[i] and a[i] > 0 else entry * 0.002
        if exit_mode == "atr_hiwr":
            d_sl, d_tp = aa * 2.0, aa * 1.0
        elif exit_mode == "atr_bal":
            d_sl, d_tp = aa * 1.5, aa * 1.5
        elif exit_mode == "pct":
            d_sl, d_tp = entry * 0.03, entry * 0.05
        else:  # pip5
            d_sl, d_tp = 5 * pip, 5 * pip
        sl = entry - d_sl if s == 1 else entry + d_sl
        tp = entry + d_tp if s == 1 else entry - d_tp
        outcome = "timeout"
        px = entry
        ej = min(i + max_hold, n - 1)
        for j in range(i + 1, min(i + max_hold + 1, n)):
            hit_sl = l[j] <= sl if s == 1 else h[j] >= sl
            hit_tp = h[j] >= tp if s == 1 else l[j] <= tp
            if hit_sl and hit_tp:
                outcome, px, ej = "loss", sl, j
                break
            if hit_sl:
                outcome, px, ej = "loss", sl, j
                break
            if hit_tp:
                outcome, px, ej = "win", tp, j
                break
        if outcome == "timeout":
            px = float(c[ej])
        trades.append(
            dict(dir=s, entry=entry, exit=px, outcome=outcome, bars=ej - i, entry_i=i, exit_i=ej)
        )
        i = ej + 1

    w = sum(1 for t in trades if t["outcome"] == "win")
    loss = sum(1 for t in trades if t["outcome"] == "loss")
    to = sum(1 for t in trades if t["outcome"] == "timeout")
    tot = len(trades)
    res = w + loss
    return dict(
        trades=tot,
        wins=w,
        losses=loss,
        timeouts=to,
        wr=round(100 * w / tot, 2) if tot else None,
        wr_res=round(100 * w / res, 2) if res else None,
        avg_bars=round(sum(t["bars"] for t in trades) / tot, 2) if tot else None,
    )


def main():
    symbols = ["BTC", "EURUSD", "XAU"]
    tfs = ["5m", "15m", "1h", "4h"]
    gates = ["cardwell_only", "near", "magnet", "near_or_magnet", "near_and_magnet"]
    exits = {
        "BTC": ["atr_hiwr", "atr_bal", "pct"],
        "EURUSD": ["atr_hiwr", "atr_bal", "pip5"],
        "XAU": ["atr_hiwr", "atr_bal", "pip5"],
    }

    rows = []
    for symbol in symbols:
        for tf in tfs:
            path = Path("data") / f"{symbol}_{tf}.csv"
            if not path.exists():
                continue
            df = load_df(symbol, tf)
            if len(df) < 100:
                continue
            print(f"\n=== {symbol} {tf} bars={len(df)} ===")
            cw = cardwell_signals(df, confirm=3)
            nd, ns, mu, md = sd_masks(df, lookback=20, thr=5.0)
            max_hold = {"5m": 288 * 2, "15m": 96 * 2, "1h": 120, "4h": 60}[tf]

            for gate in gates:
                sig = apply_gate(cw, nd, ns, mu, md, gate)
                for ex in exits[symbol]:
                    st = backtest(df, sig, ex, symbol, max_hold)
                    st.update(symbol=symbol, tf=tf, gate=gate, exit=ex)
                    rows.append(st)
                    if ex == "atr_hiwr":
                        print(
                            f"  {gate:18s} {ex:10s} n={st['trades']:3d} "
                            f"WR={st['wr']}% W/L/T={st['wins']}/{st['losses']}/{st['timeouts']}"
                        )

    sdf = pd.DataFrame(rows)
    sdf.to_csv(OUT / "cardwell_sd_gate_full.csv", index=False)

    # Focus table: atr_hiwr
    focus = sdf[sdf["exit"] == "atr_hiwr"].copy()
    print("\n========== WR%  |  ATR High-WR (SL2/TP1) ==========")
    for gate in gates:
        sub = focus[focus["gate"] == gate]
        piv = sub.pivot_table(index="symbol", columns="tf", values="wr", aggfunc="first")
        pivn = sub.pivot_table(index="symbol", columns="tf", values="trades", aggfunc="first")
        print(f"\n--- {gate} ---")
        print("WR:")
        print(piv.to_string())
        print("Trades:")
        print(pivn.to_string())

    # Summary avg
    print("\n========== Average WR (atr_hiwr, trades>=5) ==========")
    ok = focus[focus["trades"] >= 5]
    print(ok.groupby("gate")["wr"].agg(["mean", "count"]).sort_values("mean", ascending=False))

    print("\n========== Avg trades count ==========")
    print(focus.groupby("gate")["trades"].mean().sort_values(ascending=False))

    # Best practical: near_or_magnet vs only
    print("\n========== Delta: near_or_magnet - cardwell_only (atr_hiwr) ==========")
    a = focus[focus.gate == "cardwell_only"][["symbol", "tf", "wr", "trades"]].rename(
        columns={"wr": "wr_cw", "trades": "n_cw"}
    )
    b = focus[focus.gate == "near_or_magnet"][["symbol", "tf", "wr", "trades"]].rename(
        columns={"wr": "wr_gate", "trades": "n_gate"}
    )
    m = a.merge(b, on=["symbol", "tf"])
    m["d_wr"] = m["wr_gate"] - m["wr_cw"]
    m["d_n"] = m["n_gate"] - m["n_cw"]
    print(m.to_string(index=False))
    print(f"\nMean ΔWR = {m['d_wr'].mean():.2f} pts | Mean trades kept = {(m['n_gate']/m['n_cw']).mean()*100:.1f}%")

    print("\nWrote results/cardwell_sd_gate_full.csv")


if __name__ == "__main__":
    main()
