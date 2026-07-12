"""MADDNESSANI v4 — Python port with 1h+4h HTF trend gate."""
from __future__ import annotations

import numpy as np
import pandas as pd

from farhad_master_strategy import _zero_lag_trend
from indicators import alpha_trend_signals, atr_wilder, bj_bot_signals, crossover, crossunder, ema, ut_bot_signals
from trend_filter import filter_signals_df, htf_trend_gate
from zone_engine import pivot_high, pivot_low
from extra_indicators import liquidity_shift_signals
from zone_indicators import rsi_advanced_signals, strong_pullback_signals

MODE_PARAMS = {
    "precision": dict(min_tier1=2, min_tech=4, min_score=7.5, min_zone=2.0, cooldown=5),
    "balanced": dict(min_tier1=1, min_tech=2, min_score=5.5, min_zone=1.0, cooldown=3),
    "sniper": dict(min_tier1=2, min_tech=4, min_score=9.0, min_zone=2.0, cooldown=10),
}

TF_ADJ = {
    "5m": dict(score_adj=-1.0, cooldown_add=3, swing_len=8),
    "15m": dict(score_adj=-0.5, cooldown_add=1, swing_len=10),
    "1h": dict(score_adj=0.0, cooldown_add=0, swing_len=12),
}


def _adx_ok(df: pd.DataFrame, length: int = 14, minimum: float = 20.0) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    dn = -low.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx_v = dx.ewm(alpha=1 / length, adjust=False).mean()
    return adx_v >= minimum


def _fvg_sd_liq_flags(df: pd.DataFrame, piv_len: int = 5, sd_len: int = 10) -> tuple[pd.Series, ...]:
    out = df.copy()
    ph = pivot_high(out["high"], piv_len, piv_len)
    pl = pivot_low(out["low"], piv_len, piv_len)
    swing_hi = ph.shift(piv_len)
    swing_lo = pl.shift(piv_len)
    bull_pend = (out["low"] < swing_lo) & (out["close"] > swing_lo)
    bear_pend = (out["high"] > swing_hi) & (out["close"] < swing_hi)
    liq_long = bull_pend & (out["close"] > swing_hi)
    liq_short = bear_pend & (out["close"] < swing_lo)
    fvg_long = (out["low"] > out["high"].shift(2)) & (out["close"] > out["open"])
    fvg_short = (out["high"] < out["low"].shift(2)) & (out["close"] < out["open"])
    sd_bot = out["low"].rolling(sd_len).min().shift(1)
    sd_top = out["high"].rolling(sd_len).max().shift(1)
    sd_long = (out["low"] <= sd_bot * 1.002) & (out["close"] > sd_bot) & (out["close"] > out["open"])
    sd_short = (out["high"] >= sd_top * 0.998) & (out["close"] < sd_top) & (out["close"] < out["open"])
    return fvg_long.fillna(False), fvg_short.fillna(False), sd_long.fillna(False), sd_short.fillna(False), liq_long.fillna(False), liq_short.fillna(False)


def _zone_score(flags: pd.Series, bar: int, lb: int) -> float:
    lo = max(0, bar - lb + 1)
    return float(flags.iloc[lo : bar + 1].sum()) * 1.5


def _struct_sl_tp(
    df: pd.DataFrame,
    i: int,
    direction: str,
    swing_len: int,
    sl_atr_buf: float = 1.5,
    min_rr: float = 2.0,
    max_rr: float = 4.0,
    tp_swing_lb: int = 24,
) -> tuple[float, float]:
    close = float(df["close"].iloc[i])
    atr_v = float(atr_wilder(df, 14).iloc[i])
    ema_f = float(ema(df["close"], 34).iloc[i])
    if direction == "long":
        swing_lo = float(df["low"].iloc[max(0, i - swing_len + 1) : i + 1].min())
        sl = swing_lo - atr_v * sl_atr_buf
        sl = min(sl, ema_f - atr_v * 0.3)
        risk = max(close - sl, atr_v * 0.55)
        struct_hi = float(df["high"].iloc[max(0, i - tp_swing_lb + 1) : i + 1].max())
        tp = max(close + risk * min_rr, struct_hi + atr_v * 0.1)
        tp = min(tp, close + risk * max_rr)
    else:
        swing_hi = float(df["high"].iloc[max(0, i - swing_len + 1) : i + 1].max())
        sl = swing_hi + atr_v * sl_atr_buf
        sl = max(sl, ema_f + atr_v * 0.3)
        risk = max(sl - close, atr_v * 0.55)
        struct_lo = float(df["low"].iloc[max(0, i - tp_swing_lb + 1) : i + 1].min())
        tp = min(close - risk * min_rr, struct_lo - atr_v * 0.1)
        tp = max(tp, close - risk * max_rr)
    return sl, tp


