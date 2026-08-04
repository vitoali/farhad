#!/usr/bin/env python3
"""
Backtest Cardwell / MACD / EWO-RSI / Elliott-ZigZag signals
on BTC, XAU, EURUSD across 5m/15m/1h/4h.

Risk rules:
  BTC: SL 3%, TP 5%
  Others: SL 5 pips, TP 5 pips
    EURUSD pip = 0.0001
    XAU pip = 0.01
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data"
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

Symbol = Literal["BTC", "XAU", "EURUSD"]
TF = Literal["5m", "15m", "1h", "4h"]


# ── Indicators helpers ───────────────────────────────────────────
def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            (df["High"] - df["Low"]).abs(),
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


def mfi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    mf = tp * df["Volume"].clip(lower=0)
    direction = tp.diff()
    pos = mf.where(direction > 0, 0.0)
    neg = mf.where(direction < 0, 0.0)
    pos_sum = pos.rolling(length, min_periods=length).sum()
    neg_sum = neg.rolling(length, min_periods=length).sum()
    ratio = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + ratio))


def adx(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_v = tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(
        alpha=1 / length, min_periods=length, adjust=False
    ).mean() / atr_v
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(
        alpha=1 / length, min_periods=length, adjust=False
    ).mean() / atr_v
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    return dx.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()


# ── Signal generators ────────────────────────────────────────────
def signals_cardwell(df: pd.DataFrame) -> pd.Series:
    """Cardwell Range Analyze defaults: RSI14, SMA50, bull 40-80, bear 20-60, confirm 2."""
    r = rsi(df["Close"], 14)
    ma = sma(df["Close"], 50)
    up = df["Close"] > ma
    down = df["Close"] < ma
    bull_raw = up & (r >= 40) & (r <= 80)
    bear_raw = down & (r >= 20) & (r <= 60)

    bull_cnt = bull_raw.astype(int).groupby((~bull_raw).cumsum()).cumsum()
    bear_cnt = bear_raw.astype(int).groupby((~bear_raw).cumsum()).cumsum()
    bull = bull_raw & (bull_cnt >= 2)
    bear = bear_raw & (bear_cnt >= 2)
    regime = pd.Series(0, index=df.index, dtype=int)
    regime = regime.mask(bull, 1).mask(bear, -1)
    prev = regime.shift(1).fillna(0).astype(int)
    sig = pd.Series(0, index=df.index, dtype=int)
    sig = sig.mask((regime == 1) & (prev != 1), 1)
    sig = sig.mask((regime == -1) & (prev != -1), -1)
    return sig.fillna(0).astype(int)


def signals_macd(df: pd.DataFrame) -> pd.Series:
    macd_line = ema(df["Close"], 12) - ema(df["Close"], 26)
    signal = sma(macd_line, 9)  # CM script uses SMA of MACD
    cross_up = (macd_line > signal) & (macd_line.shift(1) <= signal.shift(1))
    cross_dn = (macd_line < signal) & (macd_line.shift(1) >= signal.shift(1))
    sig = pd.Series(0, index=df.index, dtype=int)
    sig = sig.mask(cross_up, 1).mask(cross_dn, -1)
    return sig.fillna(0).astype(int)


def signals_ewo_rsi(df: pd.DataFrame) -> pd.Series:
    ewo = sma((df["High"] + df["Low"]) / 2, 5) - sma((df["High"] + df["Low"]) / 2, 34)
    r = rsi(df["Close"], 14)
    m = mfi(df, 14)
    vol_raw = df["Volume"].replace(0, np.nan).ffill().fillna(1)
    vol_ma = sma(vol_raw, 20)
    vol = vol_raw.fillna(vol_ma)
    vol_ok = vol > vol_ma * 0.8
    oversold_zone = (r < 30).astype(int)
    # sticky oversold until buy — approximate with forward fill of events
    oz = pd.Series(False, index=df.index)
    active = False
    for i in range(len(df)):
        if r.iloc[i] < 30:
            active = True
        oz.iloc[i] = active
        # reset happens after buy; handled below

    barrier = df["High"].rolling(10, min_periods=10).max().shift(1)
    breakout = df["Close"] > barrier

    raw_buy = (r > 40) & (r.shift(1) <= 40) & (m > 30) & (ewo > ewo.shift(1)) & vol_ok & (breakout | oz)
    raw_sell = (r < 60) & (r.shift(1) >= 60) & (m < 70) & (ewo < ewo.shift(1)) & vol_ok

    last = 0
    out = np.zeros(len(df), dtype=int)
    active = False
    for i in range(len(df)):
        if r.iloc[i] < 30:
            active = True
        buy = bool(raw_buy.iloc[i])
        # recompute buy with sticky oversold
        if not buy:
            buy_cond = (
                (r.iloc[i] > 40)
                and (r.iloc[i - 1] <= 40 if i > 0 else False)
                and (m.iloc[i] > 30)
                and (ewo.iloc[i] > ewo.iloc[i - 1] if i > 0 else False)
                and bool(vol_ok.iloc[i])
                and (bool(breakout.iloc[i]) or active)
            )
            buy = buy_cond
        sell = bool(raw_sell.iloc[i])
        if buy and last != 1:
            out[i] = 1
            last = 1
            active = False
        elif sell and last != -1:
            out[i] = -1
            last = -1
    return pd.Series(out, index=df.index, dtype=int)


def zigzag_pivots(df: pd.DataFrame, length: int = 8) -> pd.Series:
    """Simplified Elliott proxy: confirmed swing pivots from rolling extremes."""
    highs = df["High"]
    lows = df["Low"]
    is_high = highs == highs.rolling(length * 2 + 1, center=True).max()
    is_low = lows == lows.rolling(length * 2 + 1, center=True).min()
    # Signal on pivot confirmation: after length bars of the pivot
    sig = pd.Series(0, index=df.index, dtype=int)
    # Confirm pivot at i when the center was length bars ago
    for i in range(length, len(df) - length):
        center = i
        window_h = highs.iloc[center - length : center + length + 1]
        window_l = lows.iloc[center - length : center + length + 1]
        if highs.iloc[center] >= window_h.max():
            # confirm sell at bar center+length
            conf = center + length
            if conf < len(df):
                sig.iloc[conf] = -1
        if lows.iloc[center] <= window_l.min():
            conf = center + length
            if conf < len(df):
                sig.iloc[conf] = 1
    # Keep last signal if both (rare)
    return sig.astype(int)


def signals_elliott(df: pd.DataFrame) -> pd.Series:
    """Use medium zigzag (len=8) direction flips as Elliott-style structure signals."""
    return zigzag_pivots(df, length=8)


SIGNAL_FNS = {
    "Cardwell": signals_cardwell,
    "MACD": signals_macd,
    "EWO_RSI": signals_ewo_rsi,
    "Elliott_ZZ": signals_elliott,
}


# ── Risk / backtest ──────────────────────────────────────────────
def pip_size(symbol: str) -> float:
    if symbol == "EURUSD":
        return 0.0001
    if symbol == "XAU":
        return 0.01
    return 1.0  # unused for BTC


def sl_tp_levels(symbol: str, entry: float, direction: int) -> tuple[float, float]:
    if symbol == "BTC":
        sl_dist = entry * 0.03
        tp_dist = entry * 0.05
    else:
        p = pip_size(symbol)
        sl_dist = 5 * p
        tp_dist = 5 * p
    if direction == 1:
        return entry - sl_dist, entry + tp_dist
    return entry + sl_dist, entry - tp_dist


@dataclass
class TradeResult:
    symbol: str
    tf: str
    indicator: str
    direction: int
    entry_time: str
    exit_time: str
    entry: float
    exit: float
    sl: float
    tp: float
    outcome: str  # win / loss / timeout
    bars_held: int


def backtest(
    df: pd.DataFrame,
    signals: pd.Series,
    symbol: str,
    tf: str,
    indicator: str,
    max_hold_bars: int | None = None,
) -> list[TradeResult]:
    trades: list[TradeResult] = []
    i = 0
    n = len(df)
    # default max hold: enough to span ~3 months window sanity
    if max_hold_bars is None:
        max_hold_bars = {"5m": 288 * 3, "15m": 96 * 3, "1h": 24 * 7, "4h": 6 * 14}.get(tf, 500)

    while i < n:
        s = int(signals.iloc[i])
        if s == 0:
            i += 1
            continue
        # Enter at close of signal bar (or next open — use close for consistency with Cardwell close[1] style)
        entry = float(df["Close"].iloc[i])
        direction = s
        sl, tp = sl_tp_levels(symbol, entry, direction)
        entry_time = str(df.index[i])
        exit_idx = None
        outcome = "timeout"
        exit_price = float(df["Close"].iloc[min(i + max_hold_bars, n - 1)])

        for j in range(i + 1, min(i + max_hold_bars + 1, n)):
            hi = float(df["High"].iloc[j])
            lo = float(df["Low"].iloc[j])
            if direction == 1:
                hit_sl = lo <= sl
                hit_tp = hi >= tp
            else:
                hit_sl = hi >= sl
                hit_tp = lo <= tp
            if hit_sl and hit_tp:
                # conservative: SL first on same bar
                outcome = "loss"
                exit_price = sl
                exit_idx = j
                break
            if hit_sl:
                outcome = "loss"
                exit_price = sl
                exit_idx = j
                break
            if hit_tp:
                outcome = "win"
                exit_price = tp
                exit_idx = j
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
        # After SL/TP: continue searching from bar AFTER exit (user requirement)
        i = exit_idx + 1

    return trades


def summarize(trades: list[TradeResult]) -> dict:
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "win_rate": None,
            "win_rate_resolved": None,
            "avg_bars": None,
            "flip_proxy": None,
        }
    wins = sum(1 for t in trades if t.outcome == "win")
    losses = sum(1 for t in trades if t.outcome == "loss")
    timeouts = sum(1 for t in trades if t.outcome == "timeout")
    resolved = wins + losses
    # flip proxy: opposite consecutive signals within short hold (from original signal stream measured separately)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "win_rate": round(100 * wins / len(trades), 2) if trades else None,
        "win_rate_resolved": round(100 * wins / resolved, 2) if resolved else None,
        "avg_bars": round(sum(t.bars_held for t in trades) / len(trades), 2),
    }


def flip_rate(signals: pd.Series, window: int = 5) -> float | None:
    """% of signals that reverse within `window` bars (Cardwell weakness metric)."""
    idxs = np.where(signals.values != 0)[0]
    if len(idxs) < 2:
        return None
    flips = 0
    for k, i in enumerate(idxs[:-1]):
        nxt = idxs[k + 1]
        if nxt - i <= window and signals.iloc[nxt] == -signals.iloc[i]:
            flips += 1
    return round(100 * flips / max(len(idxs) - 1, 1), 2)


def load_df(symbol: str, tf: str) -> pd.DataFrame:
    path = DATA / f"{symbol}_{tf}.csv"
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.title() for c in df.columns]
    # last ~90 days if available
    cutoff = df.index.max() - pd.Timedelta(days=90)
    df = df[df.index >= cutoff]
    return df


def run_all() -> None:
    symbols = ["BTC", "XAU", "EURUSD"]
    tfs = ["5m", "15m", "1h", "4h"]
    summary_rows = []
    all_trades = []

    for symbol in symbols:
        for tf in tfs:
            path = DATA / f"{symbol}_{tf}.csv"
            if not path.exists():
                print(f"Missing {path}")
                continue
            df = load_df(symbol, tf)
            if len(df) < 100:
                print(f"Too few bars {symbol} {tf}: {len(df)}")
                continue
            print(f"\n=== {symbol} {tf} bars={len(df)} {df.index.min()} -> {df.index.max()} ===")
            for name, fn in SIGNAL_FNS.items():
                try:
                    sig = fn(df)
                except Exception as e:
                    print(f"  {name} failed: {e}")
                    continue
                trades = backtest(df, sig, symbol, tf, name)
                stats = summarize(trades)
                fr = flip_rate(sig, window={"5m": 6, "15m": 4, "1h": 3, "4h": 2}[tf])
                stats["flip_within_N"] = fr
                stats["symbol"] = symbol
                stats["tf"] = tf
                stats["indicator"] = name
                stats["bars"] = len(df)
                summary_rows.append(stats)
                all_trades.extend([asdict(t) for t in trades])
                wr = stats["win_rate"]
                wrr = stats["win_rate_resolved"]
                print(
                    f"  {name:12s} trades={stats['trades']:4d}  "
                    f"WR={wr}%  WRres={wrr}%  "
                    f"W/L/T={stats['wins']}/{stats['losses']}/{stats['timeouts']}  "
                    f"flip%={fr}  avgBars={stats['avg_bars']}"
                )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(all_trades).to_csv(OUT / "trades.csv", index=False)

    # Pivot tables
    if not summary_df.empty:
        pivot_wr = summary_df.pivot_table(
            index=["indicator", "symbol"], columns="tf", values="win_rate", aggfunc="first"
        )
        pivot_n = summary_df.pivot_table(
            index=["indicator", "symbol"], columns="tf", values="trades", aggfunc="first"
        )
        pivot_wr.to_csv(OUT / "pivot_winrate.csv")
        pivot_n.to_csv(OUT / "pivot_trades.csv")
        (OUT / "summary.json").write_text(summary_df.to_json(orient="records", indent=2))
        print("\nWin-rate pivot:")
        print(pivot_wr.to_string())
        print("\nTrade-count pivot:")
        print(pivot_n.to_string())


if __name__ == "__main__":
    # silence pandas FutureWarning for fillna method
    pd.set_option("future.no_silent_downcasting", True)
    run_all()
