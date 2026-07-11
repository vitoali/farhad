"""
Farhad Combo Strategy — synthesized from 52-indicator backtest journal.

Architecture (from LEARNING_JOURNAL.md):
  Entry:   Bj Bot EMA21/50 cross
  Filter1: UT Bot trend direction (close vs TSL)
  Filter2: AlphaTrend momentum alignment
  Filter3: Zero-Lag trend state (optional)
  Filter4: Zone confluence score (IFVG / Supply-Demand / RSI Advanced / Liquidity Shift)
  SL/TP:   Bj Bot structural swing + ATR (native R:R)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import alpha_trend_signals, atr_wilder, bj_bot_signals, crossover, crossunder, ema, true_range, ut_bot_signals
from zone_indicators import ifvg_signals, rsi_advanced_signals, supply_demand_signals, zero_lag_signals

try:
    from extra_indicators import liquidity_shift_signals
except ImportError:
    liquidity_shift_signals = None  # type: ignore


def _zero_lag_trend(df: pd.DataFrame, length: int = 70, mult: float = 1.2) -> pd.Series:
    close = df["close"]
    lag = (length - 1) // 2
    zlema = ema(close + (close - close.shift(lag)), length)
    atr_v = true_range(df).ewm(alpha=1 / length, adjust=False).mean()
    volatility = atr_v.rolling(length * 3).max() * mult
    trend = pd.Series(0, index=close.index, dtype=int)
    for i in range(1, len(df)):
        if (
            close.iloc[i] > zlema.iloc[i] + volatility.iloc[i]
            and close.iloc[i - 1] <= zlema.iloc[i - 1] + volatility.iloc[i - 1]
        ):
            trend.iloc[i] = 1
        elif (
            close.iloc[i] < zlema.iloc[i] - volatility.iloc[i]
            and close.iloc[i - 1] >= zlema.iloc[i - 1] - volatility.iloc[i - 1]
        ):
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]
    return trend


def _recent_signal(series: pd.Series, bar: int, lookback: int) -> bool:
  lo = max(0, bar - lookback)
  return bool(series.iloc[lo:bar].any())


def farhad_combo_signals(
    df: pd.DataFrame,
    mode: str = "standard",
    zone_lookback: int = 8,
    use_zero_lag: bool = True,
    novolumedata: bool = False,
    rnr: float = 1.0,
) -> pd.DataFrame:
    """
    Modes:
      loose    — Bj + UT + Alpha only
      standard — + zone confluence >= 1
      strict   — + zone confluence >= 2 + zero-lag trend
    """
    out = bj_bot_signals(df, rnr=rnr)
    ut = ut_bot_signals(df)
    alpha = alpha_trend_signals(df, novolumedata=novolumedata)
    zl_trend = _zero_lag_trend(df)

    ifvg = ifvg_signals(df)
    sd = supply_demand_signals(df)
    rsi_a = rsi_advanced_signals(df)
    liq = liquidity_shift_signals(df) if liquidity_shift_signals else None

    min_zone = {"loose": 0, "standard": 1, "strict": 2}.get(mode, 1)
    if mode == "loose":
        use_zero_lag = False

    closes = out["close"].values
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    zone_score = np.zeros(n, dtype=int)

    for i in range(1, n):
        ut_bull = closes[i] > ut["tsl"].iloc[i]
        ut_bear = closes[i] < ut["tsl"].iloc[i]
        alpha_bull = closes[i] > alpha["alpha_trend"].iloc[i]
        alpha_bear = closes[i] < alpha["alpha_trend"].iloc[i]
        zl_ok_long = zl_trend.iloc[i] == 1 if use_zero_lag else True
        zl_ok_short = zl_trend.iloc[i] == -1 if use_zero_lag else True

        z_long = z_short = 0
        if _recent_signal(ifvg["buy"], i, zone_lookback):
            z_long += 1
        if _recent_signal(sd["buy"], i, zone_lookback):
            z_long += 1
        if _recent_signal(rsi_a["buy"], i, zone_lookback):
            z_long += 1
        if liq is not None and _recent_signal(liq["buy"], i, zone_lookback):
            z_long += 1
        if _recent_signal(ifvg["sell"], i, zone_lookback):
            z_short += 1
        if _recent_signal(sd["sell"], i, zone_lookback):
            z_short += 1
        if _recent_signal(rsi_a["sell"], i, zone_lookback):
            z_short += 1
        if liq is not None and _recent_signal(liq["sell"], i, zone_lookback):
            z_short += 1

        zone_score[i] = z_long if out["buy_raw"].iloc[i] else (z_short if out["sell_raw"].iloc[i] else 0)

        if (
            out["buy_raw"].iloc[i]
            and ut_bull
            and alpha_bull
            and zl_ok_long
            and z_long >= min_zone
        ):
            buy[i] = True
        if (
            out["sell_raw"].iloc[i]
            and ut_bear
            and alpha_bear
            and zl_ok_short
            and z_short >= min_zone
        ):
            sell[i] = True

    out["buy"] = buy
    out["sell"] = sell
    out["zone_score"] = zone_score
    out["ut_tsl"] = ut["tsl"]
    out["alpha_trend_line"] = alpha["alpha_trend"]
    out["zl_trend"] = zl_trend
    return out
