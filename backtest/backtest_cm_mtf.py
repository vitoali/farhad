"""Backtest of CM_MacD_Ult_MTF (ChrisMoody, 2014) — uploaded Pine v1 script.

The tradable event of this indicator is the DOT: cross of MACD(12,26) and its
signal line. NOTE: this script uses signal = SMA(macd, 9) (not the standard
EMA), which is reproduced faithfully here.

The script itself has NO filters, NO exits and NO alerts — it's visual only.
We evaluate raw dots and then ablate filters that could raise the win rate:

  BASE       every dot (long = cross up, short = cross down)
  TREND      + EMA200 chart trend filter (long above / short below)
  HTF        + higher-TF MACD state (4H for 1H charts, 1H for 15M charts),
               computed from CLOSED HTF candles only (the original script's
               MTF mode repaints intrabar — we test the non-repainting form)
  T+H        both filters
  ZLINE      dot must agree with zero line (long cross above 0 = continuation)
  CONFIRM2   enter only after the new MACD-vs-signal state holds 2 bars
  T+H+C2     trend + HTF + 2-bar confirmation

Exits: ATR(14) brackets with three risk/reward profiles to show the win-rate /
expectancy trade-off: RR2 (SL1.5/TP3), RR1 (SL1.5/TP1.5), RR0.5 (SL2/TP1).
Costs per side: BTC 0.05% (taker fee), gold 0.02%, EURUSD 0.01% (~1 pip
round trip). Entry = next bar open after the signal bar closes.

Eval window: last 180 days on 1H files, last 30 days on 15M files.
"""
import numpy as np
import pandas as pd

from backtest_macd_ultimate import atr, pine_ema, atr_bracket_stats, summarize

HTF_RULE = {"1h": "4h", "15m": "1h", "4h": "1D"}
BRACKETS = [("RR2  (SL1.5/TP3)", 1.5, 3.0),
            ("RR1  (SL1.5/TP1.5)", 1.5, 1.5),
            ("RR0.5(SL2/TP1)", 2.0, 1.0)]


def pine_sma(series, length):
    return pd.Series(series).rolling(length).mean().to_numpy()


def macd_cm(close):
    macd = pine_ema(close, 12) - pine_ema(close, 26)
    sig = pine_sma(macd, 9)
    return macd, sig


def cross_arrays(macd, sig):
    n = len(macd)
    up = np.zeros(n, dtype=bool)
    dn = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if np.isnan(macd[i]) or np.isnan(sig[i]) or np.isnan(macd[i - 1]) or np.isnan(sig[i - 1]):
            continue
        up[i] = macd[i - 1] <= sig[i - 1] and macd[i] > sig[i]
        dn[i] = macd[i - 1] >= sig[i - 1] and macd[i] < sig[i]
    return up, dn


def htf_macd_state(df, ltf):
    """+1 when HTF MACD > its signal, -1 otherwise; closed HTF candles only."""
    rule = HTF_RULE[ltf]
    s = df.set_index("time")["close"].resample(rule).last().dropna()
    macd, sig = macd_cm(s.to_numpy())
    state = np.where(np.isnan(sig), 0, np.where(macd > sig, 1, -1))
    htf_close_time = (s.index + pd.Timedelta(rule)).to_numpy()
    pos = np.searchsorted(htf_close_time, df["time"].to_numpy(), side="right") - 1
    out = np.zeros(len(df), dtype=int)
    ok = pos >= 0
    out[ok] = state[pos[ok]]
    return out


def run(name, csv_path, ltf, eval_days, cost):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    close = df["close"].to_numpy()
    n = len(close)

    macd, sig = macd_cm(close)
    up, dn = cross_arrays(macd, sig)
    atr_arr = atr(df)
    ema200 = pine_ema(close, 200)
    trend_up = close > ema200
    htf = htf_macd_state(df, ltf)

    # 2-bar confirmation: state changed 2 bars ago and still holds
    above = macd > sig
    conf_long = np.zeros(n, dtype=bool)
    conf_short = np.zeros(n, dtype=bool)
    for i in range(2, n):
        conf_long[i] = up[i - 1] and above[i]
        conf_short[i] = dn[i - 1] and not above[i]

    eval_start = df["time"].iloc[-1] - pd.Timedelta(days=eval_days)
    st = int(np.argmax((df["time"] >= eval_start).to_numpy()))
    rng = range(st, n - 1)

    L = [i for i in rng if up[i]]
    S = [i for i in rng if dn[i]]
    variants = {
        "BASE    ": (L, S),
        "TREND   ": ([i for i in L if trend_up[i]], [i for i in S if not trend_up[i]]),
        "HTF     ": ([i for i in L if htf[i] == 1], [i for i in S if htf[i] == -1]),
        "T+H     ": ([i for i in L if trend_up[i] and htf[i] == 1],
                     [i for i in S if not trend_up[i] and htf[i] == -1]),
        "ZLINE   ": ([i for i in L if macd[i] > 0], [i for i in S if macd[i] < 0]),
        "CONFIRM2": ([i for i in rng if conf_long[i]], [i for i in rng if conf_short[i]]),
        "T+H+C2  ": ([i for i in rng if conf_long[i] and trend_up[i] and htf[i] == 1],
                     [i for i in rng if conf_short[i] and not trend_up[i] and htf[i] == -1]),
    }

    print(f"\n{'='*84}\n{name}   ({df['time'].iloc[st]:%Y-%m-%d} .. {df['time'].iloc[-1]:%Y-%m-%d}, dots: {len(L)}L/{len(S)}S)\n{'='*84}")
    for blabel, sl_m, tp_m in BRACKETS:
        print(f"\n {blabel}")
        for vname, (li, si) in variants.items():
            rl = atr_bracket_stats(df, li, 1, atr_arr, sl_m, tp_m, cost_per_side=cost)
            rs = atr_bracket_stats(df, si, -1, atr_arr, sl_m, tp_m, cost_per_side=cost)
            allr = np.concatenate([rl, rs]) if len(rl) or len(rs) else np.array([])
            print(f"   {vname} (L={len(li):>3} S={len(si):>3}) : {summarize(allr)}")


COST = {"gold": 0.0002, "btc": 0.0005, "eurusd": 0.0001}

if __name__ == "__main__":
    run("GOLD 1H — 6 months", "data/gold_1h_6m.csv", "1h", 180, COST["gold"])
    run("BTC 1H — 6 months", "data/btc_1h_6m.csv", "1h", 180, COST["btc"])
    run("EURUSD 1H — 6 months", "data/eurusd_1h_6m.csv", "1h", 180, COST["eurusd"])
    run("GOLD 15M — 1 month", "data/gold_15m.csv", "15m", 30, COST["gold"])
    run("BTC 15M — 1 month", "data/btc_15m_6m.csv", "15m", 30, COST["btc"])
    run("EURUSD 15M — 1 month", "data/eurusd_15m.csv", "15m", 30, COST["eurusd"])
    run("BTC 4H — 6 months", "data/btc_4h.csv", "4h", 180, COST["btc"])
    run("BTC 4H — 12 months", "data/btc_4h.csv", "4h", 365, COST["btc"])
