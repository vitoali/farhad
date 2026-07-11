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
