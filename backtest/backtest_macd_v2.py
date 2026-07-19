"""Ablation backtest: does fixing the identified weaknesses of
CM_MACD_Ultimate actually help?

Variants (all based on original SILVER signals, entry = next bar open,
exit = ATR(14) bracket, costs 0.05%/side):
  BASE        original signals, no filter
  TREND       + chart-TF trend filter: long only if close > EMA200, short only if close < EMA200
  HTF         + higher-TF trend filter: EMA50 direction on 4H (for 1H charts) / 1H (for 15M charts),
                using only CLOSED higher-TF candles (no lookahead)
  TREND+HTF   both filters

Because the original entry ("cross while DEEP in the band") is counter-trend by
construction, trend filters leave almost no trades. So two REDESIGNED entries
are also tested (both trend-aligned pullback logic, long side shown):
  V2-ZERO    MACD crosses above signal while MACD < 0, close > EMA200, HTF up
  V2-RECENT  MACD crosses above signal and was below -1*stdev within the last
             10 bars, close > EMA200, HTF up

Two bracket configs are tested: SL 1.5*ATR / TP 3.0*ATR  and  SL 1.0*ATR / TP 2.0*ATR.
Evaluation window = last 30 days (same as the original backtest).
"""
import numpy as np
import pandas as pd

from backtest_macd_ultimate import (
    compute_signals, atr, pine_ema, atr_bracket_stats, summarize, EVAL_DAYS)

HTF_RULE = {"1h": "4h", "15m": "1h"}
HTF_EMA_LEN = 50


def htf_trend(df, ltf):
    """+1/-1 higher-TF trend per LTF bar, using only closed HTF candles."""
    rule = HTF_RULE[ltf]
    s = df.set_index("time")["close"].resample(rule).last().dropna()
    ema = pine_ema(s.to_numpy(), HTF_EMA_LEN)
    htf_close_time = (s.index + pd.Timedelta(rule)).to_numpy()
    dir_htf = np.where(s.to_numpy() > ema, 1, -1)
    dir_htf = np.where(np.isnan(ema), 0, dir_htf)
    # for each LTF bar time t: last HTF candle whose close time <= t
    lt = df["time"].to_numpy()
    pos = np.searchsorted(htf_close_time, lt, side="right") - 1
    out = np.zeros(len(df), dtype=int)
    ok = pos >= 0
    out[ok] = dir_htf[pos[ok]]
    return out


def run(name, csv_path, ltf, eval_days=EVAL_DAYS):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    sig = compute_signals(df)
    atr_arr = atr(df)
    close = df["close"].to_numpy()
    ema200 = pine_ema(close, 200)
    trend_up = close > ema200
    htf_dir = htf_trend(df, ltf)

    eval_start = df["time"].iloc[-1] - pd.Timedelta(days=eval_days)
    eval_start_idx = int(np.argmax((df["time"] >= eval_start).to_numpy()))

    base_long = [i for i in range(eval_start_idx, len(df) - 1) if sig["silver_long"][i]]
    base_short = [i for i in range(eval_start_idx, len(df) - 1) if sig["silver_short"][i]]

    # redesigned entries -------------------------------------------------
    macd, sigl, sd = sig["macd"], sig["signal"], sig["sd"]
    n = len(df)
    cross_up = np.zeros(n, dtype=bool)
    cross_dn = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if np.isnan(macd[i]) or np.isnan(sigl[i]) or np.isnan(macd[i - 1]) or np.isnan(sigl[i - 1]):
            continue
        cross_up[i] = macd[i - 1] <= sigl[i - 1] and macd[i] > sigl[i]
        cross_dn[i] = macd[i - 1] >= sigl[i - 1] and macd[i] < sigl[i]

    was_os = pd.Series(macd < -sd).rolling(10, min_periods=1).max().to_numpy() == 1
    was_ob = pd.Series(macd > sd).rolling(10, min_periods=1).max().to_numpy() == 1

    def aligned(i, d):
        return (trend_up[i] and htf_dir[i] == 1) if d == 1 else (not trend_up[i] and htf_dir[i] == -1)

    rng = range(eval_start_idx, n - 1)
    v2zero_long = [i for i in rng if cross_up[i] and macd[i] < 0 and aligned(i, 1)]
    v2zero_short = [i for i in rng if cross_dn[i] and macd[i] > 0 and aligned(i, -1)]
    v2rec_long = [i for i in rng if cross_up[i] and was_os[i] and aligned(i, 1)]
    v2rec_short = [i for i in rng if cross_dn[i] and was_ob[i] and aligned(i, -1)]

    variants = {
        "BASE     ": (base_long, base_short),
        "TREND    ": ([i for i in base_long if trend_up[i]],
                      [i for i in base_short if not trend_up[i]]),
        "HTF      ": ([i for i in base_long if htf_dir[i] == 1],
                      [i for i in base_short if htf_dir[i] == -1]),
        "TREND+HTF": ([i for i in base_long if trend_up[i] and htf_dir[i] == 1],
                      [i for i in base_short if not trend_up[i] and htf_dir[i] == -1]),
        "V2-ZERO  ": (v2zero_long, v2zero_short),
        "V2-RECENT": (v2rec_long, v2rec_short),
    }

    print(f"\n{'='*78}\n{name}   ({df['time'].iloc[eval_start_idx]:%Y-%m-%d} .. {df['time'].iloc[-1]:%Y-%m-%d})\n{'='*78}")
    for sl_m, tp_m in [(1.5, 3.0), (1.0, 2.0)]:
        print(f"\n bracket SL={sl_m}xATR TP={tp_m}xATR")
        for vname, (li, si) in variants.items():
            rl = atr_bracket_stats(df, li, 1, atr_arr, sl_m, tp_m)
            rs = atr_bracket_stats(df, si, -1, atr_arr, sl_m, tp_m)
            allr = np.concatenate([rl, rs]) if len(rl) or len(rs) else np.array([])
            print(f"   {vname} (L={len(li):>3} S={len(si):>3}) : {summarize(allr)}")

    if eval_days > 60:  # month-by-month stability check
        months = df["time"].dt.to_period("M")
        print("\n monthly breakdown (bracket 1.5/3.0):")
        for vname in ["BASE     ", "V2-RECENT"]:
            li, si = variants[vname]
            print(f"   {vname}:")
            for m in sorted({months[i] for i in li + si}):
                rl = atr_bracket_stats(df, [i for i in li if months[i] == m], 1, atr_arr)
                rs = atr_bracket_stats(df, [i for i in si if months[i] == m], -1, atr_arr)
                r = np.concatenate([rl, rs]) if len(rl) or len(rs) else np.array([])
                if len(r):
                    print(f"      {m}: n={len(r):<3} total={100*((1+r).prod()-1):+6.2f}%  win%={100*(r>0).mean():.0f}")


if __name__ == "__main__":
    import sys
    if "--6m" in sys.argv:
        run("GOLD 1H — 6 MONTHS", "data/gold_1h_6m.csv", "1h", 180)
        run("BTC 1H — 6 MONTHS", "data/btc_1h_6m.csv", "1h", 180)
        run("BTC 15M — 6 MONTHS", "data/btc_15m_6m.csv", "15m", 180)
    else:
        run("GOLD 1H", "data/gold_1h.csv", "1h")
        run("GOLD 15M", "data/gold_15m.csv", "15m")
        run("BTC 1H", "data/btc_1h.csv", "1h")
        run("BTC 15M", "data/btc_15m.csv", "15m")