def maddnessani_signals(
    df: pd.DataFrame,
    chart_tf: str = "1h",
    market: str = "crypto",
    mode: str = "precision",
    use_htf_trend: bool = True,
    zone_lb: int = 8,
    novolumedata: bool = False,
    h1_df: pd.DataFrame | None = None,
    h4_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """MADDNESSANI v4 signal engine with optional 1h+4h trend gate."""
    if chart_tf not in TF_ADJ:
        raise ValueError(f"chart_tf must be one of {list(TF_ADJ)}; got {chart_tf}")

    p = MODE_PARAMS.get(mode, MODE_PARAMS["precision"])
    adj = TF_ADJ[chart_tf]
    min_score = p["min_score"] + adj["score_adj"]
    cooldown = p["cooldown"] + adj["cooldown_add"]
    swing_len = adj["swing_len"]

    out = df.copy()
    n = len(out)
    bj = bj_bot_signals(out)
    ut = ut_bot_signals(out)
    alpha = alpha_trend_signals(out, novolumedata=novolumedata)
    zl = _zero_lag_trend(out)
    rsi_sig = rsi_advanced_signals(out)
    sp = strong_pullback_signals(out)
    liq_sig = liquidity_shift_signals(out)
    adx_ok = _adx_ok(out, minimum=20.0)
    fvg_l, fvg_s, sd_l, sd_s, _, _ = _fvg_sd_liq_flags(out)

    ma21 = ema(out["close"], 21)
    ma50 = ema(out["close"], 50)
    bj_cross_l = crossover(ma21, ma50).fillna(False)
    bj_cross_s = crossunder(ma21, ma50).fillna(False)

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    entry_p = np.full(n, np.nan)
    last_sig = -999

    closes = out["close"].values

    for i in range(max(zone_lb, 30), n):
        if i - last_sig < cooldown:
            continue
        ut_bull = closes[i] > ut["tsl"].iloc[i]
        ut_bear = closes[i] < ut["tsl"].iloc[i]
        alpha_bull = closes[i] > alpha["alpha_trend"].iloc[i]
        alpha_bear = closes[i] < alpha["alpha_trend"].iloc[i]
        zl_bull = zl.iloc[i] == 1
        zl_bear = zl.iloc[i] == -1
        bj_bull = bj["ma1"].iloc[i] > bj["ma2"].iloc[i]
        bj_bear = bj["ma1"].iloc[i] < bj["ma2"].iloc[i]
        tech_long = int(ut_bull) + int(alpha_bull) + int(zl_bull) + int(bj_bull)
        tech_short = int(ut_bear) + int(alpha_bear) + int(zl_bear) + int(bj_bear)

        tier1_l = int(rsi_sig["buy"].iloc[i]) + int(liq_sig["buy"].iloc[i]) + int(sp["buy"].iloc[i]) + int(bj_cross_l.iloc[i])
        tier1_s = int(rsi_sig["sell"].iloc[i]) + int(liq_sig["sell"].iloc[i]) + int(sp["sell"].iloc[i]) + int(bj_cross_s.iloc[i])
        zone_l = _zone_score(fvg_l | sd_l | liq_sig["buy"], i, zone_lb)
        zone_s = _zone_score(fvg_s | sd_s | liq_sig["sell"], i, zone_lb)
        score_l = zone_l + tier1_l * 3.0 + tech_long * 0.75
        score_s = zone_s + tier1_s * 3.0 + tech_short * 0.75

        setup_l = (
            tier1_l >= p["min_tier1"]
            and zone_l >= p["min_zone"]
            and score_l >= min_score
            and tech_long >= p["min_tech"]
            and adx_ok.iloc[i]
        )
        setup_s = (
            tier1_s >= p["min_tier1"]
            and zone_s >= p["min_zone"]
            and score_s >= min_score
            and tech_short >= p["min_tech"]
            and adx_ok.iloc[i]
        )

        if setup_l:
            buy[i] = True
            entry_p[i] = closes[i]
            sl_p[i], tp_p[i] = _struct_sl_tp(out, i, "long", swing_len)
            last_sig = i
        elif setup_s:
            sell[i] = True
            entry_p[i] = closes[i]
            sl_p[i], tp_p[i] = _struct_sl_tp(out, i, "short", swing_len)
            last_sig = i

    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = entry_p
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p

    if use_htf_trend:
        gate = htf_trend_gate(out, market=market, h1_df=h1_df, h4_df=h4_df)  # type: ignore[arg-type]
        out = filter_signals_df(
            out, gate, require_trend=True, long_col="htf_allow_long", short_col="htf_allow_short"
        )
        out["h1_bull"] = gate["h1_bull"].values
        out["h4_bull"] = gate["h4_bull"].values
        out["htf_allow_long"] = gate["htf_allow_long"].values
        out["htf_allow_short"] = gate["htf_allow_short"].values

    return out
