"""Additional indicator ports (#20+) for batch backtesting."""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import atr_wilder, crossover, crossunder, ema, rsi, sma, true_range
from zone_engine import pivot_high, pivot_low
from zone_engine import ZoneSignal, signals_to_df
from zone_indicators import _htf_ema_series


def _signal_df(df: pd.DataFrame, buy: np.ndarray, sell: np.ndarray) -> pd.DataFrame:
    out = df.copy()
    out["buy"] = buy
    out["sell"] = sell
    return out


def _zone_df(df: pd.DataFrame, signals: list[ZoneSignal]) -> pd.DataFrame:
    return signals_to_df(df, signals)


# ---------------------------------------------------------------------------
# #20 Cardwell RSI Trade Navigator
# ---------------------------------------------------------------------------

def cardwell_rsi_signals(
    df: pd.DataFrame,
    rsi_len: int = 14,
    rma_fast_len: int = 9,
    rma_slow_len: int = 45,
    atr_len: int = 14,
    atr_mult_sl: float = 1.5,
    tp_rr: float = 1.0,
) -> pd.DataFrame:
    out = df.copy()
    rsi_v = rsi(out["close"], rsi_len)
    rma_fast = rsi_v.ewm(alpha=1 / rma_fast_len, adjust=False).mean()
    rma_slow = rsi_v.ewm(alpha=1 / rma_slow_len, adjust=False).mean()
    atr_v = atr_wilder(out, atr_len).values
    closes = out["close"].values
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    rf, rs = rma_fast.values, rma_slow.values
    for i in range(2, n):
        bull = rf[i - 1] > rs[i - 1] and rf[i - 2] <= rs[i - 2]
        bear = rf[i - 1] < rs[i - 1] and rf[i - 2] >= rs[i - 2]
        a = atr_v[i - 1] if not np.isnan(atr_v[i - 1]) else closes[i] * 0.01
        entry = closes[i - 1]
        if bull:
            buy[i] = True
            risk = a * atr_mult_sl
            sl_p[i] = entry - risk
            tp_p[i] = entry + risk * tp_rr
        elif bear:
            sell[i] = True
            risk = a * atr_mult_sl
            sl_p[i] = entry + risk
            tp_p[i] = entry - risk * tp_rr
    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = out["close"].shift(1)
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    return out


# ---------------------------------------------------------------------------
# #21 FVG Retest Entry Engine (simplified classic sync)
# ---------------------------------------------------------------------------

