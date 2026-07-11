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


# ---------------------------------------------------------------------------
# #18 Supply and Demand Zones (Flux Charts)
# ---------------------------------------------------------------------------

@dataclass
class _SDZone:
    id: int
    top: float
    bottom: float
    created_bar: int
    is_supply: bool
    active: bool = True
    pending_flip: bool = False
    last_retest_bar: int = -999
    retests: int = 0


def _sd_zone_bounds(
    highs: np.ndarray,
    lows: np.ndarray,
    opens: np.ndarray,
    closes: np.ndarray,
    bars_back: int,
    i: int,
    is_supply: bool,
    wick_avg_bars: int = 5,
) -> tuple[float, float]:
    pivot_h = highs[i - bars_back]
    pivot_l = lows[i - bars_back]
    sum_wick = 0.0
    for k in range(wick_avg_bars):
        idx = i - bars_back + k
        h, l = highs[idx], lows[idx]
        o, c = opens[idx], closes[idx]
        sum_wick += (h - max(o, c)) if is_supply else (min(o, c) - l)
    avg_wick = sum_wick / wick_avg_bars
    if is_supply:
        top, bot = pivot_h, pivot_h - avg_wick
    else:
        top, bot = pivot_l + avg_wick, pivot_l
    return top, bot


def _sd_has_overlap(new_top: float, new_bot: float, zones: list[_SDZone], bar_index: int, lookback: int) -> bool:
    for z in zones:
        if z.active and bar_index - z.created_bar <= lookback:
            if new_bot <= z.top and new_top >= z.bottom:
                return True
    return False


def _sd_update_zones(
    zones: list[_SDZone],
    bar_index: int,
    close: float,
    high: float,
    low: float,
    lookback: int,
    cooldown: int,
) -> tuple[bool, bool]:
    """Returns (bull_retest, bear_retest) for this bar."""
    bull_retest = bear_retest = False
    for z in zones:
        if z.active and bar_index - z.created_bar > lookback:
            z.active = False
        if not z.active:
            continue
        broke_through = (z.is_supply and close > z.top) or (not z.is_supply and close < z.bottom)
        broke_back = (z.is_supply and close < z.bottom) or (not z.is_supply and close > z.top)
        pending_handled = False
        flipped = False
        if z.pending_flip and broke_through:
            z.is_supply = not z.is_supply
            z.pending_flip = False
            pending_handled = True
            flipped = True
        if z.pending_flip and broke_back:
            z.retests += 1
            z.last_retest_bar = bar_index
            if z.is_supply:
                bear_retest = True
            else:
                bull_retest = True
            z.pending_flip = False
            pending_handled = True
        if not pending_handled and not z.pending_flip and broke_through:
            z.pending_flip = True
        if (
            z.active
            and not flipped
            and not z.pending_flip
            and not pending_handled
            and bar_index > z.created_bar
            and bar_index - z.last_retest_bar >= cooldown
        ):
            reacted = False
            if z.is_supply:
                if high >= z.bottom and close < z.bottom:
                    reacted = True
            else:
                if low <= z.top and close > z.top:
                    reacted = True
            if reacted:
                z.retests += 1
                z.last_retest_bar = bar_index
                if z.is_supply:
                    bear_retest = True
                else:
                    bull_retest = True
    return bull_retest, bear_retest


