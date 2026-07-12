#!/usr/bin/env python3
"""Backtest Cardwell Range Analyze logic on crypto pairs."""

import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

# ── Cardwell defaults (from indicator) ──────────────────────────
RSI_LEN = 14
TREND_LEN = 50
BULL_LO, BULL_HI = 40, 80
BEAR_LO, BEAR_HI = 20, 60
CONFIRM_BARS = 2
ATR_LEN = 14
SL_MULT = 1.5
TP1_MULT, TP2_MULT, TP3_MULT = 1.0, 2.0, 3.0
USE_HTF = False
USE_ADX = False
ADX_MIN = 20


SYMBOL_MAP = {"BTCUSDT": "BTC-USDT", "SOLUSDT": "SOL-USDT"}
BAR_MAP = {"15m": "15m", "1h": "1H"}


def fetch_klines(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    """Fetch OHLCV from OKX public API (~1 month)."""
    inst_id = SYMBOL_MAP.get(symbol, symbol.replace("USDT", "-USDT"))
    bar = BAR_MAP.get(interval, interval)
    limit = 300
    start_ms = int((datetime.now(timezone.utc).timestamp() - days * 86400) * 1000)
    all_rows = []
    after = None
    max_pages = 30

    for _ in range(max_pages):
        url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={limit}"
        if after:
            url += f"&after={after}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
        data = payload.get("data", [])
        if not data:
            break
        all_rows.extend(data)
        oldest = int(data[-1][0])
        if oldest <= start_ms:
            break
        if len(data) < limit:
            break
        after = oldest

    df = pd.DataFrame(all_rows, columns=["open_time", "open", "high", "low", "close", "volume", "volccy", "volquote", "confirm"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df["open_time"] = df["open_time"].astype(int)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df[df["open_time"] >= start_ms].drop_duplicates("open_time")
    return df.sort_values("open_time").reset_index(drop=True)


def rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, length: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def adx(df: pd.DataFrame, length: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    down = -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_v = tr.ewm(alpha=1 / length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_v
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / length, adjust=False).mean() / atr_v
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / length, adjust=False).mean()


def cardwell_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["rsi"] = rsi(out["close"], RSI_LEN)
    out["trend_ma"] = out["close"].rolling(TREND_LEN).mean()
    out["is_up"] = out["close"] > out["trend_ma"]
    out["is_down"] = out["close"] < out["trend_ma"]
    out["in_bull_range"] = (out["rsi"] >= BULL_LO) & (out["rsi"] <= BULL_HI)
    out["in_bear_range"] = (out["rsi"] >= BEAR_LO) & (out["rsi"] <= BEAR_HI)
    out["bull_raw"] = out["is_up"] & out["in_bull_range"]
    out["bear_raw"] = out["is_down"] & out["in_bear_range"]

    bull_cnt, bear_cnt = [], []
    bc = be = 0
    for br, bar in zip(out["bull_raw"], out["bear_raw"]):
        bc = bc + 1 if br else 0
        be = be + 1 if bar else 0
        bull_cnt.append(bc)
        bear_cnt.append(be)
    out["bull_cnt"] = bull_cnt
    out["bear_cnt"] = bear_cnt
    out["bull_regime"] = out["bull_raw"] & (out["bull_cnt"] >= CONFIRM_BARS)
    out["bear_regime"] = out["bear_raw"] & (out["bear_cnt"] >= CONFIRM_BARS)
    out["regime"] = np.where(out["bull_regime"], 1, np.where(out["bear_regime"], -1, 0))
    out["prev_regime"] = out["regime"].shift(1).fillna(0).astype(int)

    if USE_ADX:
        out["adx"] = adx(out, ATR_LEN)
        out["chop_ok"] = out["adx"] >= ADX_MIN
    else:
        out["chop_ok"] = True

    out["long_signal"] = (out["regime"] == 1) & (out["prev_regime"] != 1) & out["chop_ok"]
    out["short_signal"] = (out["regime"] == -1) & (out["prev_regime"] != -1) & out["chop_ok"]
    out["atr"] = atr(out, ATR_LEN)
    return out


@dataclass
class Trade:
    side: str
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl_pct: float = 0.0


def backtest(df: pd.DataFrame, fee_pct: float = 0.04) -> dict:
    """Simulate: enter on signal close, exit on SL, opposite signal, or TP3."""
    trades: list[Trade] = []
    position: Optional[Trade] = None

    for i in range(TREND_LEN + CONFIRM_BARS, len(df)):
        row = df.iloc[i]
        price = row["close"]
        hi, lo = row["high"], row["low"]

        if position:
            t = position
            hit_sl = (t.side == "long" and lo <= t.sl) or (t.side == "short" and hi >= t.sl)
            hit_tp3 = (t.side == "long" and hi >= t.tp3) or (t.side == "short" and lo <= t.tp3)
            flip = (t.side == "long" and row["short_signal"]) or (t.side == "short" and row["long_signal"])

            if hit_sl:
                t.exit_time = row["time"]
                t.exit_price = t.sl
                t.exit_reason = "SL"
            elif hit_tp3:
                t.exit_time = row["time"]
                t.exit_price = t.tp3
                t.exit_reason = "TP3"
            elif flip:
                t.exit_time = row["time"]
                t.exit_price = price
                t.exit_reason = "Flip"
            else:
                continue

            if t.side == "long":
                t.pnl_pct = (t.exit_price / t.entry - 1) * 100 - fee_pct * 2
            else:
                t.pnl_pct = (t.entry / t.exit_price - 1) * 100 - fee_pct * 2
            trades.append(t)
            position = None

        if position is None:
            a = row["atr"]
            if row["long_signal"] and not np.isnan(a):
                entry = price
                position = Trade(
                    "long", row["time"], entry,
                    entry - a * SL_MULT, entry + a * TP1_MULT,
                    entry + a * TP2_MULT, entry + a * TP3_MULT,
                )
            elif row["short_signal"] and not np.isnan(a):
                entry = price
                position = Trade(
                    "short", row["time"], entry,
                    entry + a * SL_MULT, entry - a * TP1_MULT,
                    entry - a * TP2_MULT, entry - a * TP3_MULT,
                )

    if position:
        last = df.iloc[-1]
        position.exit_time = last["time"]
        position.exit_price = last["close"]
        position.exit_reason = "EOD"
        if position.side == "long":
            position.pnl_pct = (position.exit_price / position.entry - 1) * 100 - fee_pct * 2
        else:
            position.pnl_pct = (position.entry / position.exit_price - 1) * 100 - fee_pct * 2
        trades.append(position)

    if not trades:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "total_pnl_pct": 0.0, "avg_pnl_pct": 0.0, "max_dd_pct": 0.0,
            "longs": 0, "shorts": 0, "signals_long": int(df["long_signal"].sum()),
            "signals_short": int(df["short_signal"].sum()),
        }

    pnls = [t.pnl_pct for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    equity = 100.0
    peak = 100.0
    max_dd = 0.0
    for p in pnls:
        equity *= 1 + p / 100
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak * 100)

    return {
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate": round(wins / len(trades) * 100, 1),
        "total_pnl_pct": round(sum(pnls), 2),
        "avg_pnl_pct": round(np.mean(pnls), 2),
        "max_dd_pct": round(max_dd, 2),
        "longs": sum(1 for t in trades if t.side == "long"),
        "shorts": sum(1 for t in trades if t.side == "short"),
        "signals_long": int(df["long_signal"].sum()),
        "signals_short": int(df["short_signal"].sum()),
        "exit_sl": sum(1 for t in trades if t.exit_reason == "SL"),
        "exit_tp3": sum(1 for t in trades if t.exit_reason == "TP3"),
        "exit_flip": sum(1 for t in trades if t.exit_reason == "Flip"),
    }


def run_all():
    pairs = [("BTCUSDT", "15m"), ("BTCUSDT", "1h"), ("SOLUSDT", "15m"), ("SOLUSDT", "1h")]
    interval_map = {"15m": "15m", "1h": "1h"}
    results = []

    print("=" * 70)
    print("Cardwell Range Analyze — Backtest (~31 days, OKX data)")
    print("Settings: RSI14, SMA50, Bull RSI 40-80, Bear RSI 20-60, Confirm=2")
    print("Exit: SL 1.5ATR | TP3 3ATR | Flip on opposite signal | Fee 0.04%/side")
    print("=" * 70)

    for symbol, tf in pairs:
        print(f"\nFetching {symbol} {tf}...")
        try:
            raw = fetch_klines(symbol, interval_map[tf], days=31)
            df = cardwell_signals(raw)
            stats = backtest(df)
            period = f"{raw['time'].iloc[0].date()} → {raw['time'].iloc[-1].date()}"
            stats.update({"symbol": symbol, "timeframe": tf, "bars": len(raw), "period": period})
            results.append(stats)
            print(
                f"  {symbol} {tf} | bars={stats['bars']} | {period}\n"
                f"  Signals: {stats['signals_long']} LONG / {stats['signals_short']} SHORT\n"
                f"  Trades: {stats['trades']} (L{stats['longs']}/S{stats['shorts']}) | "
                f"Win: {stats['win_rate']}% | PnL: {stats['total_pnl_pct']:+.2f}% | "
                f"Avg: {stats['avg_pnl_pct']:+.2f}% | MaxDD: {stats['max_dd_pct']:.2f}%\n"
                f"  Exits: SL={stats.get('exit_sl',0)} TP3={stats.get('exit_tp3',0)} Flip={stats.get('exit_flip',0)}"
            )
        except Exception as e:
            print(f"  ERROR {symbol} {tf}: {e}")
            results.append({"symbol": symbol, "timeframe": tf, "error": str(e)})

    return results


if __name__ == "__main__":
    run_all()
