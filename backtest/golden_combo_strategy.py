"""Golden Combo — MTF fusion of Elliott Wave + CM MACD + EWO/RSI (5 scenarios)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import atr_wilder, crossover, crossunder, ema, mfi, rsi, sma
from extra_indicators import cardwell_range_states, cm_macd_ultimate_signals
from zone_engine import pivot_high, pivot_low

STRUCTURE_TFS = ("4h", "1h")
CONFIRM_TF = "1h"
ENTRY_TF = "15m"
I_854 = 0.854


def _ts_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    if "timestamp" in df.columns:
        return pd.to_datetime(df["timestamp"], utc=True)
    return pd.to_datetime(df.index, utc=True)


def _align_bool(htf: pd.DataFrame, col: str, chart: pd.DataFrame) -> np.ndarray:
    s = pd.Series(htf[col].astype(bool).values, index=_ts_index(htf))
    cidx = _ts_index(chart)
    return s.reindex(cidx, method="ffill").fillna(False).values


def _align_float(htf: pd.DataFrame, col: str, chart: pd.DataFrame) -> np.ndarray:
    s = pd.Series(htf[col].values, index=_ts_index(htf))
    cidx = _ts_index(chart)
    return s.reindex(cidx, method="ffill").values


def macd_cm_states(df: pd.DataFrame, fast: int = 12, slow: int = 26, sig: int = 9) -> pd.DataFrame:
    """CM MACD histogram colours + cross states."""
    out = df.copy()
    macd = ema(out["close"], fast) - ema(out["close"], slow)
    signal = ema(macd, sig)
    hist = macd - signal
    h = hist.values
    m = macd.values
    s = signal.values
    n = len(out)

    cross_bull = crossover(macd, signal).fillna(False).values
    cross_bear = crossunder(macd, signal).fillna(False).values
    hist_aqua = np.zeros(n, dtype=bool)
    hist_maroon_turn = np.zeros(n, dtype=bool)
    hist_blue_turn = np.zeros(n, dtype=bool)
    bull_above_zero = np.zeros(n, dtype=bool)
    bear_above_zero = np.zeros(n, dtype=bool)
    cross_bull_below = np.zeros(n, dtype=bool)
    cross_bear_above = np.zeros(n, dtype=bool)
    hist_bull_turn = np.zeros(n, dtype=bool)

    for i in range(1, n):
        hist_aqua[i] = h[i] > h[i - 1] and h[i] > 0
        hist_maroon_turn[i] = h[i] > h[i - 1] and h[i] <= 0
        hist_blue_turn[i] = h[i] < h[i - 1] and h[i] > 0
        bull_above_zero[i] = m[i] > s[i] and m[i] > 0
        bear_above_zero[i] = m[i] < s[i] and m[i] > 0
        if cross_bull[i]:
            cross_bull_below[i] = m[i] < 0
            cross_bear_above[i] = False
        if cross_bear[i]:
            cross_bear_above[i] = m[i] > 0
        # first bullish hist colour shift after decline
        if h[i] > h[i - 1] and h[i - 1] <= h[i - 2] if i > 1 else False:
            hist_bull_turn[i] = True

    out["macd_cross_bull"] = cross_bull
    out["macd_cross_bear"] = cross_bear
    out["macd_cross_bull_below"] = cross_bull_below
    out["macd_cross_bear_above"] = cross_bear_above
    out["macd_bull_above_zero"] = bull_above_zero
    out["macd_hist_aqua"] = hist_aqua
    out["macd_hist_maroon_turn"] = hist_maroon_turn
    out["macd_hist_blue_turn"] = hist_blue_turn
    out["macd_hist_bull_turn"] = hist_bull_turn
    return out


def macd_divergence_states(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    sig: int = 9,
    lookback: int = 20,
    pivot_bars: int = 3,
) -> pd.DataFrame:
    """
    MACD regular divergence on confirm TF.
    Bullish: price lower low + MACD higher low (S1 filter).
    Bearish: price higher high + MACD lower high (S2 filter).
    """
    out = macd_cm_states(df, fast=fast, slow=slow, sig=sig)
    macd_line = ema(out["close"], fast) - ema(out["close"], slow)
    m = macd_line.values
    lows = out["low"].values
    highs = out["high"].values
    n = len(out)
    bull_div = np.zeros(n, dtype=bool)
    bear_div = np.zeros(n, dtype=bool)

    for i in range(lookback * 2 + pivot_bars + 2, n):
        # pivot low at i - pivot_bars
        lb = i - pivot_bars
        if lb < lookback:
            continue
        is_pl = lows[lb] <= lows[lb - pivot_bars : lb + pivot_bars + 1].min()
        if not is_pl:
            continue
        # find previous pivot low within lookback
        prev_pl = None
        for j in range(lb - pivot_bars - 1, max(pivot_bars, lb - lookback), -1):
            if lows[j] <= lows[max(0, j - pivot_bars) : j + pivot_bars + 1].min():
                prev_pl = j
                break
        if prev_pl is not None:
            if lows[lb] < lows[prev_pl] and m[lb] > m[prev_pl]:
                bull_div[i] = True

        # pivot high
        is_ph = highs[lb] >= highs[lb - pivot_bars : lb + pivot_bars + 1].max()
        if not is_ph:
            continue
        prev_ph = None
        for j in range(lb - pivot_bars - 1, max(pivot_bars, lb - lookback), -1):
            if highs[j] >= highs[max(0, j - pivot_bars) : j + pivot_bars + 1].max():
                prev_ph = j
                break
        if prev_ph is not None:
            if highs[lb] > highs[prev_ph] and m[lb] < m[prev_ph]:
                bear_div[i] = True

    out["macd_bull_div"] = bull_div
    out["macd_bear_div"] = bear_div
    return out


def ewo_rsi_features(
    df: pd.DataFrame,
    ewo_fast: int = 5,
    ewo_slow: int = 34,
    rsi_len: int = 14,
    lookback_len: int = 10,
    rsi_oversold: int = 30,
) -> pd.DataFrame:
    """EWO/RSI entry layer with pre-signals and volume filter."""
    out = df.copy()
    hl2 = (out["high"] + out["low"]) / 2
    ewo = sma(hl2, ewo_fast) - sma(hl2, ewo_slow)
    rsi_v = rsi(out["close"], rsi_len)
    mfi_v = mfi(out, 14)
    vol_ma = sma(out["volume"], 20)
    has_vol = bool(out["volume"].sum() > 0)
    vol_ok = (out["volume"] > vol_ma * 0.8) if has_vol else pd.Series(True, index=out.index)
    breakout_barrier = out["high"].rolling(lookback_len).max().shift(1)

    n = len(out)
    pre_buy = np.zeros(n, dtype=bool)
    pre_sell = np.zeros(n, dtype=bool)
    raw_buy = np.zeros(n, dtype=bool)
    raw_sell = np.zeros(n, dtype=bool)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    os = False
    last_sig = 0

    closes = out["close"].values
    rsi_a = rsi_v.values
    ewo_a = ewo.values
    mfi_a = mfi_v.values
    vol_a = vol_ok.values
    bb_a = breakout_barrier.values

    for i in range(1, n):
        if rsi_a[i] < rsi_oversold:
            os = True
        pre_buy[i] = rsi_a[i] < 40 and ewo_a[i] > ewo_a[i - 1] and ewo_a[i] < 0
        pre_sell[i] = rsi_a[i] > 60 and ewo_a[i] < ewo_a[i - 1] and ewo_a[i] > 0
        price_break = closes[i] > bb_a[i] if not np.isnan(bb_a[i]) else False
        raw_buy[i] = rsi_a[i - 1] < 40 <= rsi_a[i] and mfi_a[i] > 30 and ewo_a[i] > ewo_a[i - 1] and vol_a[i] and (price_break or os)
        raw_sell[i] = rsi_a[i - 1] > 60 >= rsi_a[i] and mfi_a[i] < 70 and ewo_a[i] < ewo_a[i - 1] and vol_a[i]
        if raw_buy[i] and last_sig != 1:
            buy[i] = True
            last_sig = 1
            os = False
        if raw_sell[i] and last_sig != -1:
            sell[i] = True
            last_sig = -1

    out["ewo"] = ewo
    out["rsi"] = rsi_v
    out["mfi"] = mfi_v
    out["vol_ok"] = vol_ok
    out["breakout_barrier"] = breakout_barrier
    out["price_breakout"] = out["close"] > breakout_barrier
    out["pre_buy"] = pre_buy
    out["pre_sell"] = pre_sell
    out["raw_buy"] = raw_buy
    out["raw_sell"] = raw_sell
    out["buy"] = buy
    out["sell"] = sell
    return out


def elliott_wave_states(df: pd.DataFrame, left: int = 8) -> pd.DataFrame:
    """LuxAlgo EW states: motive 5, wave-start, ABC box, box break."""
    out = df.copy()
    n = len(out)
    hi = out["high"].values
    lo = out["low"].values
    cl = out["close"].values

    motive_bull_5 = np.zeros(n, dtype=bool)
    motive_bear_5 = np.zeros(n, dtype=bool)
    wave_start_bull = np.zeros(n, dtype=bool)
    wave_start_bear = np.zeros(n, dtype=bool)
    corrective_bull = np.zeros(n, dtype=bool)
    corrective_bear = np.zeros(n, dtype=bool)
    box_broken = np.zeros(n, dtype=bool)
    struct_bull = np.zeros(n, dtype=bool)
    struct_bear = np.zeros(n, dtype=bool)
    wave1_high = np.full(n, np.nan)
    wave2_low = np.full(n, np.nan)
    wave4_high = np.full(n, np.nan)
    wave5_high = np.full(n, np.nan)
    wave5_low = np.full(n, np.nan)
    box_top = np.full(n, np.nan)
    box_bot = np.full(n, np.nan)
    sl_long = np.full(n, np.nan)
    sl_short = np.full(n, np.nan)
    tp_long = np.full(n, np.nan)
    tp_short = np.full(n, np.nan)

    d = [0] * 11
    x = [0] * 11
    y = [0.0] * 11
    wave_dir = 0
    wave_on = False
    b5_x = b5_y = 0.0
    bC_x = 0
    bC_set = False
    active_box_top = np.nan
    active_box_bot = np.nan
    active_box_bull = False
    last_w1_hi = np.nan
    last_w2_lo = np.nan
    last_w4_hi = np.nan
    last_w5_hi = np.nan
    last_w5_lo = np.nan

    ph_s = pivot_high(out["high"], left, 1).values
    pl_s = pivot_low(out["low"], left, 1).values

    for i in range(left + 2, n):
        x2 = i - 1

        if not np.isnan(ph_s[i]):
            dir0 = d[0]
            x1_, y1_ = x[0], y[0]
            y2 = hi[i - 1]
            if dir0 < 1:
                d.insert(0, 1); x.insert(0, x2); y.insert(0, y2); d.pop(); x.pop(); y.pop()
            elif dir0 == 1 and y2 > y1_:
                x[0], y[0] = x2, y2

            _6y = y2
            _5y, _4y, _3y, _2y, _1y = y[1], y[2], y[3], y[4], y[5]
            w5, w3, w1 = _6y - _5y, _4y - _3y, _2y - _1y
            mn = min(w1, w3, w5)
            if w3 != mn and _6y > _4y and _3y > _1y and _5y > _2y:
                motive_bull_5[i] = True
                wave_dir, wave_on = 1, True
                b5_x, b5_y = x2, _6y
                last_w1_hi, last_w2_lo = _2y, _3y
                last_w4_hi, last_w5_hi = _4y, _6y
                struct_bull[i] = True
                sl_short[i] = _6y * 1.001
                tp_short[i] = _3y

            if wave_on and wave_dir == -1 and bC_set and y[1] == bC_x and _6y > b5_y:
                wave_start_bull[i] = True
                struct_bull[i] = True

            if wave_on and wave_dir == 1 and x[3] == b5_x:
                diff = abs(b5_y - y[5]) if y[5] else abs(_6y - y[5])
                if _6y > b5_y - diff * I_854 and y[2] > b5_y - diff * I_854 and y[1] < b5_y:
                    corrective_bull[i] = True
                    active_box_top, active_box_bot = _6y, y[2]
                    active_box_bull = True
                    bC_x, bC_set = x2, True
                    box_top[i], box_bot[i] = active_box_top, active_box_bot
                    sl_long[i] = active_box_bot * 0.999
                    tp_long[i] = last_w5_hi if not np.isnan(last_w5_hi) else _6y + diff

        if not np.isnan(pl_s[i]):
            dir0 = d[0]
            x1_, y1_ = x[0], y[0]
            y2 = lo[i - 1]
            if dir0 > -1:
                d.insert(0, -1); x.insert(0, x2); y.insert(0, y2); d.pop(); x.pop(); y.pop()
            elif dir0 == -1 and y2 < y1_:
                x[0], y[0] = x2, y2

            _6y = y2
            _5y, _4y, _3y, _2y, _1y = y[1], y[2], y[3], y[4], y[5]
            w5, w3, w1 = _5y - _6y, _3y - _4y, _1y - _2y
            mn = min(w1, w3, w5)
            if w3 != mn and y[2] > _6y and y[5] > _3y and y[4] > _5y:
                motive_bear_5[i] = True
                wave_dir, wave_on = -1, True
                b5_x, b5_y = x2, _6y
                last_w1_hi, last_w2_lo = y[4], y[5]
                last_w5_lo = _6y
                struct_bear[i] = True
                sl_long[i] = _6y * 0.999
                tp_long[i] = y[2]

            if wave_on and wave_dir == 1 and bC_set and y[1] == bC_x and _6y < b5_y:
                wave_start_bear[i] = True
                struct_bear[i] = True

            if wave_on and wave_dir == -1 and x[3] == b5_x:
                diff = abs(b5_y - y[5]) if y[5] else abs(b5_y - _6y)
                if _6y < b5_y + diff * I_854 and y[2] < b5_y + diff * I_854 and y[1] > b5_y:
                    corrective_bear[i] = True
                    active_box_top, active_box_bot = y[2], _6y
                    active_box_bull = False
                    bC_x, bC_set = x2, True
                    box_top[i], box_bot[i] = active_box_top, active_box_bot
                    sl_short[i] = active_box_top * 1.001
                    tp_short[i] = last_w5_lo if not np.isnan(last_w5_lo) else _6y - diff

        # wave 3 break: price breaks wave 1 high after wave 2 low formed
        if not np.isnan(last_w1_hi) and not np.isnan(last_w2_lo) and cl[i] > last_w1_hi and lo[i - 1] <= last_w1_hi:
            wave_start_bull[i] = True
            struct_bull[i] = True
            w1_len = last_w1_hi - last_w2_lo
            sl_long[i] = last_w2_lo * 0.999
            tp_long[i] = cl[i] + w1_len * 1.618

        # C-box survival filter
        if active_box_bull and not np.isnan(active_box_bot):
            if lo[i] < active_box_bot:
                box_broken[i] = True
                active_box_bull = False
        elif not active_box_bull and not np.isnan(active_box_top):
            if hi[i] > active_box_top:
                box_broken[i] = True
                active_box_top = np.nan

        wave1_high[i] = last_w1_hi
        wave2_low[i] = last_w2_lo
        wave4_high[i] = last_w4_hi
        wave5_high[i] = last_w5_hi
        wave5_low[i] = last_w5_lo

    out["motive_bull_5"] = motive_bull_5
    out["motive_bear_5"] = motive_bear_5
    out["wave_start_bull"] = wave_start_bull
    out["wave_start_bear"] = wave_start_bear
    out["corrective_bull"] = corrective_bull
    out["corrective_bear"] = corrective_bear
    out["box_broken"] = box_broken
    out["struct_bull"] = struct_bull
    out["struct_bear"] = struct_bear
    out["box_top"] = box_top
    out["box_bot"] = box_bot
    out["sl_long"] = sl_long
    out["sl_short"] = sl_short
    out["tp_long"] = tp_long
    out["tp_short"] = tp_short
    return out


@dataclass
class GoldenSignal:
    scenario: str
    direction: str


SCENARIOS = {
    "S0_hw_long": "خرید الگوی CM MACD (سبز زیر صفر + HTF≥3)",
    "S0_hw_short": "فروش الگوی CM MACD (BTC: red hist 1h + HTF≥2)",
    "S1_bottom": "خرید کف مطلق (پایان موج ۵ نزولی)",
    "S2_top": "فروش سقف مطلق (پایان موج ۵ صعودی)",
    "S3_wave3": "خرید موج ۳ صعودی",
    "S4_pullback_long": "خرید پولبک اصلاحی C",
    "S5_pullback_short": "فروش پولبک اصلاحی C",
}


def golden_combo_signals(
    entry_df: pd.DataFrame,
    confirm_df: pd.DataFrame,
    structure_df: pd.DataFrame,
    structure_tf: str = "4h",
    require_volume: bool = True,
    use_cardwell: bool = True,
    cardwell_trend_len: int = 100,
    require_macd_div_s1s2: bool = True,
    use_cm_ultimate: bool = False,
    require_entry_ultimate_gold: bool = False,
    use_cm_hw_patterns: bool = False,
    hw_context: dict | None = None,
) -> pd.DataFrame:
    """
    Fuse 5 golden scenarios on 15m entry chart.
    Structure = Elliott (4h/1h), Confirm = MACD/CM Ultimate + Cardwell (1h), Entry = EWO/RSI (15m).
    use_cm_ultimate=True → Golden Fusion v2 (Silver/Gold OB/OS + built-in divergence).
    use_cm_hw_patterns=True → Golden Fusion v3 (green below zero + HTF≥3, 1h red hist + HTF≥2).
    """
    entry = ewo_rsi_features(entry_df)
    if use_cm_hw_patterns and hw_context is None:
        raise ValueError("hw_context required when use_cm_hw_patterns=True")
    if use_cm_ultimate:
        confirm = cm_macd_ultimate_signals(confirm_df)
        entry_ult = cm_macd_ultimate_signals(entry_df)
        cardwell = cardwell_range_states(confirm_df, trend_len=cardwell_trend_len)
        for col in ("cardwell_bull_regime", "cardwell_bear_regime", "cardwell_regime", "cardwell_long_signal", "cardwell_short_signal"):
            confirm[col] = cardwell[col].values
        if structure_tf != CONFIRM_TF:
            struct_ult = cm_macd_ultimate_signals(structure_df)
        else:
            struct_ult = None
    elif use_cm_hw_patterns:
        confirm = macd_divergence_states(confirm_df)
        cardwell = cardwell_range_states(confirm_df, trend_len=cardwell_trend_len)
        for col in ("cardwell_bull_regime", "cardwell_bear_regime", "cardwell_regime", "cardwell_long_signal", "cardwell_short_signal"):
            confirm[col] = cardwell[col].values
        entry_ult = struct_ult = None
    else:
        confirm = macd_divergence_states(confirm_df)
        cardwell = cardwell_range_states(confirm_df, trend_len=cardwell_trend_len)
        for col in ("cardwell_bull_regime", "cardwell_bear_regime", "cardwell_regime", "cardwell_long_signal", "cardwell_short_signal"):
            confirm[col] = cardwell[col].values
        entry_ult = struct_ult = None
    structure = elliott_wave_states(structure_df)

    n = len(entry)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    scenario_id = np.full(n, "", dtype=object)

    # align HTF → 15m
    s_motive_bear = _align_bool(structure, "motive_bear_5", entry)
    s_motive_bull = _align_bool(structure, "motive_bull_5", entry)
    s_wave3 = _align_bool(structure, "wave_start_bull", entry)
    s_corr_bull = _align_bool(structure, "corrective_bull", entry)
    s_corr_bear = _align_bool(structure, "corrective_bear", entry)
    s_box_broken = _align_bool(structure, "box_broken", entry)
    s_struct_bull = _align_bool(structure, "struct_bull", entry)
    s_struct_bear = _align_bool(structure, "struct_bear", entry)
    s_sl_l = _align_float(structure, "sl_long", entry)
    s_sl_s = _align_float(structure, "sl_short", entry)
    s_tp_l = _align_float(structure, "tp_long", entry)
    s_tp_s = _align_float(structure, "tp_short", entry)

    c_cardwell_bull = _align_bool(confirm, "cardwell_bull_regime", entry)
    c_cardwell_bear = _align_bool(confirm, "cardwell_bear_regime", entry)
    c_cardwell_long = _align_bool(confirm, "cardwell_long_signal", entry)
    c_cardwell_short = _align_bool(confirm, "cardwell_short_signal", entry)

    if use_cm_ultimate:
        c_cross_bull_below = c_cross_bear_above = np.zeros(n, dtype=bool)
        c_bull_above = c_hist_aqua = c_hist_maroon = c_hist_blue = np.zeros(n, dtype=bool)
        c_cross_bull = c_cross_bear = c_hist_bull_turn = np.zeros(n, dtype=bool)
        c_macd_bull_div = c_macd_bear_div = np.zeros(n, dtype=bool)
    else:
        c_cross_bull_below = _align_bool(confirm, "macd_cross_bull_below", entry)
        c_cross_bear_above = _align_bool(confirm, "macd_cross_bear_above", entry)
        c_bull_above = _align_bool(confirm, "macd_bull_above_zero", entry)
        c_hist_aqua = _align_bool(confirm, "macd_hist_aqua", entry)
        c_hist_maroon = _align_bool(confirm, "macd_hist_maroon_turn", entry)
        c_hist_blue = _align_bool(confirm, "macd_hist_blue_turn", entry)
        c_cross_bull = _align_bool(confirm, "macd_cross_bull", entry)
        c_cross_bear = _align_bool(confirm, "macd_cross_bear", entry)
        c_hist_bull_turn = _align_bool(confirm, "macd_hist_bull_turn", entry)
        c_macd_bull_div = _align_bool(confirm, "macd_bull_div", entry)
        c_macd_bear_div = _align_bool(confirm, "macd_bear_div", entry)

    if use_cm_hw_patterns and hw_context:
        hw_long = np.asarray(hw_context["hw_long_pattern"], dtype=bool)
        hw_short = np.asarray(hw_context["hw_short_pattern"], dtype=bool)
        e_green_below = np.asarray(hw_context["entry_green_below"], dtype=bool)
        c_red_hist = np.asarray(hw_context["confirm_red_hist"], dtype=bool)
        htf_long_15m = hw_context["htf_long_15m"]
        htf_short_15m = hw_context["htf_short_15m"]
        htf_short_1h = hw_context["htf_short_1h"]
    else:
        hw_long = hw_short = e_green_below = c_red_hist = None
        htf_long_15m = htf_short_15m = htf_short_1h = None

    if use_cm_ultimate:
        c_u_gold_long = _align_bool(confirm, "gold_long", entry)
        c_u_gold_short = _align_bool(confirm, "gold_short", entry)
        c_u_silver_long = _align_bool(confirm, "silver_long", entry)
        c_u_silver_short = _align_bool(confirm, "silver_short", entry)
        e_u_gold_long = _align_bool(entry_ult, "gold_long", entry)
        e_u_gold_short = _align_bool(entry_ult, "gold_short", entry)
        e_u_silver_long = _align_bool(entry_ult, "silver_long", entry)
        e_u_silver_short = _align_bool(entry_ult, "silver_short", entry)
        if struct_ult is not None:
            s_u_gold_long = _align_bool(struct_ult, "gold_long", entry)
            s_u_gold_short = _align_bool(struct_ult, "gold_short", entry)
            s_u_silver_long = _align_bool(struct_ult, "silver_long", entry)
            s_u_silver_short = _align_bool(struct_ult, "silver_short", entry)
        else:
            s_u_gold_long = s_u_gold_short = s_u_silver_long = s_u_silver_short = np.zeros(n, dtype=bool)
    else:
        c_u_gold_long = c_u_gold_short = c_u_silver_long = c_u_silver_short = None
        e_u_gold_long = e_u_gold_short = e_u_silver_long = e_u_silver_short = None
        s_u_gold_long = s_u_gold_short = s_u_silver_long = s_u_silver_short = None

    vol_ok = entry["vol_ok"].fillna(True).values
    atr_v = atr_wilder(entry, 14).values
    closes = entry["close"].values

    # rolling HTF context windows (structure flags stay valid ~32 bars on 15m)
    def recent(arr: np.ndarray, i: int, win: int = 48) -> bool:
        lo = max(0, i - win)
        return bool(arr[lo : i + 1].any())

    for i in range(1, n):
        if require_volume and not vol_ok[i]:
            continue

        e_buy = bool(entry["buy"].iloc[i] or entry["raw_buy"].iloc[i])
        e_sell = bool(entry["sell"].iloc[i] or entry["raw_sell"].iloc[i])
        e_pre_buy = bool(entry["pre_buy"].iloc[i])
        e_pre_sell = bool(entry["pre_sell"].iloc[i])
        e_break = bool(entry["price_breakout"].iloc[i])

        struct_ok_long = recent(s_struct_bull, i, 64) or recent(s_motive_bear, i, 64) or recent(s_corr_bull, i, 64)
        struct_ok_short = recent(s_struct_bear, i, 64) or recent(s_motive_bull, i, 64) or recent(s_corr_bear, i, 64)

        atr = float(atr_v[i]) if not np.isnan(atr_v[i]) else closes[i] * 0.002

        # S0 — high-WR CM MACD pattern entry (70–80% WR in study)
        if use_cm_hw_patterns and hw_long[i]:
            buy[i] = True
            scenario_id[i] = "S0_hw_long"
            sl_p[i] = s_sl_l[i] if not np.isnan(s_sl_l[i]) else closes[i] - atr * 2
            tp_p[i] = s_tp_l[i] if not np.isnan(s_tp_l[i]) else closes[i] + atr * 3
            continue
        if use_cm_hw_patterns and hw_short[i]:
            sell[i] = True
            scenario_id[i] = "S0_hw_short"
            sl_p[i] = s_sl_s[i] if not np.isnan(s_sl_s[i]) else closes[i] + atr * 2
            tp_p[i] = s_tp_s[i] if not np.isnan(s_tp_s[i]) else closes[i] - atr * 3
            continue

        if use_cm_hw_patterns:
            macd_bull_confirm = recent(hw_long, i, 24)
            macd_bear_confirm = recent(hw_short, i, 32)
            macd_wave3_confirm = recent(hw_long, i, 32)
            macd_pullback_bull = recent(hw_long, i, 32)
            macd_pullback_bear = recent(hw_short, i, 32)
            s1_div_ok = s2_div_ok = True
            entry_ult_long_ok = entry_ult_short_ok = True
        elif use_cm_ultimate:
            # 1H Ultimate: gold preferred; silver acceptable with 4H structure alignment
            macd_bull_confirm = (
                recent(c_u_gold_long, i, 32)
                or recent(c_u_silver_long, i, 24)
                or (structure_tf == "4h" and recent(s_u_silver_long, i, 48))
            )
            macd_bear_confirm = (
                recent(c_u_gold_short, i, 32)
                or recent(c_u_silver_short, i, 24)
                or (structure_tf == "4h" and recent(s_u_silver_short, i, 48))
            )
            macd_wave3_confirm = recent(c_u_silver_long, i, 32) and (c_u_gold_long[i] or recent(c_u_gold_long, i, 16))
            macd_pullback_bull = recent(c_u_silver_long, i, 32) or recent(c_u_gold_long, i, 32)
            macd_pullback_bear = recent(c_u_silver_short, i, 32) or recent(c_u_gold_short, i, 32)
            # S1/S2: gold on 1H replaces separate divergence filter
            s1_div_ok = recent(c_u_gold_long, i, 48) or not require_macd_div_s1s2
            s2_div_ok = recent(c_u_gold_short, i, 48) or not require_macd_div_s1s2
            entry_ult_long_ok = (not require_entry_ultimate_gold) or recent(e_u_gold_long, i, 16) or e_u_gold_long[i]
            entry_ult_short_ok = (not require_entry_ultimate_gold) or recent(e_u_gold_short, i, 16) or e_u_gold_short[i]
        else:
            macd_bull_confirm = recent(c_cross_bull_below, i, 32) or recent(c_hist_maroon, i, 16) or recent(c_cross_bull, i, 24)
            macd_bear_confirm = recent(c_cross_bear_above, i, 32) or recent(c_hist_blue, i, 16) or recent(c_cross_bear, i, 24)
            macd_wave3_confirm = recent(c_bull_above, i, 32) and (c_hist_aqua[i] or recent(c_hist_aqua, i, 8))
            macd_pullback_bull = recent(c_cross_bull, i, 32) or recent(c_hist_bull_turn, i, 16)
            macd_pullback_bear = recent(c_cross_bear, i, 32)
            s1_div_ok = (not require_macd_div_s1s2) or recent(c_macd_bull_div, i, 96)
            s2_div_ok = (not require_macd_div_s1s2) or recent(c_macd_bear_div, i, 96)
            entry_ult_long_ok = entry_ult_short_ok = True

        # S1/S2 Cardwell: skip at reversals when Ultimate/HW patterns handle OB/OS
        if use_cm_ultimate or use_cm_hw_patterns:
            cardwell_s1_ok = cardwell_s2_ok = True
        else:
            cardwell_s1_ok = (not use_cardwell) or (not c_cardwell_bear[i] and not recent(c_cardwell_bear, i, 8))
            cardwell_s2_ok = (not use_cardwell) or (not c_cardwell_bull[i] and not recent(c_cardwell_bull, i, 8))
        cardwell_trend_long_ok = (not use_cardwell) or c_cardwell_bull[i] or recent(c_cardwell_bull, i, 16) or recent(c_cardwell_long, i, 32)
        cardwell_trend_short_ok = (not use_cardwell) or c_cardwell_bear[i] or recent(c_cardwell_bear, i, 16) or recent(c_cardwell_short, i, 32)
        if not use_cm_ultimate and not use_cm_hw_patterns:
            s1_div_ok = (not require_macd_div_s1s2) or recent(c_macd_bull_div, i, 96)
            s2_div_ok = (not require_macd_div_s1s2) or recent(c_macd_bear_div, i, 96)

        # Entry layer
        if use_cm_hw_patterns:
            e_long_trig = hw_long[i] or recent(hw_long, i, 8) or e_buy or e_pre_buy
            e_short_trig = hw_short[i] or recent(hw_short, i, 8) or e_sell or e_pre_sell
        elif use_cm_ultimate:
            e_long_trig = e_buy or e_pre_buy or e_u_silver_long[i] or e_u_gold_long[i] or recent(e_u_silver_long, i, 8) or recent(e_u_gold_long, i, 16)
            e_short_trig = e_sell or e_pre_sell or e_u_silver_short[i] or e_u_gold_short[i] or recent(e_u_silver_short, i, 8) or recent(e_u_gold_short, i, 16)
        else:
            e_long_trig = e_buy or e_pre_buy
            e_short_trig = e_sell or e_pre_sell

        # S1 — absolute bottom buy
        if (
            recent(s_motive_bear, i, 48)
            and macd_bull_confirm
            and s1_div_ok
            and cardwell_s1_ok
            and entry_ult_long_ok
            and (e_long_trig or (e_pre_buy and entry["rsi"].iloc[i] < 38))
            and struct_ok_long
        ):
            buy[i] = True
            scenario_id[i] = "S1_bottom"
            sl_p[i] = s_sl_l[i] if not np.isnan(s_sl_l[i]) else closes[i] - atr * 2
            tp_p[i] = s_tp_l[i] if not np.isnan(s_tp_l[i]) else closes[i] + atr * 3
            continue

        # S2 — absolute top sell
        if (
            recent(s_motive_bull, i, 48)
            and macd_bear_confirm
            and s2_div_ok
            and cardwell_s2_ok
            and entry_ult_short_ok
            and (e_short_trig or (e_pre_sell and entry["rsi"].iloc[i] > 62))
            and struct_ok_short
        ):
            sell[i] = True
            scenario_id[i] = "S2_top"
            sl_p[i] = s_sl_s[i] if not np.isnan(s_sl_s[i]) else closes[i] + atr * 2
            tp_p[i] = s_tp_s[i] if not np.isnan(s_tp_s[i]) else closes[i] - atr * 3
            continue

        # S4 — corrective C buy
        if (
            recent(s_corr_bull, i, 48)
            and not recent(s_box_broken, i, 8)
            and macd_pullback_bull
            and cardwell_trend_long_ok
            and entry_ult_long_ok
            and (e_long_trig or e_pre_buy)
            and struct_ok_long
        ):
            buy[i] = True
            scenario_id[i] = "S4_pullback_long"
            sl_p[i] = s_sl_l[i] if not np.isnan(s_sl_l[i]) else closes[i] - atr * 1.5
            tp_p[i] = s_tp_l[i] if not np.isnan(s_tp_l[i]) else closes[i] + atr * 4
            continue

        # S5 — corrective C sell
        if (
            recent(s_corr_bear, i, 48)
            and not recent(s_box_broken, i, 8)
            and macd_pullback_bear
            and cardwell_trend_short_ok
            and entry_ult_short_ok
            and (e_short_trig or e_pre_sell)
            and struct_ok_short
        ):
            sell[i] = True
            scenario_id[i] = "S5_pullback_short"
            sl_p[i] = s_sl_s[i] if not np.isnan(s_sl_s[i]) else closes[i] + atr * 1.5
            tp_p[i] = s_tp_s[i] if not np.isnan(s_tp_s[i]) else closes[i] - atr * 4
            continue

        # S3 — wave 3 buy
        if (
            recent(s_wave3, i, 48)
            and macd_wave3_confirm
            and cardwell_trend_long_ok
            and entry_ult_long_ok
            and (e_long_trig or (e_pre_buy and e_break))
            and struct_ok_long
        ):
            buy[i] = True
            scenario_id[i] = "S3_wave3"
            sl_p[i] = s_sl_l[i] if not np.isnan(s_sl_l[i]) else closes[i] - atr * 2
            tp_p[i] = s_tp_l[i] if not np.isnan(s_tp_l[i]) else closes[i] + atr * 3.2
            continue

    entry["buy"] = buy
    entry["sell"] = sell
    entry["sl_price"] = sl_p
    entry["tp_price"] = tp_p
    entry["scenario"] = scenario_id
    entry["structure_tf"] = structure_tf
    return entry