def fvg_retest_signals(
    df: pd.DataFrame,
    structure_len: int = 5,
    min_fvg_atr: float = 0.10,
    max_fvg_age: int = 150,
    max_bars_wait: int = 30,
    min_retest_delay: int = 1,
    tp_rr: float = 1.0,
    sl_buffer_atr: float = 0.15,
) -> pd.DataFrame:
    out = df.copy()
    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    n = len(out)
    ph = pivot_high(out["high"], structure_len, structure_len).values
    pl = pivot_low(out["low"], structure_len, structure_len).values
    roll_hi = pd.Series(highs).rolling(structure_len * 2 + 1).max().shift(1).values
    roll_lo = pd.Series(lows).rolling(structure_len * 2 + 1).min().shift(1).values
    signals: list[ZoneSignal] = []
    fvgs: list[dict] = []
    armed: dict | None = None

    for i in range(structure_len * 2 + 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else closes[i] * 0.005
        fvgs = [f for f in fvgs if i - f["birth"] <= max_fvg_age]
        if i >= 2:
            if lows[i] > highs[i - 2]:
                gap = lows[i] - highs[i - 2]
                if gap >= a * min_fvg_atr:
                    fvgs.append({"dir": 1, "top": lows[i], "bot": highs[i - 2], "birth": i})
            if highs[i] < lows[i - 2]:
                gap = lows[i - 2] - highs[i]
                if gap >= a * min_fvg_atr:
                    fvgs.append({"dir": -1, "top": lows[i - 2], "bot": highs[i], "birth": i})

        bull_break = closes[i] > roll_hi[i] if not np.isnan(roll_hi[i]) else False
        bear_break = closes[i] < roll_lo[i] if not np.isnan(roll_lo[i]) else False
        if armed and i - armed["break_bar"] > max_bars_wait:
            armed = None
        if armed and ((armed["dir"] == 1 and closes[i] < armed["bot"]) or (armed["dir"] == -1 and closes[i] > armed["top"])):
            armed = None

        if not armed and bull_break:
            cands = [f for f in fvgs if f["dir"] == 1 and i - f["birth"] <= 30]
            if cands:
                armed = {**cands[-1], "break_bar": i, "dir": 1}
        elif not armed and bear_break:
            cands = [f for f in fvgs if f["dir"] == -1 and i - f["birth"] <= 30]
            if cands:
                armed = {**cands[-1], "break_bar": i, "dir": -1}

        if armed and i - armed["break_bar"] >= min_retest_delay and i > armed["birth"]:
            tol = closes[i] * 0.00025
            if armed["dir"] == 1:
                touched = lows[i] <= armed["top"] + tol and closes[i] > armed["top"] and closes[i] > opens[i]
            else:
                touched = highs[i] >= armed["bot"] - tol and closes[i] < armed["bot"] and closes[i] < opens[i]
            if touched:
                entry = closes[i]
                if armed["dir"] == 1:
                    sl = armed["bot"] - a * sl_buffer_atr
                    risk = max(entry - sl, entry * 0.01)
                    signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
                else:
                    sl = armed["top"] + a * sl_buffer_atr
                    risk = max(sl - entry, entry * 0.01)
                    signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
                armed = None
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #22 Stop Hunt Radar (reclaim events)
# ---------------------------------------------------------------------------

def stop_hunt_signals(
    df: pd.DataFrame,
    left_bars: int = 8,
    right_bars: int = 3,
    pen_mult: float = 0.05,
    conf_mult: float = 0.50,
    tp_rr: float = 2.0,
) -> pd.DataFrame:
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 100).values
    n = len(out)
    ph = pivot_high(out["high"], left_bars, right_bars).values
    pl = pivot_low(out["low"], left_bars, right_bars).values
    signals: list[ZoneSignal] = []
    pools: list[dict] = []

    for i in range(left_bars + right_bars + 1, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else (highs[i] - lows[i])
        min_pen = a * pen_mult
        if not np.isnan(pl[i]):
            pools.append({"side": 1, "level": lows[i - right_bars], "phase": 1, "ext": lows[i - right_bars], "born": i})
        if not np.isnan(ph[i]):
            pools.append({"side": -1, "level": highs[i - right_bars], "phase": 1, "ext": highs[i - right_bars], "born": i})
        pools = pools[-12:]
        keep = []
        for p in pools:
            lvl = p["level"]
            if p["phase"] == 1:
                swept = (p["side"] == 1 and lows[i] < lvl - min_pen and closes[i] > lvl) or (
                    p["side"] == -1 and highs[i] > lvl + min_pen and closes[i] < lvl
                )
                if swept:
                    p["phase"] = 2
                    p["ext"] = lows[i] if p["side"] == 1 else highs[i]
                    p["sweep_bar"] = i
            elif p["phase"] == 2:
                p["ext"] = min(p["ext"], lows[i]) if p["side"] == 1 else max(p["ext"], highs[i])
                reclaimed = (p["side"] == 1 and closes[i] > lvl + conf_mult * a) or (
                    p["side"] == -1 and closes[i] < lvl - conf_mult * a
                )
                if reclaimed:
                    entry = closes[i]
                    if p["side"] == 1:
                        sl = p["ext"] - a * 0.05
                        risk = max(entry - sl, a * 0.25)
                        signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
                    else:
                        sl = p["ext"] + a * 0.05
                        risk = max(sl - entry, a * 0.25)
                        signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
                    continue
                if i - p.get("sweep_bar", i) > 30:
                    continue
            keep.append(p)
        pools = keep
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #23 Smart Money Structure (GainzAlgo momentum)
# ---------------------------------------------------------------------------

def smart_money_structure_signals(
    df: pd.DataFrame,
    min_signal_distance: int = 5,
    tp_atr: float = 2.0,
    sl_atr: float = 1.5,
) -> pd.DataFrame:
    out = df.copy()
    closes, highs, lows, opens = out["close"].values, out["high"].values, out["low"].values, out["open"].values
    vol = out["volume"].values if "volume" in out.columns else np.ones(len(out))
    atr_v = atr_wilder(out, 14).values
    ema30 = ema(out["close"], 30).values
    ema100 = ema(out["close"], 100).values
    vol_avg = sma(out["volume"], 50).values if "volume" in out.columns else np.ones(len(out))
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    last_sig = -99
    highest_br = pd.Series(highs).rolling(5).max().shift(1).values
    lowest_br = pd.Series(lows).rolling(5).min().shift(1).values

    for i in range(101, n):
        if i - last_sig < min_signal_distance:
            continue
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.01
        mom = (closes[i] - closes[i - 1]) / closes[i - 1] * 100
        thresh = 0.01 * (1 + (a / closes[i]) * 2)
        bull_trend = ema30[i] > ema100[i]
        bear_trend = ema30[i] < ema100[i]
        vol_ok = vol[i] > vol_avg[i] if not np.isnan(vol_avg[i]) else True
        buy_ok = mom > thresh and bull_trend and vol_ok and closes[i] > highest_br[i]
        sell_ok = mom < -thresh and bear_trend and vol_ok and closes[i] < lowest_br[i]
        if buy_ok:
            buy[i] = True
            sl_p[i] = lows[i] - a * sl_atr
            tp_p[i] = closes[i] + a * tp_atr
            last_sig = i
        elif sell_ok:
            sell[i] = True
            sl_p[i] = highs[i] + a * sl_atr
            tp_p[i] = closes[i] - a * tp_atr
            last_sig = i
    out["buy"] = buy
    out["sell"] = sell
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    return out


# ---------------------------------------------------------------------------
# #24 SMC PRO Confluence (979a variant)
# ---------------------------------------------------------------------------

def smc_pro_alt_signals(
    df: pd.DataFrame,
    pivot_len: int = 5,
    tp_rr: float = 2.0,
) -> pd.DataFrame:
    """OB touch + discount/premium filter."""
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    bull_obs: list[dict] = []
    bear_obs: list[dict] = []
    last_ph = last_pl = np.nan

    for i in range(pivot_len * 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.01
        if not np.isnan(ph[i]):
            last_ph = highs[i - pivot_len]
        if not np.isnan(pl[i]):
            last_pl = lows[i - pivot_len]
            bull_obs.append({"top": last_pl + a * 0.5, "bot": last_pl, "bar": i})
        if not np.isnan(ph[i]):
            bear_obs.append({"top": last_ph, "bot": last_ph - a * 0.5, "bar": i})
        bull_obs = [z for z in bull_obs if i - z["bar"] < 200][-20:]
        bear_obs = [z for z in bear_obs if i - z["bar"] < 200][-20:]
        pd_mid = (last_ph + last_pl) / 2 if not np.isnan(last_ph) and not np.isnan(last_pl) else np.nan
        for z in bull_obs:
            if lows[i] <= z["top"] and closes[i] > z["bot"] and (np.isnan(pd_mid) or closes[i] < pd_mid):
                entry = closes[i]
                sl = z["bot"] - a * 0.1
                risk = max(entry - sl, a * 0.3)
                signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
                break
        for z in bear_obs:
            if highs[i] >= z["bot"] and closes[i] < z["top"] and (np.isnan(pd_mid) or closes[i] > pd_mid):
                entry = closes[i]
                sl = z["top"] + a * 0.1
                risk = max(sl - entry, a * 0.3)
                signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
                break
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #25 OrderFlow FVG Matrix MTF
# ---------------------------------------------------------------------------

def matrix_fvg_signals(
    df: pd.DataFrame,
    min_gap_atr: float = 0.15,
    tp_rr: float = 1.5,
) -> pd.DataFrame:
    """New bullish/bearish FVG formation as entry (simplified)."""
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    n = len(out)
    signals: list[ZoneSignal] = []
    for i in range(2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if lows[i] > highs[i - 2]:
            gap = lows[i] - highs[i - 2]
            if gap >= a * min_gap_atr:
                entry = closes[i]
                sl = highs[i - 2] - a * 0.1
                risk = max(entry - sl, a * 0.25)
                signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
        if highs[i] < lows[i - 2]:
            gap = lows[i - 2] - highs[i]
            if gap >= a * min_gap_atr:
                entry = closes[i]
                sl = lows[i - 2] + a * 0.1
                risk = max(sl - entry, a * 0.25)
                signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #26 PUT/CALL VP Levels
# ---------------------------------------------------------------------------

def put_call_vp_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    bull = out["close"] > out["open"]
    hl2 = (out["high"] + out["low"]) / 2
    buy = bull & (hl2 > out["high"].shift(1))
    sell = (~bull) & (hl2 < out["low"].shift(1))
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


# ---------------------------------------------------------------------------
# #27 Ranked Order Block touch
# ---------------------------------------------------------------------------

def ranked_ob_signals(
    df: pd.DataFrame,
    pivot_len: int = 5,
    tp_rr: float = 2.0,
) -> pd.DataFrame:
    return smc_pro_alt_signals(df, pivot_len=pivot_len, tp_rr=tp_rr)


# ---------------------------------------------------------------------------
# #28 QQE signals (simplified)
# ---------------------------------------------------------------------------

def qqe_signals(df: pd.DataFrame, rsi_len: int = 14, sf: int = 5) -> pd.DataFrame:
    out = df.copy()
    rsi_v = rsi(out["close"], rsi_len)
    rsi_ma = ema(rsi_v, sf)
    trail = rsi_ma.copy()
    buy = crossover(rsi_ma, pd.Series(50, index=out.index)).fillna(False).values
    sell = crossunder(rsi_ma, pd.Series(50, index=out.index)).fillna(False).values
    return _signal_df(out, buy, sell)


# ---------------------------------------------------------------------------
# #29 MACD MTF crossover
# ---------------------------------------------------------------------------

def macd_mtf_signals(df: pd.DataFrame, fast: int = 12, slow: int = 26, sig: int = 9) -> pd.DataFrame:
    out = df.copy()
    ema_f = ema(out["close"], fast)
    ema_s = ema(out["close"], slow)
    macd = ema_f - ema_s
    signal = ema(macd, sig)
    buy = crossover(macd, signal).fillna(False).values
    sell = crossunder(macd, signal).fillna(False).values
    return _signal_df(out, buy, sell)


# ---------------------------------------------------------------------------
# #30 Power Order Blocks (retest)
# ---------------------------------------------------------------------------

def power_ob_signals(df: pd.DataFrame, pivot_len: int = 10, tp_rr: float = 2.0) -> pd.DataFrame:
    return ranked_ob_signals(df, pivot_len=pivot_len, tp_rr=tp_rr)


# ---------------------------------------------------------------------------
# #31 Support/Resistance Break (LuxAlgo)
# ---------------------------------------------------------------------------

def sr_breaks_signals(df: pd.DataFrame, pivot_len: int = 15, vol_thresh: int = 20) -> pd.DataFrame:
    out = df.copy()
    ph = pivot_high(out["high"], pivot_len, pivot_len)
    pl = pivot_low(out["low"], pivot_len, pivot_len)
    vol_short = ema(out["volume"], 5)
    vol_long = ema(out["volume"], 10)
    osc = 100 * (vol_short - vol_long) / vol_long.replace(0, np.nan)
    low_pivot = pl.ffill()
    high_pivot = ph.ffill()
    buy = crossover(out["close"], high_pivot) & (osc > vol_thresh)
    sell = crossunder(out["close"], low_pivot) & (osc > vol_thresh)
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


# ---------------------------------------------------------------------------
# #32 Liquidity Pools touch (LuxAlgo simplified)
# ---------------------------------------------------------------------------

def liquidity_pool_signals(df: pd.DataFrame, contact_num: int = 2, tp_rr: float = 2.0) -> pd.DataFrame:
    """Simplified: pivot wick zones with N touches -> fade entry."""
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    n = len(out)
    signals: list[ZoneSignal] = []
    bull_zones: list[dict] = []
    bear_zones: list[dict] = []
    ph = pivot_high(out["high"], 5, 5).values
    pl = pivot_low(out["low"], 5, 5).values
    for i in range(15, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if not np.isnan(pl[i]):
            bull_zones.append({"level": lows[i - 5], "touches": 0, "bar": i})
        if not np.isnan(ph[i]):
            bear_zones.append({"level": highs[i - 5], "touches": 0, "bar": i})
        bull_zones = bull_zones[-10:]
        bear_zones = bear_zones[-10:]
        for z in bull_zones:
            if abs(lows[i] - z["level"]) < a * 0.3:
                z["touches"] += 1
            if z["touches"] >= contact_num and lows[i] <= z["level"] + a * 0.1 and closes[i] > z["level"]:
                entry = closes[i]
                sl = z["level"] - a * 0.2
                risk = max(entry - sl, a * 0.25)
                signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
                z["touches"] = 0
        for z in bear_zones:
            if abs(highs[i] - z["level"]) < a * 0.3:
                z["touches"] += 1
            if z["touches"] >= contact_num and highs[i] >= z["level"] - a * 0.1 and closes[i] < z["level"]:
                entry = closes[i]
                sl = z["level"] + a * 0.2
                risk = max(sl - entry, a * 0.25)
                signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
                z["touches"] = 0
    return _zone_df(out, signals)


def slingshot_signals(df: pd.DataFrame, fast: int = 38, slow: int = 62) -> pd.DataFrame:
    out = df.copy()
    ema_f = ema(out["close"], fast)
    ema_s = ema(out["close"], slow)
    buy = (ema_f > ema_s) & (out["close"].shift(1) < ema_f) & (out["close"] > ema_f)
    sell = (ema_f < ema_s) & (out["close"].shift(1) > ema_f) & (out["close"] < ema_f)
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


def ichimoku_ml_signals(df: pd.DataFrame, threshold: float = 0.55, disp: int = 26) -> pd.DataFrame:
    out = df.copy()
    hl2 = (out["high"] + out["low"]) / 2
    tenkan = ema(hl2, 9)
    kijun = ema(hl2, 26)
    senkou_a = ema((tenkan + kijun) / 2, 26)
    senkou_b = ema(hl2, 52)
    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1).shift(disp)
    cloud_bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1).shift(disp)
    rsi_norm = (rsi(out["close"], 14) - 50) / 25
    prob = 1 / (1 + np.exp(-rsi_norm.abs()))
    cross_above = (out["close"] > cloud_top) & (out["close"].shift(1) <= cloud_top.shift(1))
    cross_below = (out["close"] < cloud_bot) & (out["close"].shift(1) >= cloud_bot.shift(1))
    buy = cross_above & (prob >= threshold)
    sell = cross_below & (prob >= threshold)
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


def liquidity_shift_signals(
    df: pd.DataFrame, pivot_len: int = 5, disp_mult: float = 1.0, tp_rr: float = 2.0,
) -> pd.DataFrame:
    out = df.copy()
    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    swing_hi = swing_lo = np.nan
    bull_pending = bear_pending = False
    bull_level = bear_level = 0.0
    bull_bar = bear_bar = 0

    for i in range(pivot_len * 2 + 1, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else max(highs[i] - lows[i], 1e-8)
        body = abs(closes[i] - opens[i])
        if not np.isnan(ph[i]):
            swing_hi = highs[i - pivot_len]
        if not np.isnan(pl[i]):
            swing_lo = lows[i - pivot_len]
        if not np.isnan(swing_lo) and lows[i] < swing_lo and closes[i] > swing_lo:
            bull_pending, bull_level, bull_bar = True, swing_lo, i
        if not np.isnan(swing_hi) and highs[i] > swing_hi and closes[i] < swing_hi:
            bear_pending, bear_level, bear_bar = True, swing_hi, i
        if bull_pending and i - bull_bar > 100:
            bull_pending = False
        if bear_pending and i - bear_bar > 100:
            bear_pending = False
        bull_ok = bull_pending and ((not np.isnan(swing_hi) and closes[i] > swing_hi) or (closes[i] > opens[i] and body >= a * disp_mult))
        bear_ok = bear_pending and ((not np.isnan(swing_lo) and closes[i] < swing_lo) or (closes[i] < opens[i] and body >= a * disp_mult))
        if bull_ok:
            entry = closes[i]
            sl = bull_level - a * 0.15
            risk = max(entry - sl, a * 0.3)
            signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
            bull_pending = False
        if bear_ok:
            entry = closes[i]
            sl = bear_level + a * 0.15
            risk = max(sl - entry, a * 0.3)
            signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
            bear_pending = False
    return _zone_df(out, signals)


def cm_ma_mtf_signals(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    out = df.copy()
    buy = crossover(ema(out["close"], fast), ema(out["close"], slow))
    sell = crossunder(ema(out["close"], fast), ema(out["close"], slow))
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


def fxpip_scob_signals(df: pd.DataFrame) -> pd.DataFrame:
    """FxPipFinder Single Candle Order Block pattern."""
    out = df.copy()
    o, h, l, c = out["open"], out["high"], out["low"], out["close"]
    bull = (o.shift(2) > c.shift(2)) & (c.shift(1) > o.shift(1)) & (c > o) & (l.shift(1) < l.shift(2)) & (c > h.shift(1))
    bear = (o.shift(2) < c.shift(2)) & (c.shift(1) < o.shift(1)) & (c < o) & (h.shift(1) > h.shift(2)) & (c < l.shift(1))
    return _signal_df(out, bull.fillna(False).values, bear.fillna(False).values)


def buyside_liquidity_signals(df: pd.DataFrame, pivot_len: int = 10, tp_rr: float = 2.0) -> pd.DataFrame:
    """LuxAlgo BSL/SSL breach — SSL taken then reclaim long, BSL taken then reclaim short."""
    return stop_hunt_signals(df, left_bars=pivot_len, right_bars=3, tp_rr=tp_rr)


def sr_signals_mtf_signals(df: pd.DataFrame, lookback: int = 20, tp_rr: float = 2.0) -> pd.DataFrame:
    """S/R breakout + zone retest (LuxAlgo SR Signals simplified)."""
    out = df.copy()
    highs, lows, closes, opens = out["high"].values, out["low"].values, out["close"].values, out["open"].values
    atr_v = atr_wilder(out, 14).values
    n = len(out)
    signals: list[ZoneSignal] = []
    res_hi = pd.Series(highs).rolling(lookback).max().shift(1).values
    sup_lo = pd.Series(lows).rolling(lookback).min().shift(1).values
    zones: list[dict] = []

    for i in range(lookback + 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if closes[i] > res_hi[i]:
            zones.append({"type": "res", "top": highs[i], "bot": res_hi[i], "bar": i})
        if closes[i] < sup_lo[i]:
            zones.append({"type": "sup", "top": sup_lo[i], "bot": lows[i], "bar": i})
        zones = zones[-15:]
        for z in zones:
            if z["type"] == "res" and opens[i] < z["bot"] and highs[i] > z["bot"] and closes[i] < z["bot"] and i > z["bar"] + 2:
                entry = closes[i]
                sl = z["top"] + a * 0.1
                risk = max(sl - entry, a * 0.3)
                signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
            if z["type"] == "sup" and opens[i] > z["top"] and lows[i] < z["top"] and closes[i] > z["top"] and i > z["bar"] + 2:
                entry = closes[i]
                sl = z["bot"] - a * 0.1
                risk = max(entry - sl, a * 0.3)
                signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
    return _zone_df(out, signals)


def divergence_signals(df: pd.DataFrame, rsi_len: int = 14, lookback: int = 5) -> pd.DataFrame:
    """Regular RSI divergence (simplified)."""
    out = df.copy()
    rsi_v = rsi(out["close"], rsi_len).values
    lows, highs, closes = out["low"].values, out["high"].values, out["close"].values
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    for i in range(lookback * 2 + 2, n):
        pl_now = lows[i] < min(lows[i - lookback : i])
        pl_prev = lows[i - lookback] < min(lows[i - lookback * 2 : i - lookback])
        if pl_now and pl_prev and lows[i] < lows[i - lookback] and rsi_v[i] > rsi_v[i - lookback]:
            buy[i] = True
        ph_now = highs[i] > max(highs[i - lookback : i])
        ph_prev = highs[i - lookback] > max(highs[i - lookback * 2 : i - lookback])
        if ph_now and ph_prev and highs[i] > highs[i - lookback] and rsi_v[i] < rsi_v[i - lookback]:
            sell[i] = True
    return _signal_df(out, buy, sell)


def orderflow_print_signals(df: pd.DataFrame, vol_mult: float = 2.0) -> pd.DataFrame:
    """OrderFlow absorption matrix — volume spike + direction."""
    out = df.copy()
    if "volume" not in out.columns:
        return _signal_df(out, np.zeros(len(out), bool), np.zeros(len(out), bool))
    vol_ma = sma(out["volume"], 20)
    spike = out["volume"] > vol_ma * vol_mult
    buy = spike & (out["close"] > out["open"])
    sell = spike & (out["close"] < out["open"])
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


def fair_value_gap_signals(df: pd.DataFrame, min_gap_atr: float = 0.1, tp_rr: float = 1.5) -> pd.DataFrame:
    """LuxAlgo FVG display -> formation entry (same as matrix_fvg)."""
    return matrix_fvg_signals(df, min_gap_atr=min_gap_atr, tp_rr=tp_rr)


# ---------------------------------------------------------------------------
# #44 Mirage LSP — liquidity sweep + immediate entry (mirage_d9ef.txt)
# ---------------------------------------------------------------------------

def mirage_lsp_signals(
    df: pd.DataFrame,
    swing_len: int = 5,
    lookback: int = 50,
    min_score: float = 0.3,
    sl_buf_atr: float = 0.25,
    tp1_r: float = 1.0,
) -> pd.DataFrame:
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], swing_len, swing_len).values
    pl = pivot_low(out["low"], swing_len, swing_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    lo_lvl: list[tuple[float, int]] = []
    hi_lvl: list[tuple[float, int]] = []
    lo_used: list[bool] = []
    hi_used: list[bool] = []

    for i in range(swing_len * 2 + 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else closes[i] * 0.005
        if not np.isnan(pl[i]):
            lo_lvl.append((lows[i - swing_len], i - swing_len))
            lo_used.append(False)
        if not np.isnan(ph[i]):
            hi_lvl.append((highs[i - swing_len], i - swing_len))
            hi_used.append(False)
        if len(lo_lvl) > 30:
            lo_lvl.pop(0)
            lo_used.pop(0)
        if len(hi_lvl) > 30:
            hi_lvl.pop(0)
            hi_used.pop(0)

        bull_q = bear_q = False
        anchor_lo = anchor_hi = np.nan
        for j in range(len(lo_lvl) - 1, -1, -1):
            if lo_used[j]:
                continue
            lvl, born = lo_lvl[j]
            if i - born > lookback:
                lo_used[j] = True
                continue
            if closes[i] < lvl:
                lo_used[j] = True
            elif lows[i] < lvl and closes[i] > lvl:
                lo_used[j] = True
                vol_comp = 1.0
                score = vol_comp * (1 - abs(closes[i] - lvl) / max(a, 1e-9) * 0.1)
                if score >= min_score:
                    bull_q = True
                    anchor_lo = lows[i]
                break
        for j in range(len(hi_lvl) - 1, -1, -1):
            if hi_used[j]:
                continue
            lvl, born = hi_lvl[j]
            if i - born > lookback:
                hi_used[j] = True
                continue
            if closes[i] > lvl:
                hi_used[j] = True
            elif highs[i] > lvl and closes[i] < lvl:
                hi_used[j] = True
                vol_comp = 1.0
                score = vol_comp * (1 - abs(closes[i] - lvl) / max(a, 1e-9) * 0.1)
                if score >= min_score:
                    bear_q = True
                    anchor_hi = highs[i]
                break

        if bull_q and not bear_q:
            entry = closes[i]
            sl = anchor_lo - a * sl_buf_atr
            risk = max(entry - sl, a * 0.5)
            signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp1_r))
        elif bear_q and not bull_q:
            entry = closes[i]
            sl = anchor_hi + a * sl_buf_atr
            risk = max(sl - entry, a * 0.5)
            signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp1_r))
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #45 TrendMaster Pro — filtered MA cross (4_7c06.txt)
# ---------------------------------------------------------------------------

def _adx_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(df)
    atr_s = pd.Series(tr, index=df.index).ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def trendmaster_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    short_ma = sma(out["close"], 9)
    long_ma = sma(out["close"], 21)
    buy_raw = crossover(short_ma, long_ma)
    sell_raw = crossunder(short_ma, long_ma)
    basis = sma(out["close"], 20)
    dev = out["close"].rolling(20).std()
    upper = basis + 2 * dev
    lower = basis - 2 * dev
    atr_bb = atr_wilder(out, 20)
    vol_filt = (upper - lower) > (atr_bb * 2)
    bb_long = out["close"] > basis
    bb_short = out["close"] < basis
    rsi_v = rsi(out["close"], 14)
    rsi_long = rsi_v > 55
    rsi_short = rsi_v < 45
    ema12 = ema(out["close"], 12)
    ema26 = ema(out["close"], 26)
    macd_line = ema12 - ema26
    macd_sig = ema(macd_line, 9)
    macd_long = macd_line > macd_sig
    macd_short = macd_line < macd_sig
    lo = out["low"].rolling(14).min()
    hi = out["high"].rolling(14).max()
    k = sma(100 * (out["close"] - lo) / (hi - lo).replace(0, np.nan), 3)
    stoch_long = k < 80
    stoch_short = k > 20
    adx_v = _adx_series(out, 14)
    adx_ok = adx_v > 25
    buy = buy_raw & vol_filt & bb_long & rsi_long & macd_long & stoch_long & adx_ok
    sell = sell_raw & vol_filt & bb_short & rsi_short & macd_short & stoch_short & adx_ok
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


# ---------------------------------------------------------------------------
# #46 PMax Explorer — MAvg/PMax crossover (3_2c7c.txt)
# ---------------------------------------------------------------------------

def _pmax_series(src: pd.Series, df: pd.DataFrame, length: int = 10, atr_len: int = 10, mult: float = 3.0) -> tuple[pd.Series, pd.Series]:
    mavg = ema(src, length)
    atr_v = atr_wilder(df, atr_len)
    n = len(df)
    pmax = np.full(n, np.nan)
    direction = np.ones(n, dtype=int)
    long_stop_prev = short_stop_prev = np.nan
    for i in range(n):
        ls = mavg.iloc[i] - mult * atr_v.iloc[i]
        ss = mavg.iloc[i] + mult * atr_v.iloc[i]
        if not np.isnan(long_stop_prev):
            ls = max(ls, long_stop_prev) if mavg.iloc[i] > long_stop_prev else ls
        if not np.isnan(short_stop_prev):
            ss = min(ss, short_stop_prev) if mavg.iloc[i] < short_stop_prev else ss
        if i > 0:
            if direction[i - 1] == -1 and mavg.iloc[i] > short_stop_prev:
                direction[i] = 1
            elif direction[i - 1] == 1 and mavg.iloc[i] < long_stop_prev:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]
        pmax[i] = ls if direction[i] == 1 else ss
        long_stop_prev = ls
        short_stop_prev = ss
    return mavg, pd.Series(pmax, index=df.index)


