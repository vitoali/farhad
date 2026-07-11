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


# ---------------------------------------------------------------------------
# #5 FibFib / AutoFib — rolling Fibonacci retracement zones
# ---------------------------------------------------------------------------

def fib_fib_levels(df: pd.DataFrame, fiblength: int = 265) -> pd.DataFrame:
    out = df.copy()
    maxr = out["close"].rolling(fiblength).max()
    minr = out["close"].rolling(fiblength).min()
    ranr = maxr - minr
    out["fib_max"] = maxr
    out["fib_min"] = minr
    out["fib_range"] = ranr
    out["fib_786"] = maxr - 0.236 * ranr  # 0.764 from bottom
    out["fib_618"] = maxr - 0.382 * ranr  # golden ratio
    out["fib_500"] = maxr - 0.50 * ranr
    out["fib_382"] = minr + 0.382 * ranr
    out["fib_236"] = minr + 0.236 * ranr
    return out


def fib_fib_signals(df: pd.DataFrame, fiblength: int = 265, touch_pct: float = 0.003, cooldown: int = 10) -> pd.DataFrame:
    """
    Zone touch + bounce/rejection at key Fib levels (no native signals in Pine).
    Long: low touches support fib, close bounces above.
    Short: high touches resistance fib, close rejects below.
    """
    out = fib_fib_levels(df, fiblength)
    n = len(out)
    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    touch_level = [""] * n

    supports = ["fib_618", "fib_500", "fib_382"]
    resists = ["fib_618", "fib_786", "fib_max"]

    lows = out["low"].values
    highs = out["high"].values
    closes = out["close"].values
    opens = out["open"].values
    ranges = out["fib_range"].values

    last_sig = -cooldown - 1
    for i in range(fiblength, n):
        if i - last_sig < cooldown:
            continue
        if np.isnan(ranges[i]) or ranges[i] <= 0:
            continue
        tol = max(ranges[i] * touch_pct, closes[i] * 0.001)

        for lvl in supports:
            level = out[lvl].iloc[i]
            if np.isnan(level):
                continue
            if lows[i] <= level + tol and closes[i] > level and closes[i] > opens[i]:
                buy[i] = True
                touch_level[i] = lvl
                last_sig = i
                break

        if buy[i]:
            continue

        for lvl in resists:
            level = out[lvl].iloc[i]
            if np.isnan(level):
                continue
            if highs[i] >= level - tol and closes[i] < level and closes[i] < opens[i]:
                sell[i] = True
                touch_level[i] = lvl
                last_sig = i
                break

    out["buy"] = buy
    out["sell"] = sell
    out["touch_level"] = touch_level
    return out


# ---------------------------------------------------------------------------
# #6 Quadapt ML Trader — envelope compression breakout (core signals)
# ---------------------------------------------------------------------------

def _synth_b(close: pd.Series, ema_close: pd.Series, length: int) -> pd.Series:
    """Unused legacy helper — envelope uses inline synth in _envelope_side."""
    base_ds = (close - ema_close).abs()
    nd = base_ds / ema_close.abs().clip(lower=1e-8)
    x = 0.68 * nd.pow(2) + 0.79 * nd + nd
    synth = np.sin(x) * np.cos(x)
    return synth.abs() * ema_close.abs().clip(lower=1e-8)