def supply_demand_signals(
    df: pd.DataFrame,
    pivot_len: int = 30,
    lookback_bars: int = 2000,
    cooldown_bars: int = 3,
    sl_atr_mult: float = 0.15,
    tp_rr: float = 2.0,
) -> pd.DataFrame:
    """Flux supply/demand zone retest alerts with zone-native SL/TP."""
    out = df.copy()
    n = len(out)
    highs = out["high"].values
    lows = out["low"].values
    opens = out["open"].values
    closes = out["close"].values
    atr_v = atr_wilder(out, 14).values

    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values

    supply: list[_SDZone] = []
    demand: list[_SDZone] = []
    zone_id = 0
    max_zones = 500

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)

    for i in range(pivot_len * 2, n):
        if not np.isnan(ph[i]):
            bars_back = pivot_len
            top, bot = _sd_zone_bounds(highs, lows, opens, closes, bars_back, i, True)
            if top > bot and not _sd_has_overlap(top, bot, supply + demand, i, lookback_bars):
                supply.append(_SDZone(zone_id, top, bot, i - pivot_len, True))
                zone_id += 1
                if len(supply) > max_zones:
                    supply.pop(0)
        if not np.isnan(pl[i]):
            bars_back = pivot_len
            top, bot = _sd_zone_bounds(highs, lows, opens, closes, bars_back, i, False)
            if top > bot and not _sd_has_overlap(top, bot, supply + demand, i, lookback_bars):
                demand.append(_SDZone(zone_id, top, bot, i - pivot_len, False))
                zone_id += 1
                if len(demand) > max_zones:
                    demand.pop(0)

        bull_r, bear_r = False, False
        for zones in (supply, demand):
            br, sr = _sd_update_zones(zones, i, closes[i], highs[i], lows[i], lookback_bars, cooldown_bars)
            bull_r = bull_r or br
            bear_r = bear_r or sr

        safe_atr = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else closes[i] * 0.005
        if bull_r:
            # Demand bounce — SL below zone, TP at RR
            z = min((z for z in demand if z.active), key=lambda z: abs((z.top + z.bottom) / 2 - closes[i]), default=None)
            entry = closes[i]
            sl = (z.bottom - safe_atr * sl_atr_mult) if z else entry - safe_atr
            risk = max(entry - sl, safe_atr * 0.25)
            buy[i] = True
            sl_p[i] = sl
            tp_p[i] = entry + risk * tp_rr
        if bear_r:
            z = min((z for z in supply if z.active), key=lambda z: abs((z.top + z.bottom) / 2 - closes[i]), default=None)
            entry = closes[i]
            sl = (z.top + safe_atr * sl_atr_mult) if z else entry + safe_atr
            risk = max(sl - entry, safe_atr * 0.25)
            sell[i] = True
            sl_p[i] = sl
            tp_p[i] = entry - risk * tp_rr

    out["buy"] = buy
    out["sell"] = sell
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    return out


# ---------------------------------------------------------------------------
# #19 Strong Pullback Signals
# ---------------------------------------------------------------------------

