"""Zone / SMC / trend indicator ports for offline backtest."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import atr_wilder, crossover, crossunder, ema, mfi, rsi, sma, true_range
from zone_engine import ZoneSignal, htf_ema_bias, pivot_high, pivot_low, signals_to_df


# ---------------------------------------------------------------------------
# #10 IFVG Sniper Entry Engine
# ---------------------------------------------------------------------------

@dataclass
class HiddenFVG:
    top: float
    bot: float
    direction: int  # 1 bull fvg, -1 bear fvg
    age: int
    gap_atr: float
    body_ratio: float
    range_atr: float


def ifvg_signals(
    df: pd.DataFrame,
    max_hidden: int = 120,
    max_age: int = 60,
    filter_mode: str = "Balanced",
    sl_atr_mult: float = 1.5,
    tp_rr: float = 3.0,
    one_trade_at_a_time: bool = True,
) -> pd.DataFrame:
    """Core IFVG: hidden FVG memory -> inversion -> entry with ATR SL + RR TP."""
    out = df.copy()
    atr_v = atr_wilder(out, 14).values
    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    n = len(out)
    hidden: list[HiddenFVG] = []
    signals: list[ZoneSignal] = []
    trade_active = False

    min_gap_atr = {"Off": 0.0, "Loose": 0.15, "Balanced": 0.25, "Strict": 0.40}.get(filter_mode, 0.25)
    min_body = {"Off": 0.0, "Loose": 0.40, "Balanced": 0.50, "Strict": 0.60}.get(filter_mode, 0.50)
    min_range = {"Off": 0.0, "Loose": 0.40, "Balanced": 0.60, "Strict": 0.85}.get(filter_mode, 0.60)
    break_buf = {"Off": 0.0, "Loose": 0.0, "Balanced": 0.05, "Strict": 0.10}.get(filter_mode, 0.05)

    for i in range(n):
        safe_atr = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else 1e-8
        for h in hidden:
            h.age += 1
        hidden = [h for h in hidden if h.age <= max_age]

        candle_range = max(highs[i] - lows[i], 1e-8)
        body_ratio = abs(closes[i] - opens[i]) / candle_range
        range_atr = candle_range / safe_atr

        if i >= 2:
            if lows[i] > highs[i - 2]:
                gap = lows[i] - highs[i - 2]
                hidden.append(
                    HiddenFVG(lows[i], highs[i - 2], 1, 0, gap / safe_atr, body_ratio, range_atr)
                )
            if highs[i] < lows[i - 2]:
                gap = lows[i - 2] - highs[i]
                hidden.append(
                    HiddenFVG(lows[i - 2], highs[i], -1, 0, gap / safe_atr, body_ratio, range_atr)
                )
        while len(hidden) > max_hidden:
            hidden.pop(0)

        new_dir = 0
        new_top = new_bot = 0.0
        for h in reversed(hidden):
            buf = safe_atr * break_buf
            bull_inv = h.direction == -1 and closes[i] > h.top + buf
            bear_inv = h.direction == 1 and closes[i] < h.bot - buf
            if bull_inv or bear_inv:
                ok = filter_mode == "Off" or (
                    h.gap_atr >= min_gap_atr and h.body_ratio >= min_body and h.range_atr >= min_range
                )
                if ok:
                    new_dir = 1 if bull_inv else -1
                    new_top, new_bot = h.top, h.bot
                    hidden.remove(h)
                break

        if new_dir != 0:
            if one_trade_at_a_time and trade_active:
                continue
            entry = new_top if new_dir == 1 else new_bot
            risk = safe_atr * sl_atr_mult
            sl = entry - risk if new_dir == 1 else entry + risk
            tp = entry + risk * tp_rr if new_dir == 1 else entry - risk * tp_rr
            signals.append(
                ZoneSignal(i, "long" if new_dir == 1 else "short", entry, sl, tp, meta="ifvg_inversion")
            )
            trade_active = True

        if trade_active and signals:
            last = signals[-1]
            if last.direction == "long":
                if lows[i] <= last.sl or highs[i] >= last.tp:
                    trade_active = False
            else:
                if highs[i] >= last.sl or lows[i] <= last.tp:
                    trade_active = False

    return signals_to_df(out, signals)


# ---------------------------------------------------------------------------
# #11 Breaker Blocks (simplified LuxAlgo port — BB formation + retest)
# ---------------------------------------------------------------------------

@dataclass
class BreakerZone:
    top: float
    bot: float
    avg: float
    direction: int  # 1 bullish BB, -1 bearish BB
    bar: int
    broken: bool = False
    mitigated: bool = False


def breaker_blocks_signals(
    df: pd.DataFrame,
    pivot_len: int = 5,
    use_retest: bool = True,
) -> pd.DataFrame:
    """Simplified breaker: structure break + opposing candle zone + retest entry."""
    out = df.copy()
    ph = pivot_high(out["high"], pivot_len, pivot_len)
    pl = pivot_low(out["low"], pivot_len, pivot_len)
    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    n = len(out)
    last_ph = last_pl = np.nan
    mss_dir = 0
    active: BreakerZone | None = None
    signals: list[ZoneSignal] = []

    for i in range(n):
        if not np.isnan(ph.iloc[i]):
            last_ph = ph.iloc[i]
        if not np.isnan(pl.iloc[i]):
            last_pl = pl.iloc[i]

        # Bullish MSS: break above pivot high
        if not np.isnan(last_ph) and closes[i] > last_ph and mss_dir <= 0:
            mss_dir = 1
            # find last green candle in lookback
            for j in range(i - 1, max(0, i - 80), -1):
                if closes[j] > opens[j]:
                    top, bot = highs[j], lows[j]
                    avg = (top + bot) / 2
                    active = BreakerZone(top, bot, avg, 1, i)
                    atr = atr_wilder(out.iloc[: i + 1], 10).iloc[-1]
                    risk = atr * 2 if not np.isnan(atr) else (top - bot)
                    signals.append(
                        ZoneSignal(i, "long", closes[i], closes[i] - risk, closes[i] + risk * 2, meta="bb_plus")
                    )
                    break

        # Bearish MSS
        if not np.isnan(last_pl) and closes[i] < last_pl and mss_dir >= 0:
            mss_dir = -1
            for j in range(i - 1, max(0, i - 80), -1):
                if closes[j] < opens[j]:
                    top, bot = highs[j], lows[j]
                    avg = (top + bot) / 2
                    active = BreakerZone(top, bot, avg, -1, i)
                    atr = atr_wilder(out.iloc[: i + 1], 10).iloc[-1]
                    risk = atr * 2 if not np.isnan(atr) else (top - bot)
                    signals.append(
                        ZoneSignal(i, "short", closes[i], closes[i] + risk, closes[i] - risk * 2, meta="bb_min")
                    )
                    break

        if active and not active.mitigated:
            top, bot, avg = active.top, active.bot, active.avg
            if active.direction == 1:
                if closes[i] < bot:
                    active.mitigated = True
                elif use_retest and not active.broken and opens[i] > avg and opens[i] < top and closes[i] > top:
                    atr = atr_wilder(out.iloc[: i + 1], 10).iloc[-1]
                    risk = atr * 2 if not np.isnan(atr) else (top - bot)
                    signals.append(
                        ZoneSignal(i, "long", closes[i], closes[i] - risk, closes[i] + risk * 2, meta="sign_up")
                    )
                elif closes[i] < avg and closes[i] > bot:
                    active.broken = True
            else:
                if closes[i] > top:
                    active.mitigated = True
                elif use_retest and not active.broken and opens[i] < avg and opens[i] > bot and closes[i] < bot:
                    atr = atr_wilder(out.iloc[: i + 1], 10).iloc[-1]
                    risk = atr * 2 if not np.isnan(atr) else (top - bot)
                    signals.append(
                        ZoneSignal(i, "short", closes[i], closes[i] + risk, closes[i] - risk * 2, meta="sign_dn")
                    )
                elif closes[i] > avg and closes[i] < top:
                    active.broken = True

    return signals_to_df(out, signals)


# ---------------------------------------------------------------------------
# #12 Smart Money Concepts PRO v2 — confluence OB retest
# ---------------------------------------------------------------------------

@dataclass
class OBZone:
    top: float
    bot: float
    bullish: bool
    bar: int


def smc_pro_signals(
    df: pd.DataFrame,
    swing_len: int = 10,
    ob_max: int = 5,
    sig_need_zone: bool = True,
    sig_need_htf: bool = True,
    ob_vol_filter: bool = True,
    vol_mult: float = 1.5,
) -> pd.DataFrame:
    out = df.copy()
    ph_s = pivot_high(out["high"], swing_len, swing_len)
    pl_s = pivot_low(out["low"], swing_len, swing_len)
    atr14 = atr_wilder(out, 14).values
    vol_sma = sma(out["volume"], 20).values
    htf_bull = htf_ema_bias(out, factor=4)

    highs, lows, opens, closes = out["high"].values, out["low"].values, out["open"].values, out["close"].values
    n = len(out)

    last_ph = last_pl = np.nan
    last_ph_bar = last_pl_bar = 0
    ph_broken = pl_broken = True
    trend = 0
    bull_obs: list[OBZone] = []
    bear_obs: list[OBZone] = []
    signals: list[ZoneSignal] = []

    for i in range(n):
        if not np.isnan(ph_s.iloc[i]):
            last_ph = ph_s.iloc[i]
            last_ph_bar = i - swing_len
            ph_broken = False
        if not np.isnan(pl_s.iloc[i]):
            last_pl = pl_s.iloc[i]
            last_pl_bar = i - swing_len
            pl_broken = False

        bull_event = not np.isnan(last_ph) and not ph_broken and closes[i] > last_ph
        bear_event = not np.isnan(last_pl) and not pl_broken and closes[i] < last_pl
        is_bull_bos = bull_event and trend != -1
        is_bull_choch = bull_event and trend == -1
        is_bear_bos = bear_event and trend != 1
        is_bear_choch = bear_event and trend == 1

        if bull_event:
            ph_broken = True
            trend = 1
        if bear_event:
            pl_broken = True
            trend = -1

        # New bullish OB on bull structure break
        if is_bull_bos or is_bull_choch:
            dist = min(i - last_pl_bar, 100) if last_pl_bar else 0
            for off in range(dist):
                j = i - off
                if closes[j] < opens[j]:
                    strong = not ob_vol_filter or (
                        not np.isnan(vol_sma[j]) and out["volume"].iloc[j] > vol_sma[j] * vol_mult
                    )
                    if strong or not ob_vol_filter:
                        bull_obs.append(OBZone(highs[j], lows[j], True, j))
                        while len(bull_obs) > ob_max:
                            bull_obs.pop(0)
                    break

        if is_bear_bos or is_bear_choch:
            dist = min(i - last_ph_bar, 100) if last_ph_bar else 0
            for off in range(dist):
                j = i - off
                if closes[j] > opens[j]:
                    strong = not ob_vol_filter or (
                        not np.isnan(vol_sma[j]) and out["volume"].iloc[j] > vol_sma[j] * vol_mult
                    )
                    if strong or not ob_vol_filter:
                        bear_obs.append(OBZone(highs[j], lows[j], False, j))
                        while len(bear_obs) > ob_max:
                            bear_obs.pop(0)
                    break

        pd_mid = (last_ph + last_pl) / 2 if not np.isnan(last_ph) and not np.isnan(last_pl) else np.nan
        in_discount = not np.isnan(pd_mid) and closes[i] < pd_mid
        in_premium = not np.isnan(pd_mid) and closes[i] > pd_mid

        tap_bull = tap_bear = False
        prev_low, prev_high = lows[i - 1] if i else lows[i], highs[i - 1] if i else highs[i]

        for ob in list(bull_obs):
            touched = lows[i] <= ob.top and highs[i] >= ob.bot and not (prev_low <= ob.top and prev_high >= ob.bot)
            if touched:
                tap_bull = True
            if lows[i] < ob.bot:
                bull_obs.remove(ob)

        for ob in list(bear_obs):
            touched = lows[i] <= ob.top and highs[i] >= ob.bot and not (prev_low <= ob.top and prev_high >= ob.bot)
            if touched:
                tap_bear = True
            if highs[i] > ob.top:
                bear_obs.remove(ob)

        zone_long_ok = not sig_need_zone or in_discount
        zone_short_ok = not sig_need_zone or in_premium
        htf_long_ok = not sig_need_htf or bool(htf_bull.iloc[i])
        htf_short_ok = not sig_need_htf or not bool(htf_bull.iloc[i])

        atr = atr14[i] if not np.isnan(atr14[i]) else closes[i] * 0.01
        if tap_bull and zone_long_ok and htf_long_ok:
            e, sl, tp = closes[i], closes[i] - atr * 1.5, closes[i] + atr * 1.5
            signals.append(ZoneSignal(i, "long", e, sl, tp, meta="smc_confluence"))
        if tap_bear and zone_short_ok and htf_short_ok:
            e, sl, tp = closes[i], closes[i] + atr * 1.5, closes[i] - atr * 1.5
            signals.append(ZoneSignal(i, "short", e, sl, tp, meta="smc_confluence"))

    return signals_to_df(out, signals)


# ---------------------------------------------------------------------------
# #13 Zero Lag Trend Signals
# ---------------------------------------------------------------------------

def zero_lag_signals(df: pd.DataFrame, length: int = 70, mult: float = 1.2) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    lag = (length - 1) // 2
    zlema = ema(close + (close - close.shift(lag)), length)
    atr_v = true_range(out).ewm(alpha=1 / length, adjust=False).mean()
    volatility = atr_v.rolling(length * 3).max() * mult

    trend = pd.Series(0, index=close.index, dtype=int)
    for i in range(1, len(out)):
        if close.iloc[i] > zlema.iloc[i] + volatility.iloc[i] and close.iloc[i - 1] <= zlema.iloc[i - 1] + volatility.iloc[i - 1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < zlema.iloc[i] - volatility.iloc[i] and close.iloc[i - 1] >= zlema.iloc[i - 1] - volatility.iloc[i - 1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]

    buy = crossover(close, zlema) & (trend == 1) & (trend.shift(1) == 1)
    sell = crossunder(close, zlema) & (trend == -1) & (trend.shift(1) == -1)
    out["buy"] = buy.fillna(False)
    out["sell"] = sell.fillna(False)
    return out


# ---------------------------------------------------------------------------
# #14 Trendline Breakouts With Targets
# ---------------------------------------------------------------------------

def trendline_breakout_signals(df: pd.DataFrame, period: int = 10, use_wicks: bool = True) -> pd.DataFrame:
    out = df.copy()
    src_hi = out["high"] if use_wicks else out["close"].where(out["close"] > out["open"], out["close"])
    src_lo = out["low"] if use_wicks else out["close"].where(out["close"] > out["open"], out["open"])
    ph = pivot_high(src_hi, period, period // 2)
    pl = pivot_low(src_lo, period, period // 2)

    atr_adj = true_range(out).rolling(30).mean() * 0.3
    zband = atr_adj.clip(upper=out["close"] * 0.003 / 2).shift(20).fillna(out["close"] * 0.001)

    highs, lows, closes = out["high"].values, out["low"].values, out["close"].values
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    entry_sl = np.full(n, np.nan)
    entry_tp = np.full(n, np.nan)

    # Track last two pivot highs for descending line
    piv_h: list[tuple[int, float]] = []
    piv_l: list[tuple[int, float]] = []
    trade_on = False

    for i in range(n):
        if not np.isnan(ph.iloc[i]):
            piv_h.append((i - period // 2, ph.iloc[i]))
            piv_h = piv_h[-3:]
        if not np.isnan(pl.iloc[i]):
            piv_l.append((i - period // 2, pl.iloc[i]))
            piv_l = piv_l[-3:]

        zb = zband.iloc[i] if not np.isnan(zband.iloc[i]) else closes[i] * 0.001

        # Resistance break (long): line through last 2 pivot highs
        if len(piv_h) >= 2 and not trade_on:
            x1, y1 = piv_h[-2]
            x2, y2 = piv_h[-1]
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                if slope < 0:  # descending resistance
                    line_now = y2 + slope * (i - x2)
                    line_prev = y2 + slope * (i - 1 - x2)
                    if closes[i - 1] < line_prev and closes[i] > line_now:
                        buy[i] = True
                        entry_sl[i] = lows[i] - zb * 20
                        entry_tp[i] = highs[i] + zb * 20
                        trade_on = True

        if len(piv_l) >= 2 and not trade_on:
            x1, y1 = piv_l[-2]
            x2, y2 = piv_l[-1]
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                if slope > 0:  # ascending support break down
                    line_now = y2 + slope * (i - x2)
                    line_prev = y2 + slope * (i - 1 - x2)
                    if closes[i - 1] > line_prev and closes[i] < line_now:
                        sell[i] = True
                        entry_sl[i] = highs[i] + zb * 20
                        entry_tp[i] = lows[i] - zb * 20
                        trade_on = True

        if trade_on:
            if buy.any() and (highs[i] >= entry_tp[i] or closes[i] <= entry_sl[i]):
                trade_on = False
            if sell.any() and (lows[i] <= entry_tp[i] or closes[i] >= entry_sl[i]):
                trade_on = False

    out["buy"] = buy
    out["sell"] = sell
    out["sl_price"] = entry_sl
    out["tp_price"] = entry_tp
    return out


# ---------------------------------------------------------------------------
# #15 rsi_advanced (EWO + RSI strategy)
# ---------------------------------------------------------------------------

def rsi_advanced_signals(
    df: pd.DataFrame,
    ewo_fast: int = 5,
    ewo_slow: int = 34,
    rsi_len: int = 14,
    lookback_len: int = 10,
    rsi_oversold: int = 30,
) -> pd.DataFrame:
    out = df.copy()
    hl2 = (out["high"] + out["low"]) / 2
    ewo = sma(hl2, ewo_fast) - sma(hl2, ewo_slow)
    rsi_v = rsi(out["close"], rsi_len)
    mfi_v = mfi(out, 14)
    vol_ma = sma(out["volume"], 20)
    vol_ok = out["volume"] > vol_ma * 0.8

    breakout_barrier = out["high"].rolling(lookback_len).max().shift(1)
    oversold_zone = pd.Series(False, index=out.index)
    os = False
    buy = np.zeros(len(out), dtype=bool)
    sell = np.zeros(len(out), dtype=bool)
    last_sig = 0
    closes = out["close"].values
    rsi_a = rsi_v.values
    ewo_a = ewo.values
    mfi_a = mfi_v.values
    vol_a = vol_ok.values
    bb_a = breakout_barrier.values

    for i in range(1, len(out)):
        if rsi_a[i] < rsi_oversold:
            os = True
        price_break = closes[i] > bb_a[i] if not np.isnan(bb_a[i]) else False
        raw_buy = rsi_a[i - 1] < 40 <= rsi_a[i] and mfi_a[i] > 30 and ewo_a[i] > ewo_a[i - 1] and vol_a[i] and (price_break or os)
        raw_sell = rsi_a[i - 1] > 60 >= rsi_a[i] and mfi_a[i] < 70 and ewo_a[i] < ewo_a[i - 1] and vol_a[i]
        if raw_buy and last_sig != 1:
            buy[i] = True
            last_sig = 1
            os = False
        if raw_sell and last_sig != -1:
            sell[i] = True
            last_sig = -1

    out["buy"] = buy
    out["sell"] = sell
    return out
