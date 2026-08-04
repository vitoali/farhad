#!/usr/bin/env python3
"""
Improved Cardwell hybrid + sensitivity runs for Gold pip size.
Also fixes EWO volume handling for forex (zero volume).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from run_backtest import (
    DATA,
    OUT,
    TradeResult,
    adx,
    ema,
    flip_rate,
    load_df,
    mfi,
    pip_size,
    rsi,
    signals_cardwell,
    sma,
    summarize,
)

# Patch gold pip for sensitivity
GOLD_PIP_OVERRIDE: float | None = None


def sl_tp_levels_flex(symbol: str, entry: float, direction: int) -> tuple[float, float]:
    if symbol == "BTC":
        sl_dist = entry * 0.03
        tp_dist = entry * 0.05
    else:
        p = GOLD_PIP_OVERRIDE if (symbol == "XAU" and GOLD_PIP_OVERRIDE) else pip_size(symbol)
        sl_dist = 5 * p
        tp_dist = 5 * p
    if direction == 1:
        return entry - sl_dist, entry + tp_dist
    return entry + sl_dist, entry - tp_dist


def backtest_flex(df, signals, symbol, tf, indicator, max_hold_bars=None):
    # copy of backtest using flex SL/TP
    trades: list[TradeResult] = []
    i = 0
    n = len(df)
    if max_hold_bars is None:
        max_hold_bars = {"5m": 288 * 3, "15m": 96 * 3, "1h": 24 * 7, "4h": 6 * 14}.get(tf, 500)
    while i < n:
        s = int(signals.iloc[i])
        if s == 0:
            i += 1
            continue
        entry = float(df["Close"].iloc[i])
        direction = s
        sl, tp = sl_tp_levels_flex(symbol, entry, direction)
        entry_time = str(df.index[i])
        exit_idx = None
        outcome = "timeout"
        exit_price = float(df["Close"].iloc[min(i + max_hold_bars, n - 1)])
        for j in range(i + 1, min(i + max_hold_bars + 1, n)):
            hi = float(df["High"].iloc[j])
            lo = float(df["Low"].iloc[j])
            if direction == 1:
                hit_sl, hit_tp = lo <= sl, hi >= tp
            else:
                hit_sl, hit_tp = hi >= sl, lo <= tp
            if hit_sl and hit_tp:
                outcome, exit_price, exit_idx = "loss", sl, j
                break
            if hit_sl:
                outcome, exit_price, exit_idx = "loss", sl, j
                break
            if hit_tp:
                outcome, exit_price, exit_idx = "win", tp, j
                break
        if exit_idx is None:
            exit_idx = min(i + max_hold_bars, n - 1)
            exit_price = float(df["Close"].iloc[exit_idx])
            outcome = "timeout"
        trades.append(
            TradeResult(
                symbol=symbol,
                tf=tf,
                indicator=indicator,
                direction=direction,
                entry_time=entry_time,
                exit_time=str(df.index[exit_idx]),
                entry=entry,
                exit=exit_price,
                sl=sl,
                tp=tp,
                outcome=outcome,
                bars_held=exit_idx - i,
            )
        )
        i = exit_idx + 1
    return trades


def signals_ewo_rsi_fixed(df: pd.DataFrame) -> pd.Series:
    """EWO/RSI with volume optional when volume is missing/zero (forex)."""
    ewo = sma((df["High"] + df["Low"]) / 2, 5) - sma((df["High"] + df["Low"]) / 2, 34)
    r = rsi(df["Close"], 14)
    has_vol = (df["Volume"] > 0).sum() > len(df) * 0.5
    if has_vol:
        m = mfi(df, 14)
        vol_raw = df["Volume"].replace(0, np.nan).ffill().fillna(1)
        vol_ma = sma(vol_raw, 20)
        vol_ok = vol_raw > vol_ma * 0.8
    else:
        m = pd.Series(50.0, index=df.index)  # neutral MFI
        vol_ok = pd.Series(True, index=df.index)

    barrier = df["High"].rolling(10, min_periods=10).max().shift(1)
    breakout = df["Close"] > barrier

    last = 0
    out = np.zeros(len(df), dtype=int)
    active = False
    for i in range(len(df)):
        if r.iloc[i] < 30:
            active = True
        buy = (
            i > 0
            and (r.iloc[i] > 40)
            and (r.iloc[i - 1] <= 40)
            and (m.iloc[i] > 30)
            and (ewo.iloc[i] > ewo.iloc[i - 1])
            and bool(vol_ok.iloc[i])
            and (bool(breakout.iloc[i]) or active)
        )
        sell = (
            i > 0
            and (r.iloc[i] < 60)
            and (r.iloc[i - 1] >= 60)
            and (m.iloc[i] < 70)
            and (ewo.iloc[i] < ewo.iloc[i - 1])
            and bool(vol_ok.iloc[i])
        )
        if buy and last != 1:
            out[i] = 1
            last = 1
            active = False
        elif sell and last != -1:
            out[i] = -1
            last = -1
    return pd.Series(out, index=df.index, dtype=int)


def signals_cardwell_improved(
    df: pd.DataFrame,
    confirm_bars: int = 3,
    min_bars_between_flip: int = 8,
    use_macd: bool = True,
    use_adx: bool = True,
    adx_min: float = 20.0,
    use_ewo_turn: bool = True,
    htf_regime: pd.Series | None = None,
) -> pd.Series:
    """
    Cardwell core + borrowed strengths:
      - MACD direction agreement (from CM MACD)
      - ADX chop filter (built-in Cardwell, enabled)
      - EWO momentum turn confirmation (from EWO/RSI)
      - One-leg lock + min bars before opposite signal (anti-flip from EWO)
      - Optional HTF regime agreement
    Position SL/TP lock is handled in backtest (skip signals while in trade).
    """
    r = rsi(df["Close"], 14)
    ma = sma(df["Close"], 50)
    up = df["Close"] > ma
    down = df["Close"] < ma
    bull_raw = up & (r >= 40) & (r <= 80)
    bear_raw = down & (r >= 20) & (r <= 60)

    bull_cnt = bull_raw.astype(int).groupby((~bull_raw).cumsum()).cumsum()
    bear_cnt = bear_raw.astype(int).groupby((~bear_raw).cumsum()).cumsum()
    bull = bull_raw & (bull_cnt >= confirm_bars)
    bear = bear_raw & (bear_cnt >= confirm_bars)
    regime = pd.Series(0, index=df.index, dtype=int)
    regime = regime.mask(bull, 1).mask(bear, -1)
    prev = regime.shift(1).fillna(0).astype(int)

    raw_long = (regime == 1) & (prev != 1)
    raw_short = (regime == -1) & (prev != -1)

    # MACD filter
    if use_macd:
        macd_line = ema(df["Close"], 12) - ema(df["Close"], 26)
        signal = sma(macd_line, 9)
        macd_bull = macd_line > signal
        macd_bear = macd_line < signal
        raw_long = raw_long & macd_bull
        raw_short = raw_short & macd_bear

    # ADX chop filter
    if use_adx:
        a = adx(df, 14)
        chop_ok = a >= adx_min
        raw_long = raw_long & chop_ok
        raw_short = raw_short & chop_ok

    # EWO turn confirmation
    if use_ewo_turn:
        ewo = sma((df["High"] + df["Low"]) / 2, 5) - sma((df["High"] + df["Low"]) / 2, 34)
        ewo_up = ewo > ewo.shift(1)
        ewo_dn = ewo < ewo.shift(1)
        raw_long = raw_long & ewo_up
        raw_short = raw_short & ewo_dn

    # HTF regime
    if htf_regime is not None:
        h = htf_regime.reindex(df.index, method="ffill")
        raw_long = raw_long & (h == 1)
        raw_short = raw_short & (h == -1)

    # Anti-flip: one signal per leg + cooldown bars before opposite
    out = np.zeros(len(df), dtype=int)
    last_dir = 0
    last_i = -10_000
    for i in range(len(df)):
        want = 0
        if bool(raw_long.iloc[i]):
            want = 1
        elif bool(raw_short.iloc[i]):
            want = -1
        if want == 0:
            continue
        if want == last_dir:
            continue  # same leg — ignore
        if last_dir != 0 and (i - last_i) < min_bars_between_flip:
            continue  # cooldown vs flip
        out[i] = want
        last_dir = want
        last_i = i
    return pd.Series(out, index=df.index, dtype=int)


def cardwell_regime_series(df: pd.DataFrame, confirm_bars: int = 2) -> pd.Series:
    r = rsi(df["Close"], 14)
    ma = sma(df["Close"], 50)
    up = df["Close"] > ma
    down = df["Close"] < ma
    bull_raw = up & (r >= 40) & (r <= 80)
    bear_raw = down & (r >= 20) & (r <= 60)
    bull_cnt = bull_raw.astype(int).groupby((~bull_raw).cumsum()).cumsum()
    bear_cnt = bear_raw.astype(int).groupby((~bear_raw).cumsum()).cumsum()
    bull = bull_raw & (bull_cnt >= confirm_bars)
    bear = bear_raw & (bear_cnt >= confirm_bars)
    regime = pd.Series(0, index=df.index, dtype=int)
    return regime.mask(bull, 1).mask(bear, -1).fillna(0).astype(int)


def htf_map(symbol: str, tf: str) -> pd.Series | None:
    """Map LTF bars to higher-TF Cardwell regime."""
    htf = {"5m": "1h", "15m": "1h", "1h": "4h", "4h": None}.get(tf)
    if not htf:
        return None
    path = DATA / f"{symbol}_{htf}.csv"
    if not path.exists():
        return None
    hdf = load_df(symbol, htf)
    return cardwell_regime_series(hdf, confirm_bars=2)


def run() -> None:
    global GOLD_PIP_OVERRIDE
    symbols = ["BTC", "XAU", "EURUSD"]
    tfs = ["5m", "15m", "1h", "4h"]
    rows = []

    # 1) Gold sensitivity
    print("=== GOLD PIP SENSITIVITY (Cardwell) ===")
    for pip in [0.01, 0.1, 1.0, 5.0]:
        GOLD_PIP_OVERRIDE = pip
        for tf in tfs:
            df = load_df("XAU", tf)
            sig = signals_cardwell(df)
            trades = backtest_flex(df, sig, "XAU", tf, f"Cardwell_pip{pip}")
            st = summarize(trades)
            st.update({"symbol": "XAU", "tf": tf, "indicator": f"Cardwell_pip{pip}", "pip": pip})
            rows.append(st)
            print(f"  pip={pip} {tf}: trades={st['trades']} WR={st['win_rate']}% avgBars={st['avg_bars']}")
    GOLD_PIP_OVERRIDE = None

    # 2) EWO fixed for EURUSD
    print("\n=== EWO_RSI FIXED (volume-optional) ===")
    for symbol in symbols:
        for tf in tfs:
            df = load_df(symbol, tf)
            if symbol == "XAU":
                GOLD_PIP_OVERRIDE = 1.0  # practical gold pip=$1 for comparison
            else:
                GOLD_PIP_OVERRIDE = None
            sig = signals_ewo_rsi_fixed(df)
            trades = backtest_flex(df, sig, symbol, tf, "EWO_RSI_fixed")
            st = summarize(trades)
            fr = flip_rate(sig, window={"5m": 6, "15m": 4, "1h": 3, "4h": 2}[tf])
            st.update(
                {
                    "symbol": symbol,
                    "tf": tf,
                    "indicator": "EWO_RSI_fixed",
                    "flip_within_N": fr,
                }
            )
            rows.append(st)
            print(
                f"  {symbol} {tf}: trades={st['trades']} WR={st['win_rate']}% flip={fr}"
            )
    GOLD_PIP_OVERRIDE = None

    # 3) Improved Cardwell vs baseline (use gold pip=1.0)
    print("\n=== CARDWELL BASELINE vs IMPROVED ===")
    for symbol in symbols:
        for tf in tfs:
            df = load_df(symbol, tf)
            if symbol == "XAU":
                GOLD_PIP_OVERRIDE = 1.0
            else:
                GOLD_PIP_OVERRIDE = None

            # cooldown scales with TF
            cooldown = {"5m": 12, "15m": 8, "1h": 4, "4h": 2}[tf]
            confirm = {"5m": 3, "15m": 3, "1h": 2, "4h": 2}[tf]
            htf = htf_map(symbol, tf)

            base = signals_cardwell(df)
            improved = signals_cardwell_improved(
                df,
                confirm_bars=confirm,
                min_bars_between_flip=cooldown,
                use_macd=True,
                use_adx=True,
                adx_min=18 if tf in ("5m", "15m") else 20,
                use_ewo_turn=True,
                htf_regime=htf if tf in ("5m", "15m") else None,
            )

            for name, sig in [("Cardwell_base", base), ("Cardwell_improved", improved)]:
                trades = backtest_flex(df, sig, symbol, tf, name)
                st = summarize(trades)
                fr = flip_rate(sig, window={"5m": 6, "15m": 4, "1h": 3, "4h": 2}[tf])
                st.update(
                    {
                        "symbol": symbol,
                        "tf": tf,
                        "indicator": name,
                        "flip_within_N": fr,
                    }
                )
                rows.append(st)
                print(
                    f"  {symbol} {tf} {name}: trades={st['trades']} "
                    f"WR={st['win_rate']}% WRres={st['win_rate_resolved']}% "
                    f"flip={fr} W/L/T={st['wins']}/{st['losses']}/{st['timeouts']}"
                )
    GOLD_PIP_OVERRIDE = None

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT / "improved_comparison.csv", index=False)
    (OUT / "improved_comparison.json").write_text(out_df.to_json(orient="records", indent=2))
    print("\nWrote improved_comparison.csv")


if __name__ == "__main__":
    run()
