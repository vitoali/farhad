"""Python ports of the Pine indicators, with signal parity.

All signals are bar-close confirmed: a signal at index i means the condition was
true at the close of bar i; execution happens at open of bar i+1.
"""
import numpy as np
import pandas as pd


# ---------- shared building blocks ----------

def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - pc).abs(),
        (df["low"] - pc).abs(),
    ], axis=1).max(axis=1)
    return tr


def rma(s: pd.Series, length: int) -> pd.Series:
    """Pine ta.rma (Wilder). ewm alpha=1/len matches after warmup."""
    return s.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def atr_rma(df: pd.DataFrame, length: int) -> pd.Series:
    return rma(true_range(df), length)


def ema(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(span=length, adjust=False, min_periods=length).mean()


def rsi(s: pd.Series, length: int) -> pd.Series:
    d = s.diff()
    up = rma(d.clip(lower=0), length)
    dn = rma((-d).clip(lower=0), length)
    return 100 - 100 / (1 + up / dn)


def mfi(df: pd.DataFrame, length: int) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]
    pos = mf.where(tp > tp.shift(1), 0.0)
    neg = mf.where(tp < tp.shift(1), 0.0)
    pos_s = pos.rolling(length).sum()
    neg_s = neg.rolling(length).sum()
    return 100 - 100 / (1 + pos_s / neg_s)


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


# ---------- 001: UT Bot v2 ----------

def ut_bot(df: pd.DataFrame, mult: float = 1.0, atr_len: int = 10) -> pd.DataFrame:
    src = df["close"].to_numpy()
    sl = (mult * atr_rma(df, atr_len)).to_numpy()
    n = len(df)
    tsl = np.full(n, np.nan)
    for i in range(1, n):
        prev = tsl[i - 1]
        if np.isnan(sl[i]):
            continue
        if np.isnan(prev):
            tsl[i] = src[i] - sl[i]  # seed on first computable bar
            continue
        if src[i] > prev and src[i - 1] > prev:
            tsl[i] = max(prev, src[i] - sl[i])
        elif src[i] < prev and src[i - 1] < prev:
            tsl[i] = min(prev, src[i] + sl[i])
        elif src[i] > prev:
            tsl[i] = src[i] - sl[i]
        else:
            tsl[i] = src[i] + sl[i]
    t = pd.Series(tsl, index=df.index)
    out = pd.DataFrame(index=df.index)
    out["long"] = crossover(df["close"], t).fillna(False)
    out["short"] = crossunder(df["close"], t).fillna(False)
    out["line"] = t
    return out


# ---------- 002: AlphaTrend ----------

def alphatrend(df: pd.DataFrame, coeff: float = 1.0, ap: int = 14,
               use_volume: bool = True) -> pd.DataFrame:
    atr_sma = true_range(df).rolling(ap).mean()
    up_t = (df["low"] - atr_sma * coeff).to_numpy()
    down_t = (df["high"] + atr_sma * coeff).to_numpy()
    mom = (mfi(df, ap) if use_volume else rsi(df["close"], ap)).to_numpy()
    n = len(df)
    at = np.zeros(n)
    for i in range(n):
        prev = at[i - 1] if i > 0 else 0.0
        if np.isnan(mom[i]) or np.isnan(up_t[i]):
            at[i] = prev
            continue
        if mom[i] >= 50:
            at[i] = prev if up_t[i] < prev else up_t[i]
        else:
            at[i] = prev if down_t[i] > prev else down_t[i]
    s = pd.Series(at, index=df.index)
    raw_buy = crossover(s, s.shift(2)).fillna(False).to_numpy()
    raw_sell = crossunder(s, s.shift(2)).fillna(False).to_numpy()

    # Pine alternation filter: barssince(buy[1]) > barssince(sell) (na -> False)
    long_sig = np.zeros(n, dtype=bool)
    short_sig = np.zeros(n, dtype=bool)
    last_buy = -1
    last_sell = -1
    for i in range(n):
        if raw_buy[i]:
            if last_buy >= 0 and last_sell >= 0 and (i - last_buy - 1) > (i - last_sell):
                long_sig[i] = True
        if raw_sell[i]:
            if last_sell >= 0 and last_buy >= 0 and (i - last_sell - 1) > (i - last_buy):
                short_sig[i] = True
        if raw_buy[i]:
            last_buy = i
        if raw_sell[i]:
            last_sell = i
    out = pd.DataFrame(index=df.index)
    out["long"] = long_sig
    out["short"] = short_sig
    out["line"] = s
    # bars the line has been flat before each bar (chop indicator)
    flat = (s.diff() == 0).to_numpy()
    run = np.zeros(n)
    for i in range(1, n):
        run[i] = run[i - 1] + 1 if flat[i] else 0
    out["flat_bars"] = run
    return out


# ---------- 003: MA cross with structural stops ----------

def ma_cross(df: pd.DataFrame, len1: int = 21, len2: int = 50,
             swing_lookback: int = 5, atr_len: int = 14,
             risk_m: float = 1.0) -> pd.DataFrame:
    ma1 = ema(df["close"], len1)
    ma2 = ema(df["close"], len2)
    atr = atr_rma(df, atr_len)
    out = pd.DataFrame(index=df.index)
    out["long"] = (crossover(ma1, ma2) & atr.notna()).fillna(False)
    out["short"] = (crossunder(ma1, ma2) & atr.notna()).fillna(False)
    out["long_stop"] = df["low"].rolling(swing_lookback).min() - atr * risk_m
    out["short_stop"] = df["high"].rolling(swing_lookback).max() + atr * risk_m
    out["ma2_slope_up"] = ma2 >= ma2.shift(1)
    return out