def _htf_ema_series(df: pd.DataFrame, tf_minutes: int = 240, ema_len: int = 50) -> pd.Series:
    """Approximate Pine request.security HTF EMA (prior bar, no lookahead)."""
    if "timestamp" in df.columns:
        idx = pd.to_datetime(df["timestamp"])
    else:
        idx = df.index
    tmp = df.copy()
    tmp.index = idx
    try:
        rs = tmp["close"].resample(f"{tf_minutes}min").last().dropna()
    except Exception:
        factor = max(1, tf_minutes // 15)
        rs = tmp["close"].iloc[::factor]
    htf = ema(rs, ema_len).shift(1)
    aligned = htf.reindex(tmp.index, method="ffill")
    return pd.Series(aligned.values, index=df.index)


def strong_pullback_signals(
    df: pd.DataFrame,
    fast_len: int = 34,
    slow_len: int = 144,
    pull_len: int = 21,
    slope_look: int = 5,
    break_look: int = 20,
    min_wait_bars: int = 2,
    max_hunt_bars: int = 40,
    min_break_body: float = 0.20,
    use_cooldown: bool = True,
    cooldown_bars: int = 10,
    entry_depth: float = 0.40,
    require_close: bool = False,
    atr_len: int = 14,
    sl_buf_atr: float = 0.30,
    max_risk_atr: float = 2.5,
    min_risk_atr: float = 0.5,
    tp1_r: float = 1.0,
    use_htf: bool = True,
    htf_ema_len: int = 50,
    only_strong: bool = False,
    strong_thr: float = 5.0,
) -> pd.DataFrame:
    """Strong Pullback limit-fill entries with structural ATR-capped SL and 1R TP."""
    out = df.copy()
    n = len(out)
    closes = out["close"].values
    highs = out["high"].values
    lows = out["low"].values
    opens = out["open"].values
    vols = out["volume"].values if "volume" in out.columns else np.ones(n)

    fast = ema(out["close"], fast_len).values
    slow = ema(out["close"], slow_len).values
    pull = ema(out["close"], pull_len).values
    atr_v = atr_wilder(out, atr_len).values
    rsi_v = rsi(out["close"], 14).values
    vol_sma = sma(out["volume"], 20).values if "volume" in out.columns else np.ones(n)
    htf = _htf_ema_series(out, 240, htf_ema_len).values

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    entry_p = np.full(n, np.nan)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)

    armed = False
    adir = 0
    arm_bar = -1
    swing_ext = 0.0
    last_sig_bar = -999
    open_bar = -1
    open_is_long = False
    open_sl = open_tp = 0.0

    for i in range(max(slope_look, break_look) + 1, n):
        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else 1e-8
        body = abs(closes[i] - opens[i])
        bull_trend = fast[i] > slow[i] and closes[i] > slow[i] and fast[i] > fast[i - slope_look]
        bear_trend = fast[i] < slow[i] and closes[i] < slow[i] and fast[i] < fast[i - slope_look]
        hi_before = np.max(highs[i - break_look : i])
        lo_before = np.min(lows[i - break_look : i])
        break_ok = body >= a * min_break_body
        bull_break = bull_trend and closes[i] > hi_before and closes[i] > opens[i] and break_ok
        bear_break = bear_trend and closes[i] < lo_before and closes[i] < opens[i] and break_ok

        trade_active = open_bar >= 0
        cooldown_ok = (not use_cooldown) or (i - last_sig_bar >= cooldown_bars)
        if (bull_break or bear_break) and not armed and cooldown_ok and not trade_active:
            armed = True
            adir = 1 if bull_break else -1
            arm_bar = i
            swing_ext = lows[i] if adir == 1 else highs[i]

        if armed:
            swing_ext = min(swing_ext, lows[i]) if adir == 1 else max(swing_ext, highs[i])
        age = i - arm_bar if armed else 0
        expire = armed and age > max_hunt_bars
        flip = armed and ((adir == 1 and not bull_trend) or (adir == -1 and not bear_trend))
        limit_px = pull[i] - entry_depth * a * adir if adir != 0 else np.nan
        fill_now = armed and age >= min_wait_bars and (lows[i] <= limit_px if adir == 1 else highs[i] >= limit_px)
        fill_px = min(opens[i], limit_px) if adir == 1 else max(opens[i], limit_px)

        htf_ok = (not use_htf) or np.isnan(htf[i]) or (closes[i] > htf[i] if adir == 1 else closes[i] < htf[i])
        trend_ok = closes[i] > slow[i] if adir == 1 else closes[i] < slow[i]
        close_ok = (not require_close) or (closes[i] > opens[i] if adir == 1 else closes[i] < opens[i])
        can_open = not trade_active and not np.isnan(atr_v[i]) and armed

        if fill_now and can_open and htf_ok and trend_ok and close_ok:
            sep = min(abs(fast[i] - slow[i]) / (a * 2.5), 1.0)
            dep = min(entry_depth / 0.6, 1.0)
            mom = (
                min(max((rsi_v[i] - 50.0) / 30.0, 0.0), 1.0)
                if adir == 1
                else min(max((50.0 - rsi_v[i]) / 30.0, 0.0), 1.0)
            )
            vol_f = min(vols[i] / vol_sma[i], 1.0) if vol_sma[i] > 0 else 0.0
            htf_f = 1.0 if htf_ok else 0.0
            raw = (htf_f * 0.30 + 1.0 * 0.12 + sep * 0.22 + dep * 0.16 + mom * 0.10 + vol_f * 0.10) / 1.0
            score = min(max(raw * 10.0, 0.0), 10.0)
            take = (not only_strong) or score >= strong_thr
            if take:
                is_long = adir == 1
                raw_stop = swing_ext - a * sl_buf_atr if is_long else swing_ext + a * sl_buf_atr
                risk0 = abs(fill_px - raw_stop)
                risk = min(max(risk0, a * min_risk_atr), a * max_risk_atr)
                stopv = fill_px - risk if is_long else fill_px + risk
                t1 = fill_px + risk * tp1_r if is_long else fill_px - risk * tp1_r
                if is_long:
                    buy[i] = True
                else:
                    sell[i] = True
                entry_p[i] = fill_px
                sl_p[i] = stopv
                tp_p[i] = t1
                last_sig_bar = i
                open_bar = i
                open_is_long = is_long
                open_sl, open_tp = stopv, t1

        if armed and (fill_now or expire or flip):
            armed = False
            adir = 0

        if open_bar >= 0 and i > open_bar:
            if open_is_long:
                if lows[i] <= open_sl or highs[i] >= open_tp:
                    open_bar = -1
            else:
                if highs[i] >= open_sl or lows[i] <= open_tp:
                    open_bar = -1

    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = entry_p
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p
    return out
