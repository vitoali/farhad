"""Pine indicator logic ported for offline backtest."""
from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr_wilder(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tr = true_range(df)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def mfi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = tp * df["volume"]
    pos = np.where(tp > tp.shift(1), raw_mf, 0.0)
    neg = np.where(tp < tp.shift(1), raw_mf, 0.0)
    pos_sum = pd.Series(pos, index=df.index).rolling(length).sum()
    neg_sum = pd.Series(neg, index=df.index).rolling(length).sum()
    ratio = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + ratio))


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


# ---------------------------------------------------------------------------
# #1 UT Bot v2
# ---------------------------------------------------------------------------

def ut_bot_signals(df: pd.DataFrame, mult: float = 1.0, atr_len: int = 10, source_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    src = out[source_col]
    sl_value = mult * atr_wilder(out, atr_len)

    tsl = np.zeros(len(out))
    src_v = src.values
    sl_v = sl_value.values

    for i in range(1, len(out)):
        prev = tsl[i - 1] if i > 1 or tsl[i - 1] != 0 else src_v[i - 1] - sl_v[i]
        if np.isnan(sl_v[i]):
            tsl[i] = prev
            continue
        s, s1 = src_v[i], src_v[i - 1]
        if s > prev and s1 > prev:
            tsl[i] = max(prev, s - sl_v[i])
        elif s < prev and s1 < prev:
            tsl[i] = min(prev, s + sl_v[i])
        elif s > prev:
            tsl[i] = s - sl_v[i]
        else:
            tsl[i] = s + sl_v[i]

    out["tsl"] = tsl
    out["buy"] = crossover(src, out["tsl"])
    out["sell"] = crossover(out["tsl"], src)
    return out


# ---------------------------------------------------------------------------
# #2 AlphaTrend
# ---------------------------------------------------------------------------

def alpha_trend_signals(
    df: pd.DataFrame,
    coeff: float = 1.0,
    ap: int = 14,
    novolumedata: bool = False,
) -> pd.DataFrame:
    out = df.copy()
    atr_proxy = sma(true_range(out), ap)
    up_t = out["low"] - atr_proxy * coeff
    down_t = out["high"] + atr_proxy * coeff

    if novolumedata:
        bull = rsi(out["close"], ap) >= 50
    else:
        bull = mfi(out, ap) >= 50

    at = np.zeros(len(out))
    up_v = up_t.values
    dn_v = down_t.values
    bull_v = bull.values

    for i in range(len(out)):
        if i == 0:
            at[i] = up_v[i] if bull_v[i] else dn_v[i]
            continue
        prev = at[i - 1]
        if bull_v[i]:
            at[i] = prev if up_v[i] < prev else up_v[i]
        else:
            at[i] = prev if dn_v[i] > prev else dn_v[i]

    out["alpha_trend"] = at
    out["buy_raw"] = crossover(out["alpha_trend"], out["alpha_trend"].shift(2))
    out["sell_raw"] = crossunder(out["alpha_trend"], out["alpha_trend"].shift(2))

    # confirmed: signal on previous bar (no repaint)
    out["buy"] = out["buy_raw"].shift(1).fillna(False)
    out["sell"] = out["sell_raw"].shift(1).fillna(False)

    # alternation filter O1 > K2 simplified on confirmed
    buy_idx = np.where(out["buy"].values)[0]
    sell_idx = np.where(out["sell"].values)[0]
    buy_ok = np.zeros(len(out), dtype=bool)
    sell_ok = np.zeros(len(out), dtype=bool)
    last_buy, last_sell = -1, -1
    for i in range(len(out)):
        if out["buy"].iloc[i]:
            if last_sell > last_buy:
                buy_ok[i] = True
            last_buy = i
        if out["sell"].iloc[i]:
            if last_buy > last_sell:
                sell_ok[i] = True
            last_sell = i
    out["buy"] = buy_ok
    out["sell"] = sell_ok
    return out


# ---------------------------------------------------------------------------
# #3 Bj Bot / 3Commas — MA cross + swing SL + R:R limit
# ---------------------------------------------------------------------------

def bj_bot_signals(
    df: pd.DataFrame,
    ma_len1: int = 21,
    ma_len2: int = 50,
    atr_len: int = 14,
    swing_lookback: int = 5,
    risk_m: float = 1.0,
    rnr: float = 1.0,
) -> pd.DataFrame:
    out = df.copy()
    out["ma1"] = ema(out["close"], ma_len1)
    out["ma2"] = ema(out["close"], ma_len2)
    out["atr"] = atr_wilder(out, atr_len)
    out["swing_low"] = out["low"].rolling(swing_lookback).min()
    out["swing_high"] = out["high"].rolling(swing_lookback).max()

    out["buy_raw"] = crossover(out["ma1"], out["ma2"]) & out["atr"].notna()
    out["sell_raw"] = crossunder(out["ma1"], out["ma2"]) & out["atr"].notna()
    out["buy"] = out["buy_raw"]  # confirmed at bar close
    out["sell"] = out["sell_raw"]

    out["long_stop"] = out["swing_low"] - out["atr"] * risk_m
    out["short_stop"] = out["swing_high"] + out["atr"] * risk_m
    out["long_risk"] = out["close"] - out["long_stop"]
    out["short_risk"] = out["short_stop"] - out["close"]
    out["long_target"] = out["close"] + rnr * out["long_risk"]
    out["short_target"] = out["close"] - rnr * out["short_risk"]
    return out


# ---------------------------------------------------------------------------
# #5 FibFib / AutoFib — rolling Fibonacci retracement zones
# ---------------------------------------------------------------------------

def fib_fib_levels(df: pd.DataFrame, fiblength: int = 265) -> pd.DataFrame:
    out = df.copy()
    maxr = out["close"].rolling(fiblength).max()
    minr = out["close"].rolling(fiblength).min()
    ranr = maxr - minr
    out["fib_max"] = maxr
    out["fib_min"] = minr
    out["fib_range"] = ranr
    out["fib_786"] = maxr - 0.236 * ranr  # 0.764 from bottom
    out["fib_618"] = maxr - 0.382 * ranr  # golden ratio
    out["fib_500"] = maxr - 0.50 * ranr
    out["fib_382"] = minr + 0.382 * ranr
    out["fib_236"] = minr + 0.236 * ranr
    return out


def fib_fib_signals(df: pd.DataFrame, fiblength: int = 265, touch_pct: float = 0.003, cooldown: int = 10) -> pd.DataFrame:
    """
    Zone touch + bounce/rejection at key Fib levels (no native signals in Pine).
    Long: low touches support fib, close bounces above.
    Short: high touches resistance fib, close rejects below.
    """
    out = fib_fib_levels(df, fiblength)
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    touch_level = [""] * n

    supports = ["fib_618", "fib_500", "fib_382"]
    resists = ["fib_618", "fib_786", "fib_max"]

    lows = out["low"].values
    highs = out["high"].values
    closes = out["close"].values
    opens = out["open"].values
    ranges = out["fib_range"].values

    last_sig = -cooldown - 1
    for i in range(fiblength, n):
        if i - last_sig < cooldown:
            continue
        if np.isnan(ranges[i]) or ranges[i] <= 0:
            continue
        tol = max(ranges[i] * touch_pct, closes[i] * 0.001)

        for lvl in supports:
            level = out[lvl].iloc[i]
            if np.isnan(level):
                continue
            if lows[i] <= level + tol and closes[i] > level and closes[i] > opens[i]:
                buy[i] = True
                touch_level[i] = lvl
                last_sig = i
                break

        if buy[i]:
            continue

        for lvl in resists:
            level = out[lvl].iloc[i]
            if np.isnan(level):
                continue
            if highs[i] >= level - tol and closes[i] < level and closes[i] < opens[i]:
                sell[i] = True
                touch_level[i] = lvl
                last_sig = i
                break

    out["buy"] = buy
    out["sell"] = sell
    out["touch_level"] = touch_level
    return out