def _envelope_side(close: pd.Series, length: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_close = ema(close, length)
    b = _synth_b(close, ema_close, length)
    d = b.ewm(span=length, adjust=False).mean()
    upper = ema_close + d
    lower = ema_close - d
    smooth_u = pd.Series(np.maximum(upper, close), index=close.index).ewm(span=length, adjust=False).mean()
    smooth_l = pd.Series(np.minimum(close, lower), index=close.index).ewm(span=length, adjust=False).mean()
    return smooth_u, smooth_l, ema_close


def quadapt_signals(
    df: pd.DataFrame,
    len1: int = 120,
    len2: int = 70,
    enable_dual: bool = True,
    consensus: str = "Independent",
    strong_only: bool = False,
) -> pd.DataFrame:
    """Simplified port of Quadapt envelope signals (MLMA/OB/quality engine omitted)."""
    out = df.copy()
    close = out["close"]
    rsi_14 = rsi(close, 14)

    def side_signals(length: int) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        smooth_u, smooth_l, ema_c = _envelope_side(close, length)
        rp = max(1, length // 5)
        rising_l = smooth_l.diff().rolling(rp).min() > 0
        falling_u = smooth_u.diff().rolling(rp).max() < 0
        wedge = rising_l & falling_u
        rng = smooth_u - smooth_l
        falling_rng = rng.diff().rolling(length).max() < 0
        falling_ended = falling_rng.shift(1).fillna(False) & ~falling_rng
        buy = falling_ended & (close > smooth_l) & ~wedge
        sell = falling_ended & (close < smooth_u) & ~wedge
        strong_buy = buy & (close > ema_c) & (rsi_14 < 70)
        strong_sell = sell & (close < ema_c) & (rsi_14 > 30)
        return buy, sell, strong_buy, strong_sell

    b1, s1, sb1, ss1 = side_signals(len1)
    if enable_dual:
        b2, s2, sb2, ss2 = side_signals(len2)
    else:
        b2 = s2 = sb2 = ss2 = pd.Series(False, index=close.index)

    if consensus == "Consensus" and enable_dual:
        buy = b1 & b2
        sell = s1 & s2
        strong_buy = sb1 & sb2
        strong_sell = ss1 & ss2
    elif consensus == "Primary Priority":
        buy, sell, strong_buy, strong_sell = b1, s1, sb1, ss1
    else:  # Independent
        buy = b1 | b2
        sell = s1 | s2
        strong_buy = sb1 | sb2
        strong_sell = ss1 | ss2

    if strong_only:
        out["buy"] = strong_buy
        out["sell"] = strong_sell
    else:
        out["buy"] = buy | strong_buy
        out["sell"] = sell | strong_sell

    # one signal per edge
    out["buy"] = out["buy"] & ~out["buy"].shift(1).fillna(False)
    out["sell"] = out["sell"] & ~out["sell"].shift(1).fillna(False)
    return out


# ---------------------------------------------------------------------------
# #7 SuperTrend
# ---------------------------------------------------------------------------

def supertrend_signals(
    df: pd.DataFrame,
    periods: int = 10,
    multiplier: float = 3.0,
    use_wilder_atr: bool = True,
    source_col: str = "hl2",
) -> pd.DataFrame:
    """Classic SuperTrend (Pine v4 port)."""
    out = df.copy()
    src = out[source_col] if source_col in out.columns else (out["high"] + out["low"]) / 2
    atr_v = atr_wilder(out, periods) if use_wilder_atr else true_range(out).rolling(periods).mean()

    up = np.zeros(len(out))
    dn = np.zeros(len(out))
    trend = np.ones(len(out), dtype=int)
    src_v = src.values
    close_v = out["close"].values
    atr_a = atr_v.values

    for i in range(len(out)):
        if np.isnan(atr_a[i]):
            if i > 0:
                up[i], dn[i], trend[i] = up[i - 1], dn[i - 1], trend[i - 1]
            continue
        up_i = src_v[i] - multiplier * atr_a[i]
        dn_i = src_v[i] + multiplier * atr_a[i]
        up1 = up[i - 1] if i > 0 else up_i
        dn1 = dn[i - 1] if i > 0 else dn_i
        if i > 0 and close_v[i - 1] > up1:
            up_i = max(up_i, up1)
        if i > 0 and close_v[i - 1] < dn1:
            dn_i = min(dn_i, dn1)
        up[i], dn[i] = up_i, dn_i
        prev_trend = trend[i - 1] if i > 0 else 1
        if prev_trend == -1 and close_v[i] > dn1:
            trend[i] = 1
        elif prev_trend == 1 and close_v[i] < up1:
            trend[i] = -1
        else:
            trend[i] = prev_trend

    buy = np.zeros(len(out), dtype=bool)
    sell = np.zeros(len(out), dtype=bool)
    for i in range(1, len(out)):
        buy[i] = trend[i] == 1 and trend[i - 1] == -1
        sell[i] = trend[i] == -1 and trend[i - 1] == 1

    out["trend"] = trend
    out["buy"] = buy
    out["sell"] = sell
    return out


# ---------------------------------------------------------------------------
# #8 Chandelier Exit
# ---------------------------------------------------------------------------

def chandelier_exit_signals(
    df: pd.DataFrame,
    length: int = 22,
    mult: float = 3.0,
    use_close: bool = True,
) -> pd.DataFrame:
    """Chandelier Exit (everget v6 port)."""
    out = df.copy()
    atr_v = mult * atr_wilder(out, length)
    hi_base = out["close"] if use_close else out["high"]
    lo_base = out["close"] if use_close else out["low"]
    highest = hi_base.rolling(length).max()
    lowest = lo_base.rolling(length).min()

    long_stop = np.zeros(len(out))
    short_stop = np.zeros(len(out))
    direction = np.ones(len(out), dtype=int)
    close_v = out["close"].values
    atr_a = atr_v.values
    hi_a = highest.values
    lo_a = lowest.values

    for i in range(len(out)):
        if np.isnan(atr_a[i]):
            if i > 0:
                long_stop[i], short_stop[i], direction[i] = long_stop[i - 1], short_stop[i - 1], direction[i - 1]
            continue
        ls = hi_a[i] - atr_a[i]
        ss = lo_a[i] + atr_a[i]
        ls_prev = long_stop[i - 1] if i > 0 else ls
        ss_prev = short_stop[i - 1] if i > 0 else ss
        if i > 0 and close_v[i - 1] > ls_prev:
            ls = max(ls, ls_prev)
        if i > 0 and close_v[i - 1] < ss_prev:
            ss = min(ss, ss_prev)
        long_stop[i], short_stop[i] = ls, ss
        if close_v[i] > ss_prev:
            direction[i] = 1
        elif close_v[i] < ls_prev:
            direction[i] = -1
        else:
            direction[i] = direction[i - 1] if i > 0 else 1

    buy = np.zeros(len(out), dtype=bool)
    sell = np.zeros(len(out), dtype=bool)
    for i in range(1, len(out)):
        buy[i] = direction[i] == 1 and direction[i - 1] == -1
        sell[i] = direction[i] == -1 and direction[i - 1] == 1

    out["dir"] = direction
    out["buy"] = buy
    out["sell"] = sell
    return out


# ---------------------------------------------------------------------------
# #9 Lorentzian Classification (simplified core KNN port)
# ---------------------------------------------------------------------------

def _cci(series: pd.Series, length: int = 20) -> pd.Series:
    tp = series
    sma_tp = sma(tp, length)
    mad = (tp - sma_tp).abs().rolling(length).mean()
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def _adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr = true_range(df)
    atr_v = pd.Series(tr, index=df.index).ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_v
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_v
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def _wave_trend(hlc3: pd.Series, channel: int = 10, avg: int = 11) -> pd.Series:
    esa = ema(hlc3, channel)
    de = ema((hlc3 - esa).abs(), channel)
    ci = (hlc3 - esa) / (0.015 * de.replace(0, np.nan))
    wt1 = ema(ci, avg)
    return wt1


def _norm_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    return rsi(close, length) / 100.0


def _norm_cci(close: pd.Series, length: int = 20) -> pd.Series:
    raw = _cci(close, length)
    return ((raw + 200) / 400).clip(0, 1)


def _norm_adx(df: pd.DataFrame, length: int = 20) -> pd.Series:
    return (_adx(df, length) / 100.0).clip(0, 1)


def _norm_wt(hlc3: pd.Series, channel: int = 10, avg: int = 11) -> pd.Series:
    raw = _wave_trend(hlc3, channel, avg)
    return ((raw + 100) / 200).clip(0, 1)


def lorentzian_signals(
    df: pd.DataFrame,
    neighbors_count: int = 8,
    max_bars_back: int = 500,
    feature_count: int = 5,
    use_kernel_filter: bool = False,
) -> pd.DataFrame:
    """Simplified Lorentzian KNN — core ANN + direction flip entries (filters off by default)."""
    out = df.copy()
    close = out["close"]
    hlc3 = (out["high"] + out["low"] + out["close"]) / 3

    f1 = _norm_rsi(close, 14).values
    f2 = _norm_wt(hlc3, 10, 11).values
    f3 = _norm_cci(close, 20).values
    f4 = _norm_adx(out, 20).values
    f5 = _norm_rsi(close, 9).values
    feats = [f1, f2, f3, f4, f5][:feature_count]
    src = close.values
    n = len(out)

    y_train = np.zeros(n, dtype=int)
    for i in range(n):
        if i + 4 < n:
            if src[i + 4] < src[i]:
                y_train[i] = -1
            elif src[i + 4] > src[i]:
                y_train[i] = 1

    prediction = np.zeros(n)
    signal = np.zeros(n, dtype=int)
    for bar in range(n):
        if bar < 50:
            continue
        start = max(0, bar - max_bars_back)
        last_dist = -1.0
        dists: list[float] = []
        preds: list[int] = []
        for i in range(start, bar):
            if i % 4 == 0:
                continue
            d = 0.0
            for f in feats:
                d += np.log1p(abs(f[bar] - f[i]))
            if d >= last_dist:
                last_dist = d
                dists.append(d)
                preds.append(int(y_train[i]))
                if len(preds) > neighbors_count:
                    q_idx = int(neighbors_count * 3 / 4)
                    last_dist = dists[q_idx] if q_idx < len(dists) else dists[-1]
                    dists.pop(0)
                    preds.pop(0)
        prediction[bar] = sum(preds)
        if prediction[bar] > 0:
            signal[bar] = 1
        elif prediction[bar] < 0:
            signal[bar] = -1
        else:
            signal[bar] = signal[bar - 1] if bar > 0 else 0

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    for i in range(1, n):
        sig_chg = signal[i] != signal[i - 1]
        if signal[i] == 1 and sig_chg:
            buy[i] = True
        if signal[i] == -1 and sig_chg:
            sell[i] = True

    out["prediction"] = prediction
    out["signal"] = signal
    out["buy"] = buy
    out["sell"] = sell
    return out
