"""Monster Trex Vol — Python port with HTF trend filter prerequisite.

Approximates the Pine strategy (structure HTF levels + FTC/RTP trigger entries)
and gates all entries through 1h+4h trend filter (both_agree).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from extra_indicators import liquidity_shift_signals
from indicators import atr_wilder
from trend_filter import apply_trend_filter, filter_signals_df, htf_trend_gate, resample_ohlcv, _df_with_index, resample_ohlcv
from zone_engine import pivot_high, pivot_low

PAIR_MODES = {
    "H1_M5": {"structure": "1h", "trigger": "5m", "pivot_len": 8, "trend_rule": "1h_lead"},
    "H4_M15": {"structure": "4h", "trigger": "15m", "pivot_len": 10, "trend_rule": "4h_lead"},
}

PIVOT_REVERSE = 2  # mse.PIVOT_REVERSE equivalent


@dataclass
class WatchedLevel:
    birth_time: pd.Timestamp
    pivot_price: float
    zone_top: float
    zone_bot: float
    ftc_top: float
    ftc_bot: float
    is_high: bool
    th: float
    score: int
    ftc_spent: bool = False
    broken: bool = False
    traded: bool = False
    sm_ok: bool = True


def _price_in_zone(hi: float, lo: float, z_top: float, z_bot: float) -> bool:
    return lo <= z_top and hi >= z_bot


def _zone_bounds(
    highs: np.ndarray,
    lows: np.ndarray,
    opens: np.ndarray,
    closes: np.ndarray,
    pivot_bar: int,
    is_supply: bool,
) -> tuple[float, float]:
    o, h, l, c = opens[pivot_bar], highs[pivot_bar], lows[pivot_bar], closes[pivot_bar]
    body_hi = max(o, c)
    body_lo = min(o, c)
    if is_supply:
        top = max(h, body_hi)
        bot = min(body_lo, (h + l) / 2)
    else:
        top = max(body_hi, (h + l) / 2)
        bot = min(l, body_lo)
    if top <= bot:
        top, bot = h, l
    return float(top), float(bot)


def _ftc_zone(zone_top: float, zone_bot: float, is_high: bool) -> tuple[float, float]:
    span = zone_top - zone_bot
    if span <= 0:
        return zone_top, zone_bot
    if is_high:
        ftc_top = zone_top
        ftc_bot = zone_top - span * 0.45
    else:
        ftc_bot = zone_bot
        ftc_top = zone_bot + span * 0.45
    return ftc_top, ftc_bot


def _structure_score(
    closes: np.ndarray,
    volumes: np.ndarray,
    pivot_bar: int,
    is_high: bool,
    atr_v: float,
) -> int:
    if pivot_bar < 5:
        return 0
    move = abs(closes[pivot_bar] - closes[pivot_bar - 5])
    vol_ratio = 1.0
    if len(volumes) > pivot_bar and volumes[pivot_bar - 5 : pivot_bar + 1].mean() > 0:
        vol_ratio = volumes[pivot_bar] / max(volumes[pivot_bar - 5 : pivot_bar].mean(), 1e-9)
    base = int(min(100, (move / max(atr_v, 1e-9)) * 25 + vol_ratio * 15))
    return base


def _spawn_levels(struct_df: pd.DataFrame, pivot_len: int, min_score: int) -> list[WatchedLevel]:
    """Detect structure levels from HTF pivots (demand/supply zones)."""
    out = struct_df.copy()
    if "timestamp" not in out.columns:
        out = out.reset_index()
        if out.columns[0] != "timestamp":
            out = out.rename(columns={out.columns[0]: "timestamp"})
    ts = pd.to_datetime(out["timestamp"], utc=True)
    highs = out["high"].values
    lows = out["low"].values
    opens = out["open"].values
    closes = out["close"].values
    vols = out["volume"].values if "volume" in out.columns else np.ones(len(out))
    atr_s = atr_wilder(out, 14).values
    ph = pivot_high(out["high"], pivot_len, pivot_len).values
    pl = pivot_low(out["low"], pivot_len, pivot_len).values
    n = len(out)
    levels: list[WatchedLevel] = []

    for i in range(pivot_len * 2, n):
        atr_v = float(atr_s[i]) if not np.isnan(atr_s[i]) else closes[i] * 0.005

        if not np.isnan(ph[i]):
            pbar = i - pivot_len
            z_top, z_bot = _zone_bounds(highs, lows, opens, closes, pbar, True)
            sc = _structure_score(closes, vols, pbar, True, atr_v)
            if sc >= min_score and z_top > z_bot:
                ftc_t, ftc_b = _ftc_zone(z_top, z_bot, True)
                levels.append(
                    WatchedLevel(
                        birth_time=ts.iloc[i],
                        pivot_price=float(highs[pbar]),
                        zone_top=z_top,
                        zone_bot=z_bot,
                        ftc_top=ftc_t,
                        ftc_bot=ftc_b,
                        is_high=True,
                        th=atr_v,
                        score=sc,
                        sm_ok=True,
                    )
                )

        if not np.isnan(pl[i]):
            pbar = i - pivot_len
            z_top, z_bot = _zone_bounds(highs, lows, opens, closes, pbar, False)
            sc = _structure_score(closes, vols, pbar, False, atr_v)
            if sc >= min_score and z_top > z_bot:
                ftc_t, ftc_b = _ftc_zone(z_top, z_bot, False)
                levels.append(
                    WatchedLevel(
                        birth_time=ts.iloc[i],
                        pivot_price=float(lows[pbar]),
                        zone_top=z_top,
                        zone_bot=z_bot,
                        ftc_top=ftc_t,
                        ftc_bot=ftc_b,
                        is_high=False,
                        th=atr_v,
                        score=sc,
                        sm_ok=True,
                    )
                )

    return levels[-40:]


def _structure_trend_gate(
    trigger_df: pd.DataFrame,
    struct_df: pd.DataFrame,
    market: str,
    struct_tf: str,
) -> pd.DataFrame:
    """Align structure-TF trend bias to trigger bars (Monster Trex prerequisite)."""
    preset_map = {"1h": f"{market}_1h", "4h": f"{market}_4h"}
    preset = preset_map.get(struct_tf, f"{market}_1h")
    t = apply_trend_filter(struct_df, preset=preset, market=market)  # type: ignore[arg-type]
    chart = _df_with_index(trigger_df)
    n = len(trigger_df)
    if "timestamp" not in struct_df.columns:
        sidx = pd.to_datetime(struct_df.index, utc=True)
    else:
        sidx = pd.to_datetime(struct_df["timestamp"], utc=True)
    long_s = pd.Series(t["allow_long"].values, index=sidx)
    short_s = pd.Series(t["allow_short"].values, index=sidx)
    if not isinstance(chart.index, pd.DatetimeIndex):
        chart = _df_with_index(trigger_df)
    long_a = long_s.reindex(chart.index, method="ffill").fillna(False)
    short_a = short_s.reindex(chart.index, method="ffill").fillna(False)
    return pd.DataFrame(
        {
            "htf_allow_long": long_a.values[:n],
            "htf_allow_short": short_a.values[:n],
        }
    )


def _sm_confluence(liq_buy: bool, liq_sell: bool, is_high: bool, min_sm: int = 1) -> bool:
    if min_sm <= 0:
        return True
    cnt = int(liq_sell) if is_high else int(liq_buy)
    return cnt >= min_sm


def monster_trex_signals(
    trigger_df: pd.DataFrame,
    chart_tf: str = "5m",
    market: str = "crypto",
    pair_mode: str = "H1_M5",
    min_score: int = 40,
    min_sm: int = 0,
    use_ftc: bool = True,
    sl_th_mult: float = 0.5,
    tp_th_mult: float = 3.0,
    use_trend_filter: bool = True,
    trend_rule: str | None = None,
    struct_df: pd.DataFrame | None = None,
    h1_df: pd.DataFrame | None = None,
    h4_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Generate Monster Trex Vol entries on trigger TF with optional HTF trend gate.

    Trend filter is a hard prerequisite: long only when 1h+4h bullish, short when both bearish.
    """
    cfg = PAIR_MODES.get(pair_mode, PAIR_MODES["H1_M5"])
    if chart_tf != cfg["trigger"]:
        pass  # caller may pass mismatched tf; still run

    out = trigger_df.copy()
    if "timestamp" not in out.columns:
        out = out.reset_index()
        if out.columns[0] != "timestamp":
            out = out.rename(columns={out.columns[0]: "timestamp"})
    ts = pd.to_datetime(out["timestamp"], utc=True)
    n = len(out)
    highs = out["high"].values
    lows = out["low"].values
    opens = out["open"].values
    closes = out["close"].values

    eff_min = max(min_score, 35) if market == "crypto" else min_score

    if struct_df is not None and len(struct_df) > 0:
        struct_src = struct_df
    else:
        struct_src = resample_ohlcv(out, cfg["structure"])

    levels = _spawn_levels(struct_src, cfg["pivot_len"], eff_min)
    liq = liquidity_shift_signals(out)

    buy = np.zeros(n, dtype=bool)
    sell = np.zeros(n, dtype=bool)
    sl_p = np.full(n, np.nan)
    tp_p = np.full(n, np.nan)
    entry_p = np.full(n, np.nan)

    active: list[WatchedLevel] = []

    for i in range(1, n):
        bar_ts = ts.iloc[i]
        # Add levels whose birth_time <= current bar
        for lv in levels:
            if lv.birth_time <= bar_ts and lv not in active:
                active.append(lv)
        if len(active) > 40:
            active = active[-40:]

        hi, lo = float(highs[i]), float(lows[i])
        prev_hi, prev_lo = float(highs[i - 1]), float(lows[i - 1])
        close = float(closes[i])

        for lv in active:
            if lv.broken or lv.traded:
                continue
            if not lv.sm_ok:
                continue

            # Break detection
            if lv.is_high and close > lv.zone_top:
                lv.broken = True
                continue
            if not lv.is_high and close < lv.zone_bot:
                lv.broken = True
                continue

            # Mark FTC spent
            if not lv.ftc_spent and _price_in_zone(hi, lo, lv.ftc_top, lv.ftc_bot):
                if not _price_in_zone(prev_hi, prev_lo, lv.ftc_top, lv.ftc_bot):
                    lv.ftc_spent = True

            sm_ok = _sm_confluence(
                bool(liq["buy"].iloc[i]),
                bool(liq["sell"].iloc[i]),
                lv.is_high,
                min_sm,
            )
            if not sm_ok:
                continue

            ent_long = False
            ent_short = False
            # FTC first-touch entry (Monster Trex trigger)
            if use_ftc and not lv.traded:
                in_ftc = _price_in_zone(hi, lo, lv.ftc_top, lv.ftc_bot)
                was_in_ftc = _price_in_zone(prev_hi, prev_lo, lv.ftc_top, lv.ftc_bot)
                if in_ftc and not was_in_ftc:
                    if not lv.is_high and close > opens[i]:
                        ent_long = True
                    elif lv.is_high and close < opens[i]:
                        ent_short = True

            if ent_long:
                pad = lv.th * sl_th_mult
                tp_dist = lv.th * tp_th_mult
                buy[i] = True
                entry_p[i] = close
                sl_p[i] = lv.zone_bot - pad
                tp_p[i] = lv.pivot_price + tp_dist
                lv.traded = True
            elif ent_short:
                pad = lv.th * sl_th_mult
                tp_dist = lv.th * tp_th_mult
                sell[i] = True
                entry_p[i] = close
                sl_p[i] = lv.zone_top + pad
                tp_p[i] = lv.pivot_price - tp_dist
                lv.traded = True

    out["buy"] = buy
    out["sell"] = sell
    out["entry_price"] = entry_p
    out["sl_price"] = sl_p
    out["tp_price"] = tp_p

    if use_trend_filter:
        if struct_src is not None and len(struct_src) > 30:
            gate = _structure_trend_gate(out, struct_src, market, cfg["structure"])
        else:
            rule = trend_rule or cfg.get("trend_rule", "1h_lead")
            gate = htf_trend_gate(
                out,
                market=market,  # type: ignore[arg-type]
                trend_rule=rule,
                h1_df=h1_df,
                h4_df=h4_df,
            )
        out = filter_signals_df(
            out,
            gate,
            require_trend=True,
            long_col="htf_allow_long",
            short_col="htf_allow_short",
        )
        out["htf_allow_long"] = gate["htf_allow_long"].values
        out["htf_allow_short"] = gate["htf_allow_short"].values

    return out