def pmax_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    src = (out["high"] + out["low"]) / 2
    mavg, pmax = _pmax_series(src, out)
    buy = crossover(mavg, pmax)
    sell = crossunder(mavg, pmax)
    return _signal_df(out, buy.fillna(False).values, sell.fillna(False).values)


# ---------------------------------------------------------------------------
# #47 Volume-Trend OB Retest (volon_trend_order_block_93f7.txt)
# ---------------------------------------------------------------------------

def volume_ob_retest_signals(
    df: pd.DataFrame,
    st_len: int = 50,
    st_mult: float = 3.5,
    pivot_len: int = 7,
    vol_pct: float = 0.5,
) -> pd.DataFrame:
    out = df.copy()
    if "volume" not in out.columns:
        return _signal_df(out, np.zeros(len(out), bool), np.zeros(len(out), bool))
    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    vol = out["volume"].values
    custom_atr = (out["high"] - out["low"]).rolling(st_len).mean().values
    hl2 = ((out["high"] + out["low"]) / 2).values
    n = len(out)
    market_trend = 1
    trend_stop = np.nan
    active_top = active_bot = np.nan
    active_buy_ratio = 0.5
    active_ob_trend = 0
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    signals: list[ZoneSignal] = []

    for i in range(st_len + pivot_len * 2, n):
        a = custom_atr[i] if not np.isnan(custom_atr[i]) else (highs[i] - lows[i])
        upper = hl2[i] + st_mult * a
        lower = hl2[i] - st_mult * a
        prev_stop = trend_stop if not np.isnan(trend_stop) else lower
        if market_trend == 1:
            trend_stop = max(lower, prev_stop)
        else:
            trend_stop = min(upper, prev_stop if not np.isnan(trend_stop) else upper)
        prev_trend = market_trend

        if i > 0 and closes[i] > trend_stop and closes[i - 1] <= trend_stop:
            market_trend = 1
            trend_stop = lower
        elif i > 0 and closes[i] < trend_stop and closes[i - 1] >= trend_stop:
            market_trend = -1
            trend_stop = upper

        if market_trend == 1 and not np.isnan(pl[i]):
            ob_top = min(opens[i - pivot_len], closes[i - pivot_len])
            ob_bot = ob_top - a
            buy_vol = sell_vol = 0.0
            for j in range(pivot_len + 1):
                if closes[i - j] >= opens[i - j]:
                    buy_vol += vol[i - j]
                else:
                    sell_vol += vol[i - j]
            total = buy_vol + sell_vol
            active_buy_ratio = buy_vol / total if total > 0 else 0.5
            active_top, active_bot, active_ob_trend = ob_top, ob_bot, 1
        if market_trend == -1 and not np.isnan(ph[i]):
            ob_bot = max(opens[i - pivot_len], closes[i - pivot_len])
            ob_top = ob_bot + a
            buy_vol = sell_vol = 0.0
            for j in range(pivot_len + 1):
                if closes[i - j] >= opens[i - j]:
                    buy_vol += vol[i - j]
                else:
                    sell_vol += vol[i - j]
            total = buy_vol + sell_vol
            active_buy_ratio = buy_vol / total if total > 0 else 0.5
            active_top, active_bot, active_ob_trend = ob_top, ob_bot, -1

        if not np.isnan(active_top) and not np.isnan(active_bot):
            broken = (active_ob_trend == 1 and highs[i] < active_bot) or (active_ob_trend == -1 and lows[i] > active_top)
            if broken:
                active_top = active_bot = np.nan
                active_ob_trend = 0

        market_change = i > 0 and market_trend != prev_trend
        sell_ratio = 1.0 - active_buy_ratio
        if (
            not np.isnan(active_top)
            and lows[i - 1] <= active_top
            and lows[i] > active_top
            and active_buy_ratio >= vol_pct
            and np.isnan(pl[i])
            and not market_change
        ):
            entry = closes[i]
            sl = active_bot - a * 0.1
            risk = max(entry - sl, a * 0.3)
            signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * 2.0))
        if (
            not np.isnan(active_bot)
            and highs[i - 1] >= active_bot
            and highs[i] < active_bot
            and sell_ratio >= vol_pct
            and np.isnan(ph[i])
            and not market_change
        ):
            entry = closes[i]
            sl = active_top + a * 0.1
            risk = max(sl - entry, a * 0.3)
            signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * 2.0))
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #48 Dynamic Trend Bands — VWAP break signals (dynamic_trend_125b.txt)
# ---------------------------------------------------------------------------

