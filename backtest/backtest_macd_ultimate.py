"""Backtest of "CM_MACD_Ultimate_Position_Fixed" (uploaded Pine v5 indicator).

Faithful re-implementation of the Pine logic:
  - MACD(12,26,9) with Pine-style EMA (seeded with SMA of first `length` bars)
  - dynamic OB/OS levels = +/- 1.0 * population stdev(macdLine, 100)
  - SILVER signal = signal-line cross while macdLine beyond the dynamic band
  - divergence on macdLine pivots (lbL=lbR=5), confirmed 5 bars late
  - GOLD signal = SILVER + divergence seen within the last 10 bars
Signals are decided on bar close; the indicator itself plots the dot one bar
later (offset=1 on [1] series), so realistic entry = next bar OPEN.

Evaluation = last 30 days only; earlier data is indicator warm-up.

Exit models tested:
  A) fixed horizon: forward return after N bars (5/10/20)
  B) ATR(14) bracket: SL = 1.5*ATR, TP = 3.0*ATR (SL assumed first on ambiguous bars)
  C) flip: stay in until an opposite SILVER signal (max hold 200 bars)
Costs: 0.05% per side applied to every closed trade.
"""
import datetime as dt
import numpy as np
import pandas as pd

COST_PER_SIDE = 0.0005
EVAL_DAYS = 30


# ── Pine-equivalent primitives ──────────────────────────────────────────
def pine_ema(series, length):
    s = np.asarray(series, dtype=float)
    out = np.full_like(s, np.nan)
    alpha = 2.0 / (length + 1)
    if len(s) < length:
        return out
    out[length - 1] = np.mean(s[:length])
    for i in range(length, len(s)):
        out[i] = alpha * s[i] + (1 - alpha) * out[i - 1]
    return out


def rolling_stdev_pop(series, length):
    return pd.Series(series).rolling(length).std(ddof=0).to_numpy()


def pivot_flags(series, lbL, lbR):
    """flag[i]=True when a pivot at bar i-lbR is CONFIRMED on bar i."""
    s = np.asarray(series, dtype=float)
    n = len(s)
    pl = np.zeros(n, dtype=bool)
    ph = np.zeros(n, dtype=bool)
    for i in range(lbL + lbR, n):
        c = i - lbR
        w = s[c - lbL: c + lbR + 1]
        if np.isnan(w).any():
            continue
        v = s[c]
        others = np.concatenate([w[:lbL], w[lbL + 1:]])
        if (v < others).all():
            pl[i] = True
        if (v > others).all():
            ph[i] = True
    return pl, ph


def atr(df, length=14):
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    pc = np.roll(c, 1)
    pc[0] = np.nan
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    # Pine ta.atr uses RMA
    out = np.full_like(tr, np.nan)
    if len(tr) > length:
        out[length] = np.nanmean(tr[1:length + 1])
        a = 1.0 / length
        for i in range(length + 1, len(tr)):
            out[i] = a * tr[i] + (1 - a) * out[i - 1]
    return out


