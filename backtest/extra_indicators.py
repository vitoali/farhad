"""Additional indicator ports (#20+) for batch backtesting."""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import atr_wilder, crossover, crossunder, ema, rsi, sma
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