def dynamic_trend_signals(df: pd.DataFrame, lr_len: int = 50, atr_len: int = 100, atr_mult: float = 3.0, pivot_len: int = 10) -> pd.DataFrame:
    out = df.copy()
    if "volume" not in out.columns:
        out["volume"] = 1.0
    atr_v = atr_wilder(out, atr_len).values
    lr_center = ema(ema(out["close"], lr_len), lr_len).values
    upper = lr_center + atr_v * atr_mult
    lower = lr_center - atr_v * atr_mult
    closes, highs, lows, opens, vol = out["close"].values, out["high"].values, out["low"].values, out["open"].values, out["volume"].values
    n = len(out)
    trend_state = 0
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    vwap_anchor = 0
    cum_pv = cum_v = 0.0

    for i in range(max(lr_len, atr_len, pivot_len) + 2, n):
        if closes[i] > upper[i] and closes[i - 1] <= upper[i - 1]:
            trend_state = 1
        if closes[i] < lower[i] and closes[i - 1] >= lower[i - 1]:
            trend_state = -1
        lo_roll = lows[i - 1] == min(lows[i - pivot_len : i])
        hi_roll = highs[i - 1] == max(highs[i - pivot_len : i])
        if trend_state == -1 and lo_roll and lows[i] > lows[i - 1]:
            vwap_anchor = i - 1
            cum_pv = cum_v = 0.0
        if trend_state == 1 and hi_roll and highs[i] < highs[i - 1]:
            vwap_anchor = i - 1
            cum_pv = cum_v = 0.0
        if vwap_anchor > 0 and trend_state != 0:
            span = i - vwap_anchor
            cum_pv = cum_v = 0.0
            for j in range(span + 1):
                idx = i - j
                cum_pv += closes[idx] * vol[idx]
                cum_v += vol[idx]
            vwap_val = cum_pv / cum_v if cum_v > 0 else closes[i]
            if trend_state == 1 and closes[i] >= vwap_val:
                buy[i] = True
            if trend_state == -1 and closes[i] <= vwap_val:
                sell[i] = True
    return _signal_df(out, buy, sell)