# ── indicator signals ───────────────────────────────────────────────────
def compute_signals(df):
    close = df["close"].to_numpy()
    low = df["low"].to_numpy()
    high = df["high"].to_numpy()
    n = len(close)
    lbL = lbR = 5

    macd = pine_ema(close, 12) - pine_ema(close, 26)
    valid = ~np.isnan(macd)
    sig = np.full(n, np.nan)
    sig[valid] = pine_ema(macd[valid], 9)
    sd = rolling_stdev_pop(macd, 100)

    cross_up = np.zeros(n, dtype=bool)
    cross_dn = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if np.isnan(macd[i]) or np.isnan(sig[i]) or np.isnan(macd[i - 1]) or np.isnan(sig[i - 1]):
            continue
        cross_up[i] = macd[i - 1] <= sig[i - 1] and macd[i] > sig[i]
        cross_dn[i] = macd[i - 1] >= sig[i - 1] and macd[i] < sig[i]

    in_os = macd < -sd
    in_ob = macd > sd
    silver_long = cross_up & in_os
    silver_short = cross_dn & in_ob

    pl, ph = pivot_flags(macd, lbL, lbR)
    p_macd_lo = np.nan
    p_price_lo = np.nan
    p_macd_hi = np.nan
    p_price_hi = np.nan
    bull_div = np.zeros(n, dtype=bool)
    bear_div = np.zeros(n, dtype=bool)
    for i in range(n):
        # Pine: comparison uses the var's value from the PREVIOUS bar,
        # i.e. the previous pivot, then the var is updated.
        if pl[i]:
            bull_div[i] = (not np.isnan(p_macd_lo) and macd[i - lbR] > p_macd_lo
                           and low[i - lbR] < p_price_lo)
            p_macd_lo = macd[i - lbR]
            p_price_lo = low[i - lbR]
        if ph[i]:
            bear_div[i] = (not np.isnan(p_macd_hi) and macd[i - lbR] < p_macd_hi
                           and high[i - lbR] > p_price_hi)
            p_macd_hi = macd[i - lbR]
            p_price_hi = high[i - lbR]

    last_bull = -10**9
    last_bear = -10**9
    is_bull_div = np.zeros(n, dtype=bool)
    is_bear_div = np.zeros(n, dtype=bool)
    for i in range(n):
        if bull_div[i]:
            last_bull = i
        if bear_div[i]:
            last_bear = i
        is_bull_div[i] = (i - last_bull) < 10
        is_bear_div[i] = (i - last_bear) < 10

    gold_long = silver_long & is_bull_div
    gold_short = silver_short & is_bear_div
    return dict(macd=macd, signal=sig, sd=sd,
                silver_long=silver_long, silver_short=silver_short,
                gold_long=gold_long, gold_short=gold_short)


# ── evaluation ──────────────────────────────────────────────────────────
def fixed_horizon_stats(df, idxs, direction, horizons=(5, 10, 20)):
    close = df["close"].to_numpy()
    opens = df["open"].to_numpy()
    res = {}
    for h in horizons:
        rets = []
        for i in idxs:
            e = i + 1
            x = e + h
            if x >= len(close):
                continue
            r = direction * (close[x] - opens[e]) / opens[e]
            rets.append(r - 2 * COST_PER_SIDE)
        if rets:
            rets = np.array(rets)
            res[h] = (len(rets), (rets > 0).mean() * 100, rets.mean() * 100, np.median(rets) * 100)
    return res


