"""
Trend Filter Module — reusable HTF/LTF trend bias for crypto & forex strategies.

Backed by 1h/4h batch backtest rankings (Jul 2026):
  - Liquidity Shift: best overall crypto+forex on 1h/4h
  - Bj Bot EMA: stable pure-trend filter
  - SMC Structure / Strong Pullback / Ichimoku: market-specific boosts

Usage:
    from trend_filter import apply_trend_filter, TrendPreset

    out = apply_trend_filter(df, preset="crypto_4h", market="crypto")
    if out["trend_bull"].iloc[-1] and out["trend_score"].iloc[-1] >= 0.6:
        ... allow long entries ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from indicators import atr_wilder, ema, rsi, sma
from zone_engine import pivot_high, pivot_low

Market = Literal["crypto", "forex"]
PresetName = Literal[
    "crypto_1h", "crypto_4h", "crypto_scalp",
    "forex_1h", "forex_4h", "forex_scalp",
    "universal",
]


@dataclass
class TrendFilterSettings:
    """Weighted voting across trend engines."""

    name: str = "universal"
    market: Market = "crypto"
    min_score_long: float = 0.55
    min_score_short: float = 0.55
    neutral_band: float = 0.15
    adx_min: float = 18.0
    use_adx: bool = True

    w_bj: float = 1.0
    w_liquidity: float = 2.0
    w_smc: float = 1.0
    w_pullback: float = 1.0
    w_ichimoku: float = 0.0

    bj_fast: int = 21
    bj_slow: int = 50
    liq_pivot: int = 5
    smc_fast: int = 30
    smc_slow: int = 100
    pb_fast: int = 34
    pb_slow: int = 144
    liq_memory_bars: int = 80


PRESETS: dict[str, TrendFilterSettings] = {
    # Backtest winners: Ichimoku + Liq Shift + Strong PB on 1h
    "crypto_1h": TrendFilterSettings(
        name="crypto_1h",
        market="crypto",
        w_liquidity=2.0,
        w_ichimoku=1.5,
        w_pullback=1.0,
        w_bj=1.0,
        w_smc=0.75,
        min_score_long=0.55,
        min_score_short=0.55,
    ),
    # Backtest winners: Liq Shift + SMC + Bj on 4h
    "crypto_4h": TrendFilterSettings(
        name="crypto_4h",
        market="crypto",
        w_liquidity=2.5,
        w_smc=2.0,
        w_bj=1.25,
        w_pullback=0.75,
        w_ichimoku=0.5,
        min_score_long=0.60,
        min_score_short=0.60,
        adx_min=20.0,
    ),
    "crypto_scalp": TrendFilterSettings(
        name="crypto_scalp",
        market="crypto",
        w_liquidity=1.75,
        w_bj=1.25,
        w_ichimoku=1.0,
        w_smc=0.5,
        min_score_long=0.50,
        min_score_short=0.50,
        use_adx=False,
    ),
    # Forex 1h: Liq Shift + Strong Pullback + Bj
    "forex_1h": TrendFilterSettings(
        name="forex_1h",
        market="forex",
        w_liquidity=2.0,
        w_pullback=2.0,
        w_bj=1.0,
        w_ichimoku=0.75,
        w_smc=0.5,
        min_score_long=0.55,
        min_score_short=0.55,
        adx_min=18.0,
    ),
    # Forex 4h: Liq Shift dominant (XAU PF=4.37)
    "forex_4h": TrendFilterSettings(
        name="forex_4h",
        market="forex",
        w_liquidity=3.0,
        w_pullback=1.0,
        w_bj=0.75,
        w_smc=0.5,
        w_ichimoku=0.25,
        min_score_long=0.58,
        min_score_short=0.58,
        adx_min=20.0,
    ),
    "forex_scalp": TrendFilterSettings(
        name="forex_scalp",
        market="forex",
        w_liquidity=2.0,
        w_pullback=1.5,
        w_bj=1.0,
        min_score_long=0.52,
        min_score_short=0.52,
        use_adx=False,
    ),
    "universal": TrendFilterSettings(
        name="universal",
        market="crypto",
        w_liquidity=2.0,
        w_bj=1.0,
        w_smc=1.0,
        w_pullback=1.0,
        w_ichimoku=0.75,
    ),
}


def preset_for(market: Market, timeframe: str) -> TrendFilterSettings:
    """Pick preset from market + chart timeframe string."""
    tf = timeframe.lower().strip()
    if market == "crypto":
        if tf in ("5m", "5", "15m", "15"):
            return PRESETS["crypto_scalp"]
        if tf in ("4h", "240", "1d", "d"):
            return PRESETS["crypto_4h"]
        return PRESETS["crypto_1h"]
    if tf in ("5m", "5", "15m", "15"):
        return PRESETS["forex_scalp"]
    if tf in ("4h", "240", "1d", "d"):
        return PRESETS["forex_4h"]
    return PRESETS["forex_1h"]


def _adx_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    up = high.diff()
    dn = -low.diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    atr_s = tr.ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_s
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def _bj_bias(df: pd.DataFrame, fast: int, slow: int) -> tuple[pd.Series, pd.Series]:
    ma_f = ema(df["close"], fast)
    ma_s = ema(df["close"], slow)
    bull = (ma_f > ma_s) & (df["close"] > ma_s)
    bear = (ma_f < ma_s) & (df["close"] < ma_s)
    return bull.fillna(False), bear.fillna(False)


def _smc_bias(df: pd.DataFrame, fast: int, slow: int) -> tuple[pd.Series, pd.Series]:
    ma_f = ema(df["close"], fast)
    ma_s = ema(df["close"], slow)
    hi_br = df["high"].rolling(5).max().shift(1)
    lo_br = df["low"].rolling(5).min().shift(1)
    bull = (ma_f > ma_s) & (df["close"] > hi_br)
    bear = (ma_f < ma_s) & (df["close"] < lo_br)
    return bull.fillna(False), bear.fillna(False)


def _pullback_bias(df: pd.DataFrame, fast: int, slow: int) -> tuple[pd.Series, pd.Series]:
    ma_f = ema(df["close"], fast)
    ma_s = ema(df["close"], slow)
    bull = (ma_f > ma_s) & (df["close"] > ma_s) & (ma_f > ma_f.shift(5))
    bear = (ma_f < ma_s) & (df["close"] < ma_s) & (ma_f < ma_f.shift(5))
    return bull.fillna(False), bear.fillna(False)


def _ichimoku_bias(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    hl2 = (df["high"] + df["low"]) / 2
    tenkan = ema(hl2, 9)
    kijun = ema(hl2, 26)
    senkou_a = ema((tenkan + kijun) / 2, 26)
    senkou_b = ema(hl2, 52)
    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1).shift(26)
    cloud_bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1).shift(26)
    bull = (df["close"] > cloud_top) & (tenkan > kijun)
    bear = (df["close"] < cloud_bot) & (tenkan < kijun)
    return bull.fillna(False), bear.fillna(False)


def _liquidity_bias(df: pd.DataFrame, pivot_len: int, memory: int) -> tuple[pd.Series, pd.Series]:
    """Structural liquidity shift state — persists bias after sweep + reclaim."""
    n = len(df)
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    opens = df["open"].values
    atr_v = atr_wilder(df, 14).values
    ph = pivot_high(df["high"], pivot_len, pivot_len).values
    pl = pivot_low(df["low"], pivot_len, pivot_len).values

    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    swing_hi = swing_lo = np.nan
    bull_pending = bear_pending = False
    bull_bar = bear_bar = 0
    bias = 0

    for i in range(pivot_len * 2 + 1, n):
        if not np.isnan(ph[i]):
            swing_hi = highs[i - pivot_len]
        if not np.isnan(pl[i]):
            swing_lo = lows[i - pivot_len]
        if not np.isnan(swing_lo) and lows[i] < swing_lo and closes[i] > swing_lo:
            bull_pending, bull_bar = True, i
        if not np.isnan(swing_hi) and highs[i] > swing_hi and closes[i] < swing_hi:
            bear_pending, bear_bar = True, i
        if bull_pending and i - bull_bar > memory:
            bull_pending = False
        if bear_pending and i - bear_bar > memory:
            bear_pending = False

        a = atr_v[i] if not np.isnan(atr_v[i]) and atr_v[i] > 0 else max(highs[i] - lows[i], 1e-8)
        body = abs(closes[i] - opens[i])
        if bull_pending and (
            (not np.isnan(swing_hi) and closes[i] > swing_hi)
            or (closes[i] > opens[i] and body >= a * 0.8)
        ):
            bias = 1
            bull_pending = False
        if bear_pending and (
            (not np.isnan(swing_lo) and closes[i] < swing_lo)
            or (closes[i] < opens[i] and body >= a * 0.8)
        ):
            bias = -1
            bear_pending = False

        if bias == 1:
            bull[i] = True
        elif bias == -1:
            bear[i] = True

    return pd.Series(bull, index=df.index), pd.Series(bear, index=df.index)


def _vote_score(bull_flags: list[tuple[float, pd.Series]], bear_flags: list[tuple[float, pd.Series]]) -> tuple[pd.Series, pd.Series, pd.Series]:
    w_sum = sum(w for w, _ in bull_flags) or 1.0
    bull_score = sum(s.astype(float) * w for w, s in bull_flags) / w_sum
    bear_score = sum(s.astype(float) * w for w, s in bear_flags) / w_sum
    net = bull_score - bear_score
    return bull_score, bear_score, net


def apply_trend_filter(
    df: pd.DataFrame,
    preset: PresetName | str | None = None,
    market: Market = "crypto",
    settings: TrendFilterSettings | None = None,
    timeframe: str | None = None,
) -> pd.DataFrame:
    """
    Add trend filter columns to OHLCV dataframe.

    Columns added:
      trend_bull, trend_bear, trend_neutral, trend_score (-1..+1),
      trend_label, adx_ok, allow_long, allow_short
    """
    if settings is None:
        if preset and preset in PRESETS:
            settings = PRESETS[preset]
        elif timeframe:
            settings = preset_for(market, timeframe)
        else:
            settings = PRESETS["universal"]
    settings.market = market

    out = df.copy()
    b_bj, s_bj = _bj_bias(out, settings.bj_fast, settings.bj_slow)
    b_liq, s_liq = _liquidity_bias(out, settings.liq_pivot, settings.liq_memory_bars)
    b_smc, s_smc = _smc_bias(out, settings.smc_fast, settings.smc_slow)
    b_pb, s_pb = _pullback_bias(out, settings.pb_fast, settings.pb_slow)
    b_ichi, s_ichi = _ichimoku_bias(out)

    bull_flags = [
        (settings.w_bj, b_bj),
        (settings.w_liquidity, b_liq),
        (settings.w_smc, b_smc),
        (settings.w_pullback, b_pb),
        (settings.w_ichimoku, b_ichi),
    ]
    bear_flags = [
        (settings.w_bj, s_bj),
        (settings.w_liquidity, s_liq),
        (settings.w_smc, s_smc),
        (settings.w_pullback, s_pb),
        (settings.w_ichimoku, s_ichi),
    ]
    bull_score, bear_score, net = _vote_score(bull_flags, bear_flags)

    adx_v = _adx_series(out)
    adx_ok = adx_v >= settings.adx_min if settings.use_adx else pd.Series(True, index=out.index)

    out["tf_bj_bull"] = b_bj
    out["tf_bj_bear"] = s_bj
    out["tf_liq_bull"] = b_liq
    out["tf_liq_bear"] = s_liq
    out["tf_smc_bull"] = b_smc
    out["tf_smc_bear"] = s_smc
    out["tf_pb_bull"] = b_pb
    out["tf_pb_bear"] = s_pb
    out["tf_ichi_bull"] = b_ichi
    out["tf_ichi_bear"] = s_ichi
    out["trend_bull_score"] = bull_score
    out["trend_bear_score"] = bear_score
    out["trend_score"] = net
    out["adx"] = adx_v
    out["adx_ok"] = adx_ok

    out["trend_bull"] = (net >= settings.min_score_long) & adx_ok
    out["trend_bear"] = (-net >= settings.min_score_short) & adx_ok
    out["trend_neutral"] = net.abs() < settings.neutral_band
    out["trend_label"] = np.where(
        out["trend_bull"],
        "bull",
        np.where(out["trend_bear"], "bear", "neutral"),
    )
    out["allow_long"] = out["trend_bull"]
    out["allow_short"] = out["trend_bear"]
    out["trend_preset"] = settings.name
    return out


def _df_with_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.index, pd.DatetimeIndex):
        return out
    if "timestamp" in out.columns:
        out = out.set_index(pd.to_datetime(out["timestamp"], utc=True))
    return out


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample OHLCV using timestamp column."""
    d = df.copy()
    if "timestamp" not in d.columns:
        d = _df_with_index(d).reset_index()
        if d.columns[0] != "timestamp":
            d = d.rename(columns={d.columns[0]: "timestamp"})
    d = d.set_index(pd.to_datetime(d["timestamp"], utc=True))
    agg = d.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    out = agg.reset_index()
    if out.columns[0] != "timestamp":
        out = out.rename(columns={out.columns[0]: "timestamp"})
    return out


