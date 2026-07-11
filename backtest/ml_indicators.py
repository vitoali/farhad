"""Machine Learning RSI (Zeiierman) — port from machin_rsi_313b.txt."""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import atr_wilder, ema, rsi, sma


def _scale01(series: pd.Series, win_len: int) -> pd.Series:
    lo = series.rolling(win_len).min()
    hi = series.rolling(win_len).max()
    span = (hi - lo).replace(0, np.nan)
    return ((series - lo) / span).fillna(0.5)


def _percentrank(series: pd.Series, length: int) -> pd.Series:
    def pr(x: np.ndarray) -> float:
        if len(x) < 2:
            return 50.0
        return 100.0 * (np.sum(x[-1] >= x) - 1) / (len(x) - 1)

    return series.rolling(length).apply(pr, raw=True)


def _compress(d: float) -> float:
    return float(np.log1p(abs(d)))


def _gap_to(feat: np.ndarray, row: np.ndarray, w: np.ndarray) -> float:
    return sum(w[j] * _compress(feat[j] - row[j]) for j in range(8))


def ml_rsi_signals(
    df: pd.DataFrame,
    rsi_base: int = 14,
    memory_depth: int = 500,
    k_neighbors: int = 8,
    win_len: int = 100,
    spacing_bars: int = 4,
    horizon_bars: int = 4,
    gate_rank: int = 60,
    gate_conf: int = 50,
    use_trend_gate: bool = True,
    use_vol_band: bool = True,
    vol_band_lo: int = 20,
    vol_band_hi: int = 85,
    use_chop: bool = True,
    chop_cut: float = 0.5,
    atr_factor: float = 0.5,
    cool_bars: int = 5,
    st_mult_base: float = 1.5,
    st_atr_len: int = 10,
    st_ml_resp: float = 1.0,
    trend_len: int = 50,
    smooth_len: int = 10,
) -> pd.DataFrame:
    """Zeiierman ML RSI — 8-feature KNN bank + rank/confidence gates."""
    out = df.copy()
    close = out["close"]
    hl2 = (out["high"] + out["low"]) / 2
    n = len(out)

    r_osc = rsi(close, rsi_base)
    r_f = rsi(close, max(2, round(rsi_base / 2)))
    r_s = rsi(close, rsi_base * 2)
    atr_v = atr_wilder(out, 14)
    step = 3

    slope_raw = r_osc - r_osc.shift(step)
    accel_raw = slope_raw - slope_raw.shift(step)

    feat_val = (r_osc / 100.0).values
    feat_slp = _scale01(slope_raw, win_len).values
    feat_acc = _scale01(accel_raw, win_len).values
    feat_mid = (np.abs(r_osc - 50) / 50.0).values
    feat_pct = (_percentrank(r_osc, win_len) / 100.0).values
    feat_chn = _scale01(r_osc.rolling(14).std(), win_len).values
    feat_spr = _scale01(r_f - r_s, win_len).values
    feat_reg = _scale01(ema(r_osc, 20) - 50.0, win_len).values

    atr_a = atr_v.values
    close_v = close.values
    hl2_v = hl2.values

  # Feature bank: list of (features[8], outcome_class)
    bank: list[tuple[np.ndarray, int]] = []
    w_auto = np.ones(8)

    # Supertrend state
    st_long = np.full(n, np.nan)
    st_short = np.full(n, np.nan)
    st_dir = np.ones(n, dtype=int)

    stance_state = np.zeros(n, dtype=int)
    stance_age = np.zeros(n, dtype=int)
    conv_smooth = np.zeros(n)

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    last_entry = -999

    ema_trend = ema(close, trend_len).values
    ema_quick = ema(close, 5).values
    atr_pct_arr = _percentrank(atr_v, 100).values
    osc_reg = ema(r_osc, 20).values
    osc_smooth_up = ema(r_osc, 5).diff().values > 0

    for i in range(n):
        if i < horizon_bars + rsi_base * 2:
            continue

        # --- label & bank (confirmed bar) ---
        move_fwd = close_v[i] - close_v[i - horizon_bars]
        band_fwd = atr_factor * atr_a[i - horizon_bars] if not np.isnan(atr_a[i - horizon_bars]) else 0.001
        if move_fwd > 2 * band_fwd:
            outcome = 3
        elif move_fwd > band_fwd:
            outcome = 2
        elif move_fwd > 0:
            outcome = 1
        elif move_fwd < -2 * band_fwd:
            outcome = -3
        elif move_fwd < -band_fwd:
            outcome = -2
        elif move_fwd < 0:
            outcome = -1
        else:
            outcome = 0

        past_i = i - horizon_bars
        row_feat = np.array([
            feat_val[past_i], feat_slp[past_i], feat_acc[past_i], feat_mid[past_i],
            feat_pct[past_i], feat_chn[past_i], feat_spr[past_i], feat_reg[past_i],
        ])
        if not np.any(np.isnan(row_feat)):
            bank.insert(0, (row_feat, outcome))
            if len(bank) > memory_depth:
                bank.pop()

        cur = np.array([
            feat_val[i], feat_slp[i], feat_acc[i], feat_mid[i],
            feat_pct[i], feat_chn[i], feat_spr[i], feat_reg[i],
        ])
        if np.any(np.isnan(cur)):
            continue

        wts = w_auto.copy()

        # --- KNN vote ---
        neighbors: list[tuple[float, int]] = []
        for idx, (bfeat, bcls) in enumerate(bank):
            if idx % spacing_bars != 0:
                continue
            g = _gap_to(cur, bfeat, wts)
            if np.isnan(g):
                continue
            neighbors.append((g, bcls))
            neighbors.sort(key=lambda x: x[0])
            if len(neighbors) > k_neighbors:
                neighbors.pop()

        vote_score = 0.0
        vote_total = 0.0
        vote_bull = 0.0
        vote_bear = 0.0
        gap_sum = 0.0
        for g, cls in neighbors:
            w = 1.0 / (1.0 + g)
            vote_total += w
            vote_score += cls * w
            if cls > 0:
                vote_bull += w
            elif cls < 0:
                vote_bear += w
            gap_sum += g

        k_count = len(neighbors)
        analog_score = vote_score / vote_total if vote_total > 0 else 0.0
        if analog_score > 0.15:
            bias_dir = 1
        elif analog_score < -0.15:
            bias_dir = -1
        else:
            bias_dir = 0

        agree_frac = 0.0
        if vote_total > 0 and bias_dir != 0:
            agree_frac = (vote_bull if bias_dir == 1 else vote_bear) / vote_total

        w_sum = wts.sum()
        gap_scale = w_sum * 0.45 + 1e-9
        avg_gap = gap_sum / k_count if k_count > 0 else 0.0
        gap_tight = max(0.0, min(1.0, 1.0 - avg_gap / gap_scale))

        # --- ML adaptive supertrend ---
        conv_inst = max(-1.0, min(1.0, analog_score / 1.5))
        alpha = 2 / (smooth_len + 1)
        conv_smooth[i] = conv_inst if i == 0 else alpha * conv_inst + (1 - alpha) * conv_smooth[i - 1]

        ml_drive = max(0.0, min(1.0, abs(conv_smooth[i]) * 0.5 + gap_tight * 0.3 + agree_frac * 0.2))
        trend_force = abs(ema_quick[i] - ema_trend[i]) / atr_a[i] if atr_a[i] > 0 else 0.0
        chop_raw = trend_force < chop_cut
        chop_now = use_chop and chop_raw
        if chop_now:
            ml_drive *= 0.35

        adapt_mult = st_mult_base * (1.0 + st_ml_resp * (1.0 - ml_drive))
        st_atr = atr_wilder(out.iloc[: i + 1], st_atr_len).iloc[-1]
        if np.isnan(st_atr):
            st_atr = atr_a[i] if not np.isnan(atr_a[i]) else close_v[i] * 0.01

        up_band = hl2_v[i] - adapt_mult * st_atr
        dn_band = hl2_v[i] + adapt_mult * st_atr
        if i > 0 and not np.isnan(st_long[i - 1]):
            st_long[i] = max(up_band, st_long[i - 1]) if close_v[i - 1] > st_long[i - 1] else up_band
            st_short[i] = min(dn_band, st_short[i - 1]) if close_v[i - 1] < st_short[i - 1] else dn_band
        else:
            st_long[i], st_short[i] = up_band, dn_band

        if i > 0:
            prev = st_dir[i - 1]
            if prev == -1 and close_v[i] > st_short[i - 1]:
                st_dir[i] = 1
            elif prev == 1 and close_v[i] < st_long[i - 1]:
                st_dir[i] = -1
            else:
                st_dir[i] = prev
        else:
            st_dir[i] = 1

        up_trend = st_dir[i] == 1
        down_trend = st_dir[i] == -1
        atr_pct = atr_pct_arr[i] if not np.isnan(atr_pct_arr[i]) else 50.0
        vol_healthy = vol_band_lo <= atr_pct <= vol_band_hi
        r_now = r_osc.iloc[i]
        slope_up = r_now > r_osc.iloc[i - step] if i >= step else False
        slope_fit = (bias_dir == 1 and slope_up) or (bias_dir == -1 and not slope_up)
        stretched = (bias_dir == 1 and r_now > 70) or (bias_dir == -1 and r_now < 30)

        gates_pass = (
            (not use_trend_gate or (bias_dir == 1 and up_trend) or (bias_dir == -1 and down_trend))
            and (not use_vol_band or vol_healthy)
            and not chop_now
        )

        if bias_dir == 1 and gates_pass:
            stance_state[i] = 1
        elif bias_dir == -1 and gates_pass:
            stance_state[i] = -1
        elif i > 0:
            stance_state[i] = stance_state[i - 1]

        stance_changed = i > 0 and stance_state[i] != stance_state[i - 1]
        if stance_changed:
            stance_age[i] = 0
        elif i > 0:
            stance_age[i] = stance_age[i - 1] + 1

        early_flip = False
        if stance_changed and i >= 3:
            early_flip = (
                stance_state[i - 1] != stance_state[i - 2]
                or stance_state[i - 2] != stance_state[i - 3]
            )

        # rank / confidence
        aligned = (bias_dir == 1 and up_trend) or (bias_dir == -1 and down_trend)
        reg_fit = (bias_dir == 1 and osc_reg[i] > 55) or (bias_dir == -1 and osc_reg[i] < 45)
        age = stance_age[i]

        if bias_dir == 0:
            rank = conf = 0.0
        else:
            p_agree = 25.0 * agree_frac
            p_gap = 15.0 * gap_tight
            p_struct = (10.0 if slope_fit else 0.0) + (0.0 if stretched else 5.0)
            p_trend = 10.0 if aligned else 0.0
            p_vol = 10.0 if vol_healthy else (5.0 if atr_pct < vol_band_lo else 3.0)
            p_reg = 10.0 if reg_fit else (4.0 if 45 <= osc_reg[i] <= 55 else 6.0)
            p_smooth = 5.0 if ((bias_dir == 1 and osc_smooth_up[i]) or (bias_dir == -1 and not osc_smooth_up[i])) else 0.0
            p_hold = min(5.0, age)
            p_pen = min(20.0, (8.0 if chop_raw else 0.0) + (6.0 if stretched else 0.0) + (6.0 if early_flip else 0.0)
                          + (5.0 * (k_neighbors - k_count) / k_neighbors if k_count < k_neighbors else 0.0))
            rank = max(0.0, min(100.0, p_agree + p_gap + p_struct + p_trend + p_vol + p_reg + p_smooth + p_hold - p_pen))
            conf = max(0.0, min(100.0,
                40.0 * agree_frac + 25.0 * gap_tight + 15.0 * min(1.0, age / 5.0)
                + 10.0 * (1.0 if slope_fit else 0.0)
                - (15.0 if early_flip else 0.0)
                - (10.0 * (k_neighbors - k_count) / k_neighbors if k_count < k_neighbors else 0.0)
            ))

        flip_long = stance_state[i] == 1 and (i == 0 or stance_state[i - 1] != 1)
        flip_short = stance_state[i] == -1 and (i == 0 or stance_state[i - 1] != -1)
        qualifies = rank >= gate_rank and conf >= gate_conf
        cool_ok = last_entry < 0 or i - last_entry >= cool_bars

        if flip_long and qualifies and cool_ok:
            buy[i] = True
            last_entry = i
        if flip_short and qualifies and cool_ok:
            sell[i] = True
            last_entry = i

    out["buy"] = buy
    out["sell"] = sell
    out["ml_rsi"] = r_osc
    return out