# ---------------------------------------------------------------------------
# #49 Quantum Imbalance Trap (QUANTOM_4e3d.txt)
# ---------------------------------------------------------------------------

def quantum_imbalance_signals(
    df: pd.DataFrame,
    imb_len: int = 10,
    imb_thresh: float = 0.55,
    vol_mult: float = 1.2,
    sl_atr: float = 1.5,
    tp_r: float = 1.5,
) -> pd.DataFrame:
    out = df.copy()
    if "volume" not in out.columns:
        return _signal_df(out, np.zeros(len(out), bool), np.zeros(len(out), bool))
    atr_v = atr_wilder(out, 14).values
    vol_avg = sma(out["volume"], imb_len).values
    body = (out["close"] - out["open"]).abs().values
    rng = (out["high"] - out["low"]).values
    body_rat = np.where(rng > 0, body / rng, 0)
    vol_rat = np.where(vol_avg > 0, out["volume"].values / vol_avg, 1)
    mom_fast = sma(out["close"], 5).values
    mom_slow = sma(out["close"], imb_len * 2).values
    closes, opens = out["close"].values, out["open"].values
    n = len(out)
    signals: list[ZoneSignal] = []
    imb_bull = imb_bear = np.zeros(n, dtype=bool)
    for i in range(imb_len * 2 + 2, n):
        bull_body = closes[i] > opens[i]
        bear_body = closes[i] < opens[i]
        vol_spike = vol_rat[i] >= vol_mult
        bull_trend = mom_fast[i] > mom_slow[i]
        bear_trend = mom_fast[i] < mom_slow[i]
        imb_bull[i] = bull_body and body_rat[i] >= imb_thresh and vol_spike and bull_trend
        imb_bear[i] = bear_body and body_rat[i] >= imb_thresh and vol_spike and bear_trend
        sig_bull = imb_bull[i - 1] and not imb_bull[i - 2]
        sig_bear = imb_bear[i - 1] and not imb_bear[i - 2]
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if sig_bull:
            entry = closes[i]
            sl = entry - a * sl_atr
            signals.append(ZoneSignal(i, "long", entry, sl, entry + a * sl_atr * tp_r))
        if sig_bear:
            entry = closes[i]
            sl = entry + a * sl_atr
            signals.append(ZoneSignal(i, "short", entry, sl, entry - a * sl_atr * tp_r))
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #50 Multi-Divergence — RSI pivot divergence (multi_divergence_40f7.txt)
# ---------------------------------------------------------------------------

