"""User-requested test of CM_MacD_Ult_MTF signals on GOLD and EURUSD:

  Exit A: ATR(55) bracket — SL = 1.0*ATR55, TP = 2.0*ATR55
  Exit B: fixed bracket   — SL = 2%,        TP = 4%

Timeframes: 5m, 15m, 1H, 4H. Eval window: last 90 days where data allows
(Yahoo caps 5m/15m history at ~60-80 days; actual range is printed).
Variants: raw dots (BASE) and the v2 filters (TREND=EMA200, HTF=higher-TF
MACD state from closed candles, T+H, T+H+C2).

Costs per side: gold 0.02%, EURUSD 0.01%. Entry = next bar open.
Max hold before time-exit: 1000 bars (5m/15m), 500 (1h), 250 (4h) — the 2%/4%
fixed bracket on low TFs frequently ends as a time exit; timeout share is shown.
"""
import numpy as np
import pandas as pd

from backtest_macd_ultimate import atr, pine_ema, summarize
import backtest_cm_mtf as cm

cm.HTF_RULE["5m"] = "30min"

MAX_HOLD = {"5m": 1000, "15m": 1000, "1h": 500, "4h": 250}


def bracket(df, idxs, direction, sl_arr, tp_arr, max_hold, cost):
    """Generic bracket: sl_arr/tp_arr are SL/TP *prices* per signal bar index."""
    opens = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    outs, timeouts = [], 0
    for i in idxs:
        e = i + 1
        if e >= len(opens) or np.isnan(sl_arr[i]) or np.isnan(tp_arr[i]):
            continue
        entry, sl, tp = opens[e], sl_arr[i], tp_arr[i]
        result = None
        for j in range(e, min(e + max_hold, len(close))):
            hit_sl = low[j] <= sl if direction == 1 else high[j] >= sl
            hit_tp = high[j] >= tp if direction == 1 else low[j] <= tp
            if hit_sl:
                result = direction * (sl - entry) / entry
                break
            if hit_tp:
                result = direction * (tp - entry) / entry
                break
        if result is None:
            j = min(e + max_hold, len(close)) - 1
            result = direction * (close[j] - entry) / entry
            timeouts += 1
        outs.append(result - 2 * cost)
    return np.array(outs), timeouts


def run(name, csv_path, ltf, cost, eval_days=90):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    close = df["close"].to_numpy()
    n = len(close)

    macd, sig = cm.macd_cm(close)
    up, dn = cm.cross_arrays(macd, sig)
    atr55 = atr(df, 55)
    ema200 = pine_ema(close, 200)
    trend_up = close > ema200
    htf = cm.htf_macd_state(df, ltf)

    above = macd > sig
    conf_long = np.zeros(n, dtype=bool)
    conf_short = np.zeros(n, dtype=bool)
    for i in range(2, n):
        conf_long[i] = up[i - 1] and above[i]
        conf_short[i] = dn[i - 1] and not above[i]

    eval_start = df["time"].iloc[-1] - pd.Timedelta(days=eval_days)
    st = max(int(np.argmax((df["time"] >= eval_start).to_numpy())), 250)
    rng = range(st, n - 1)

    L = [i for i in rng if up[i]]
    S = [i for i in rng if dn[i]]
    variants = {
        "BASE   ": (L, S),
        "TREND  ": ([i for i in L if trend_up[i]], [i for i in S if not trend_up[i]]),
        "HTF    ": ([i for i in L if htf[i] == 1], [i for i in S if htf[i] == -1]),
        "T+H    ": ([i for i in L if trend_up[i] and htf[i] == 1],
                    [i for i in S if not trend_up[i] and htf[i] == -1]),
        "T+H+C2 ": ([i for i in rng if conf_long[i] and trend_up[i] and htf[i] == 1],
                    [i for i in rng if conf_short[i] and not trend_up[i] and htf[i] == -1]),
    }

    # SL/TP price arrays per exit model
    entry_ref = df["close"].to_numpy()  # signal-bar close as bracket anchor
    exits = {
        "ATR55 SL1/TP2": (
            (entry_ref - 1.0 * atr55, entry_ref + 2.0 * atr55),     # long (sl, tp)
            (entry_ref + 1.0 * atr55, entry_ref - 2.0 * atr55)),    # short
        "FIX SL2%/TP4%": (
            (entry_ref * 0.98, entry_ref * 1.04),
            (entry_ref * 1.02, entry_ref * 0.96)),
    }

    mh = MAX_HOLD[ltf]
    days = (df["time"].iloc[-1] - df["time"].iloc[st]).days
    print(f"\n{'='*80}\n{name}   ({df['time'].iloc[st]:%Y-%m-%d} .. {df['time'].iloc[-1]:%Y-%m-%d} = {days}d, dots {len(L)}L/{len(S)}S)\n{'='*80}")
    for ename, ((lsl, ltp), (ssl, stp)) in exits.items():
        print(f"\n {ename}")
        for vname, (li, si) in variants.items():
            rl, tl = bracket(df, li, 1, lsl, ltp, mh, cost)
            rs, ts = bracket(df, si, -1, ssl, stp, mh, cost)
            allr = np.concatenate([rl, rs]) if len(rl) or len(rs) else np.array([])
            tmo = tl + ts
            tmo_s = f"  timeout={tmo}" if tmo else ""
            print(f"   {vname} (L={len(li):>3} S={len(si):>3}) : {summarize(allr)}{tmo_s}")


if __name__ == "__main__":
    for market, cost in [("gold", 0.0002), ("eurusd", 0.0001)]:
        M = market.upper()
        run(f"{M} 5M", f"data/{market}_5m.csv", "5m", cost)
        run(f"{M} 15M", f"data/{market}_15m_60d.csv", "15m", cost)
        run(f"{M} 1H", f"data/{market}_1h_6m.csv", "1h", cost)
        run(f"{M} 4H", f"data/{market}_4h.csv", "4h", cost)