def htf_trend_gate(
    chart_df: pd.DataFrame,
    market: Market,
    trend_rule: str = "both_agree",
    block_4h_counter: bool = True,
    h1_df: pd.DataFrame | None = None,
    h4_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    1h + 4h trend gate aligned to chart bars (Monster Trex HTF style).
    """
    base = chart_df.copy()
    chart = _df_with_index(base)
    n = len(chart)
    if "timestamp" not in base.columns and isinstance(chart.index, pd.DatetimeIndex):
        base = chart.reset_index()
        if base.columns[0] != "timestamp":
            base = base.rename(columns={base.columns[0]: "timestamp"})

    if not isinstance(chart.index, pd.DatetimeIndex) and "timestamp" not in base.columns:
        return pd.DataFrame(
            {
                "htf_allow_long": np.ones(n, dtype=bool),
                "htf_allow_short": np.ones(n, dtype=bool),
                "h1_bull": np.zeros(n, dtype=bool),
                "h4_bull": np.zeros(n, dtype=bool),
                "h1_score": np.zeros(n),
                "h4_score": np.zeros(n),
            }
        )

    if not isinstance(chart.index, pd.DatetimeIndex):
        chart = base.set_index(pd.to_datetime(base["timestamp"], utc=True))

    h1_src = h1_df if h1_df is not None and len(h1_df) > 0 else resample_ohlcv(base, "1h")
    h4_src = h4_df if h4_df is not None and len(h4_df) > 0 else resample_ohlcv(base, "4h")
    if len(h1_src) < 30 or len(h4_src) < 10:
        return pd.DataFrame(
            {
                "htf_allow_long": np.zeros(n, dtype=bool),
                "htf_allow_short": np.zeros(n, dtype=bool),
                "h1_bull": np.zeros(n, dtype=bool),
                "h4_bull": np.zeros(n, dtype=bool),
                "h1_score": np.zeros(n),
                "h4_score": np.zeros(n),
            }
        )

    t1 = apply_trend_filter(h1_src, preset=f"{market}_1h", market=market)
    t4 = apply_trend_filter(h4_src, preset=f"{market}_4h", market=market)

    h1_idx = pd.to_datetime(h1_src["timestamp"], utc=True)
    h4_idx = pd.to_datetime(h4_src["timestamp"], utc=True)

    def _align(series: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
        s = pd.Series(series.values, index=idx)
        return s.reindex(chart.index, method="ffill").fillna(False)

    h1_long = _align(t1["allow_long"], h1_idx)
    h1_short = _align(t1["allow_short"], h1_idx)
    h4_long = _align(t4["allow_long"], h4_idx)
    h4_short = _align(t4["allow_short"], h4_idx)
    h1_net = _align(t1["trend_score"], h1_idx).astype(float).fillna(0)
    h4_net = _align(t4["trend_score"], h4_idx).astype(float).fillna(0)

    if trend_rule == "4h_lead":
        allow_long = h4_long & ~h4_short
        allow_short = h4_short & ~h4_long
    elif trend_rule == "1h_lead":
        allow_long = h1_long & ~h1_short
        allow_short = h1_short & ~h1_long
    else:
        allow_long = h1_long & h4_long
        allow_short = h1_short & h4_short

    if block_4h_counter:
        allow_long = allow_long & ~h4_short
        allow_short = allow_short & ~h4_long

    return pd.DataFrame(
        {
            "htf_allow_long": allow_long.values,
            "htf_allow_short": allow_short.values,
            "h1_bull": h1_long.values,
            "h4_bull": h4_long.values,
            "h1_score": h1_net.values,
            "h4_score": h4_net.values,
        }
    )


def filter_signals_df(
    sig: pd.DataFrame,
    trend: pd.DataFrame,
    require_trend: bool = True,
    long_col: str = "allow_long",
    short_col: str = "allow_short",
) -> pd.DataFrame:
    """Gate buy/sell with trend columns."""
    out = sig.copy()
    if not require_trend:
        return out
    long_ok = trend[long_col] if long_col in trend.columns else trend["htf_allow_long"]
    short_ok = trend[short_col] if short_col in trend.columns else trend["htf_allow_short"]
    if "buy" in out.columns:
        out["buy"] = out["buy"].fillna(False) & pd.Series(long_ok).fillna(False).values
    if "sell" in out.columns:
        out["sell"] = out["sell"].fillna(False) & pd.Series(short_ok).fillna(False).values
    return out


def trend_summary(trend: pd.DataFrame) -> dict:
    """Snapshot of latest trend state for dashboards."""
    if trend.empty:
        return {"label": "unknown"}
    last = trend.iloc[-1]
    return {
        "preset": str(last.get("trend_preset", "")),
        "label": str(last.get("trend_label", "neutral")),
        "score": round(float(last.get("trend_score", 0)), 3),
        "adx": round(float(last.get("adx", 0)), 2),
        "allow_long": bool(last.get("allow_long", False)),
        "allow_short": bool(last.get("allow_short", False)),
        "components": {
            "bj": bool(last.get("tf_bj_bull", False)) if last.get("trend_score", 0) >= 0 else bool(last.get("tf_bj_bear", False)),
            "liquidity": bool(last.get("tf_liq_bull", False)),
            "smc": bool(last.get("tf_smc_bull", False)),
            "pullback": bool(last.get("tf_pb_bull", False)),
            "ichimoku": bool(last.get("tf_ichi_bull", False)),
        },
    }