def multi_div_signals(df: pd.DataFrame, piv_len: int = 5, sl_atr: float = 1.5, tp_atr: float = 2.0) -> pd.DataFrame:
    out = df.copy()
    rsi_v = rsi(out["close"], 14).values
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    ph_p = pivot_high(out["high"], piv_len, piv_len).values
    pl_p = pivot_low(out["low"], piv_len, piv_len).values
    ph_r = pivot_high(pd.Series(rsi_v, index=out.index), piv_len, piv_len).values
    pl_r = pivot_low(pd.Series(rsi_v, index=out.index), piv_len, piv_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    pr_lo: list[float] = []
    pr_hi: list[float] = []
    r_lo: list[float] = []
    r_hi: list[float] = []

    for i in range(piv_len * 2 + 2, n):
        if not np.isnan(pl_p[i]):
            pr_lo.append(lows[i - piv_len])
            r_lo.append(rsi_v[i - piv_len])
            if len(pr_lo) > 2:
                pr_lo.pop(0)
                r_lo.pop(0)
        if not np.isnan(ph_p[i]):
            pr_hi.append(highs[i - piv_len])
            r_hi.append(rsi_v[i - piv_len])
            if len(pr_hi) > 2:
                pr_hi.pop(0)
                r_hi.pop(0)
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if len(pr_lo) >= 2 and len(r_lo) >= 2:
            if pr_lo[-1] < pr_lo[-2] and r_lo[-1] > r_lo[-2]:
                entry = closes[i]
                sl = entry - a * sl_atr
                signals.append(ZoneSignal(i, "long", entry, sl, entry + a * tp_atr))
        if len(pr_hi) >= 2 and len(r_hi) >= 2:
            if pr_hi[-1] > pr_hi[-2] and r_hi[-1] < r_hi[-2]:
                entry = closes[i]
                sl = entry + a * sl_atr
                signals.append(ZoneSignal(i, "short", entry, sl, entry - a * tp_atr))
    return _zone_df(out, signals)


# ---------------------------------------------------------------------------
# #51 KNN Pivot ML (MACHIN_6545.txt)
# ---------------------------------------------------------------------------

def knn_pivot_signals(df: pd.DataFrame, pivot_len: int = 10, window: int = 20, k: int = 2) -> pd.DataFrame:
    out = df.copy()
    closes = out["close"].values
    highs, lows = out["high"].values, out["low"].values
    n = len(out)
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    hi_slopes: list[float] = []
    lo_slopes: list[float] = []
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    prev_class = "Neutral"

    def rolling_slope(src: np.ndarray, end: int, length: int) -> float:
        if end < length:
            return 0.0
        y0 = np.mean(src[end - length + 1 : end + 1])
        y1 = np.mean(src[end - length : end])
        return y0 - y1

    def knn_dist(cur: float, hist: list[float]) -> float:
        if not hist:
            return 1e6
        dists = sorted(abs(cur - h) for h in hist)
        kk = min(k, len(dists))
        return sum(dists[:kk]) / kk

    for i in range(pivot_len * 2 + window, n):
        if not np.isnan(ph[i]):
            hi_slopes.append(rolling_slope(highs, i - pivot_len, window))
        if not np.isnan(pl[i]):
            lo_slopes.append(rolling_slope(lows, i - pivot_len, window))
        hi_slopes = hi_slopes[-50:]
        lo_slopes = lo_slopes[-50:]
        cur_slope = rolling_slope(closes, i, window)
        d_hi = knn_dist(cur_slope, hi_slopes)
        d_lo = knn_dist(cur_slope, lo_slopes)
        if d_hi < d_lo:
            knn_class = "Approaching Pivot High"
        elif d_lo < d_hi:
            knn_class = "Approaching Pivot Low"
        else:
            knn_class = "Neutral"
        if prev_class == "Neutral" and knn_class == "Approaching Pivot Low":
            buy[i] = True
        if prev_class == "Neutral" and knn_class == "Approaching Pivot High":
            sell[i] = True
        prev_class = knn_class
    return _signal_df(out, buy, sell)


# ---------------------------------------------------------------------------
# #52 High-Volume Pivot S/R (high_volom_pivoty_suport_809e.txt)
# ---------------------------------------------------------------------------

def hv_pivot_sr_signals(df: pd.DataFrame, sup_len: int = 10, tp_rr: float = 2.0) -> pd.DataFrame:
    out = df.copy()
    highs, lows, closes, opens = out["high"].values, out["low"].values, out["close"].values, out["open"].values
    atr_v = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], sup_len, sup_len).values
    pl = pivot_low(out["low"], sup_len, sup_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    res_top = res_bot = sup_top = sup_bot = np.nan
    res_broken = sup_broken = False

    for i in range(sup_len * 2 + 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if not np.isnan(ph[i]):
            body_top = max(opens[i - sup_len], closes[i - sup_len])
            res_top = body_top
            res_bot = body_top - a
            res_broken = False
        if not np.isnan(pl[i]):
            body_bot = min(opens[i - sup_len], closes[i - sup_len])
            sup_top = body_bot
            sup_bot = body_bot - a
            sup_broken = False
        if not np.isnan(res_top) and closes[i] > res_top and not res_broken:
            entry = closes[i]
            sl = res_bot - a * 0.1
            risk = max(entry - sl, a * 0.3)
            signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
            res_broken = True
        if not np.isnan(sup_bot) and closes[i] < sup_bot and not sup_broken:
            entry = closes[i]
            sl = sup_top + a * 0.1
            risk = max(sl - entry, a * 0.3)
            signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
            sup_broken = True
        if not np.isnan(sup_top) and opens[i] > sup_top and lows[i] < sup_top and closes[i] > sup_top and i > sup_len + 2:
            entry = closes[i]
            sl = sup_bot - a * 0.1
            risk = max(entry - sl, a * 0.3)
            signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
        if not np.isnan(res_bot) and opens[i] < res_bot and highs[i] > res_bot and closes[i] < res_bot and i > sup_len + 2:
            entry = closes[i]
            sl = res_top + a * 0.1
            risk = max(sl - entry, a * 0.3)
            signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
    return _zone_df(out, signals)


def fib_ote_signals(df: pd.DataFrame, pivot_len: int = 10, tp_rr: float = 2.0) -> pd.DataFrame:
    """Smart Money Fib OTE — entry on 0.618-0.786 retrace after BOS."""
    out = df.copy()
    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    atr_v = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    n = len(out)
    signals: list[ZoneSignal] = []
    trend = 0
    swing_hi = swing_lo = np.nan

    for i in range(pivot_len * 2, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) else closes[i] * 0.005
        if not np.isnan(ph[i]):
            swing_hi = highs[i - pivot_len]
            if trend <= 0 and closes[i] > swing_hi:
                trend = 1
        if not np.isnan(pl[i]):
            swing_lo = lows[i - pivot_len]
            if trend >= 0 and closes[i] < swing_lo:
                trend = -1
        if trend == 1 and not np.isnan(swing_hi) and not np.isnan(swing_lo):
            rng = swing_hi - swing_lo
            ote_top = swing_hi - rng * 0.618
            ote_bot = swing_hi - rng * 0.786
            if lows[i] <= ote_top and closes[i] >= ote_bot:
                entry = closes[i]
                sl = swing_lo - a * 0.1
                risk = max(entry - sl, a * 0.3)
                signals.append(ZoneSignal(i, "long", entry, sl, entry + risk * tp_rr))
        if trend == -1 and not np.isnan(swing_hi) and not np.isnan(swing_lo):
            rng = swing_hi - swing_lo
            ote_bot = swing_lo + rng * 0.618
            ote_top = swing_lo + rng * 0.786
            if highs[i] >= ote_bot and closes[i] <= ote_top:
                entry = closes[i]
                sl = swing_hi + a * 0.1
                risk = max(sl - entry, a * 0.3)
                signals.append(ZoneSignal(i, "short", entry, sl, entry - risk * tp_rr))
    return _zone_df(out, signals)