def atr_bracket_stats(df, idxs, direction, atr_arr, sl_m=1.5, tp_m=3.0, max_hold=200,
                      cost_per_side=COST_PER_SIDE):
    opens = df["open"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    outs = []
    for i in idxs:
        e = i + 1
        if e >= len(opens) or np.isnan(atr_arr[i]):
            continue
        entry = opens[e]
        sl = entry - direction * sl_m * atr_arr[i]
        tp = entry + direction * tp_m * atr_arr[i]
        result = None
        for j in range(e, min(e + max_hold, len(close))):
            hit_sl = low[j] <= sl if direction == 1 else high[j] >= sl
            hit_tp = high[j] >= tp if direction == 1 else low[j] <= tp
            if hit_sl:           # pessimistic: SL first on ambiguous bars
                result = direction * (sl - entry) / entry
                break
            if hit_tp:
                result = direction * (tp - entry) / entry
                break
        if result is None:
            j = min(e + max_hold, len(close)) - 1
            result = direction * (close[j] - entry) / entry
        outs.append(result - 2 * cost_per_side)
    return np.array(outs)


def flip_model(df, sig, eval_start_idx):
    """Enter on silver signal (next open), exit/reverse on opposite silver signal."""
    opens = df["open"].to_numpy()
    close = df["close"].to_numpy()
    n = len(close)
    trades = []
    pos = 0
    entry_px = np.nan
    entry_i = None
    for i in range(eval_start_idx, n - 1):
        lg, sh = sig["silver_long"][i], sig["silver_short"][i]
        if lg and pos <= 0:
            if pos == -1:
                trades.append((entry_i, i + 1, -1, (entry_px - opens[i + 1]) / entry_px - 2 * COST_PER_SIDE))
            pos, entry_px, entry_i = 1, opens[i + 1], i + 1
        elif sh and pos >= 0:
            if pos == 1:
                trades.append((entry_i, i + 1, 1, (opens[i + 1] - entry_px) / entry_px - 2 * COST_PER_SIDE))
            pos, entry_px, entry_i = -1, opens[i + 1], i + 1
    if pos != 0:  # mark-to-market the open trade at the last close
        trades.append((entry_i, n - 1, pos, pos * (close[-1] - entry_px) / entry_px - 2 * COST_PER_SIDE))
    return trades


def summarize(rets):
    rets = np.asarray(rets)
    if len(rets) == 0:
        return "no trades"
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    eq = np.cumprod(1 + rets)
    dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min()
    return (f"n={len(rets)}  win%={100*(rets>0).mean():.0f}  avg={100*rets.mean():+.2f}%  "
            f"total={100*(eq[-1]-1):+.2f}%  PF={pf:.2f}  maxDD={100*dd:.2f}%")


def run(name, csv_path):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"])
    sig = compute_signals(df)
    atr_arr = atr(df)

    eval_start = df["time"].iloc[-1] - pd.Timedelta(days=EVAL_DAYS)
    eval_mask = (df["time"] >= eval_start).to_numpy()
    eval_start_idx = int(np.argmax(eval_mask))

    def idxs(key):
        return [i for i in range(eval_start_idx, len(df) - 1) if sig[key][i]]

    sl_i, ss_i = idxs("silver_long"), idxs("silver_short")
    gl_i, gs_i = idxs("gold_long"), idxs("gold_short")

    print(f"\n{'='*74}\n{name}   ({df['time'].iloc[eval_start_idx]:%Y-%m-%d} .. {df['time'].iloc[-1]:%Y-%m-%d}, {int(eval_mask.sum())} bars)\n{'='*74}")
    print(f"signals: silver BUY={len(sl_i)}  silver SELL={len(ss_i)}  gold BUY={len(gl_i)}  gold SELL={len(gs_i)}")

    for label, li, si in [("SILVER", sl_i, ss_i), ("GOLD", gl_i, gs_i)]:
        for dname, ii, d in [("BUY ", li, 1), ("SELL", si, -1)]:
            if not ii:
                continue
            print(f"\n-- {label} {dname} ({len(ii)} signals) --")
            for h, (cnt, wr, avg, med) in fixed_horizon_stats(df, ii, d).items():
                print(f"   hold {h:>2} bars : n={cnt:<3} win%={wr:5.1f}  avg={avg:+.3f}%  med={med:+.3f}%")
            br = atr_bracket_stats(df, ii, d, atr_arr)
            if len(br):
                print(f"   ATR 1.5SL/3TP: {summarize(br)}")

    trades = flip_model(df, sig, eval_start_idx)
    print(f"\n-- FLIP model (silver, always-in) --\n   {summarize([t[3] for t in trades])}")

    print("\n-- signal log (last month) --")
    for i in sorted(set(sl_i + ss_i)):
        kind = "BUY " if sig["silver_long"][i] else "SELL"
        gold = "GOLD  " if (sig["gold_long"][i] or sig["gold_short"][i]) else "silver"
        nxt = df["open"].iloc[i + 1]
        print(f"   {df['time'].iloc[i]:%Y-%m-%d %H:%M}  {kind} {gold}  close={df['close'].iloc[i]:<10.2f} entry(next open)={nxt:.2f}")
    return df, sig


if __name__ == "__main__":
    run("GOLD (GC=F futures) — 1H", "data/gold_1h.csv")
    run("GOLD (GC=F futures) — 15M", "data/gold_15m.csv")
    run("BITCOIN (BTC-USD Coinbase) — 1H", "data/btc_1h.csv")
    run("BITCOIN (BTC-USD Coinbase) — 15M", "data/btc_15m.csv")
