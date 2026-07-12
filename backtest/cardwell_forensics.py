#!/usr/bin/env python3
"""Cardwell backtest + loss forensics + improved filters."""

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

SYMBOL_MAP = {"BTCUSDT": "BTC-USDT", "SOLUSDT": "SOL-USDT"}
BAR_MAP = {"15m": "15m", "1h": "1H"}

RSI_LEN = 14
TREND_LEN = 50
BULL_LO, BULL_HI = 40, 80
BEAR_LO, BEAR_HI = 20, 60
CONFIRM_BARS = 2
ATR_LEN = 14
SL_MULT = 1.5
TP3_MULT = 3.0
FEE = 0.04


def fetch_klines(symbol: str, interval: str, days: int = 31) -> pd.DataFrame:
    inst_id = SYMBOL_MAP.get(symbol, symbol.replace("USDT", "-USDT"))
    bar = BAR_MAP.get(interval, interval)
    start_ms = int((datetime.now(timezone.utc).timestamp() - days * 86400) * 1000)
    all_rows, after, limit = [], None, 300
    for _ in range(30):
        url = f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar}&limit={limit}"
        if after:
            url += f"&after={after}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode()).get("data", [])
        if not data:
            break
        all_rows.extend(data)
        oldest = int(data[-1][0])
        if oldest <= start_ms or len(data) < limit:
            break
        after = oldest
    df = pd.DataFrame(all_rows, columns=["open_time", "open", "high", "low", "close", "volume", "a", "b", "c"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df["open_time"] = df["open_time"].astype(int)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    return df[df["open_time"] >= start_ms].drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)


def rsi(s: pd.Series, n: int) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df: pd.DataFrame, n: int) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    up, down = h.diff(), -l.diff()
    pdm = np.where((up > down) & (up > 0), up, 0.0)
    mdm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    a = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * pd.Series(mdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def build_signals(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    o = df.copy()
    o["rsi"] = rsi(o["close"], cfg.get("rsi_len", RSI_LEN))
    o["rsi_prev"] = o["rsi"].shift(1)
    o["trend_ma"] = o["close"].rolling(cfg.get("trend_len", TREND_LEN)).mean()
    o["atr"] = atr(o, ATR_LEN)
    o["adx"] = adx(o, ATR_LEN)
    o["ma_dist_pct"] = (o["close"] - o["trend_ma"]) / o["trend_ma"] * 100

    bull_lo, bull_hi = cfg.get("bull_range", (BULL_LO, BULL_HI))
    bear_lo, bear_hi = cfg.get("bear_range", (BEAR_LO, BEAR_HI))
    confirm = cfg.get("confirm_bars", CONFIRM_BARS)

    o["is_up"] = o["close"] > o["trend_ma"]
    o["is_down"] = o["close"] < o["trend_ma"]
    o["in_bull_range"] = (o["rsi"] >= bull_lo) & (o["rsi"] <= bull_hi)
    o["in_bear_range"] = (o["rsi"] >= bear_lo) & (o["rsi"] <= bear_hi)
    o["bull_raw"] = o["is_up"] & o["in_bull_range"]
    o["bear_raw"] = o["is_down"] & o["in_bear_range"]

    bc = be = 0
    bull_cnt, bear_cnt = [], []
    for br, bar in zip(o["bull_raw"], o["bear_raw"]):
        bc = bc + 1 if br else 0
        be = be + 1 if bar else 0
        bull_cnt.append(bc)
        bear_cnt.append(be)
    o["bull_cnt"] = bull_cnt
    o["bear_cnt"] = bear_cnt
    o["bull_regime"] = o["bull_raw"] & (o["bull_cnt"] >= confirm)
    o["bear_regime"] = o["bear_raw"] & (o["bear_cnt"] >= confirm)
    o["regime"] = np.where(o["bull_regime"], 1, np.where(o["bear_regime"], -1, 0))
    o["prev_regime"] = o["regime"].shift(1).fillna(0).astype(int)

    # ── فیلترهای قابل تنظیم ──
    adx_ok = (~cfg.get("use_adx", False)) | (o["adx"] >= cfg.get("adx_min", 20))
    ma_dist_ok_long = o["ma_dist_pct"].abs() >= cfg.get("min_ma_dist_pct", 0) if cfg.get("min_ma_dist_pct", 0) > 0 else True
    ma_dist_ok_short = ma_dist_ok_long
    rsi_mom_long = (~cfg.get("rsi_momentum", False)) | (o["rsi"] > o["rsi_prev"])
    rsi_mom_short = (~cfg.get("rsi_momentum", False)) | (o["rsi"] < o["rsi_prev"])
    not_late_long = (~cfg.get("avoid_late_rsi", False)) | (o["rsi"] <= cfg.get("max_long_rsi", 70))
    not_late_short = (~cfg.get("avoid_late_rsi", False)) | (o["rsi"] >= cfg.get("min_short_rsi", 30))

    o["long_signal"] = (
        (o["regime"] == 1) & (o["prev_regime"] != 1) & adx_ok
        & ma_dist_ok_long & rsi_mom_long & not_late_long
    )
    o["short_signal"] = (
        (o["regime"] == -1) & (o["prev_regime"] != -1) & adx_ok
        & ma_dist_ok_short & rsi_mom_short & not_late_short
    )
    return o


@dataclass
class Trade:
    side: str
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp3: float
    rsi: float
    adx: float
    ma_dist: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""
    pnl_pct: float = 0.0
    meta: dict = field(default_factory=dict)


def backtest(df: pd.DataFrame, cooldown: int = 0) -> tuple[list[Trade], pd.DataFrame]:
    trades: list[Trade] = []
    pos: Optional[Trade] = None
    last_sig_i = -9999

    for i in range(TREND_LEN + CONFIRM_BARS + 5, len(df)):
        row = df.iloc[i]
        price, hi, lo = row["close"], row["high"], row["low"]

        if pos:
            t = pos
            if (t.side == "long" and lo <= t.sl) or (t.side == "short" and hi >= t.sl):
                t.exit_time, t.exit_price, t.exit_reason = row["time"], t.sl, "SL"
            elif (t.side == "long" and hi >= t.tp3) or (t.side == "short" and lo <= t.tp3):
                t.exit_time, t.exit_price, t.exit_reason = row["time"], t.tp3, "TP3"
            elif (t.side == "long" and row["short_signal"]) or (t.side == "short" and row["long_signal"]):
                t.exit_time, t.exit_price, t.exit_reason = row["time"], price, "Flip"
            else:
                continue
            t.pnl_pct = ((t.exit_price / t.entry - 1) if t.side == "long" else (t.entry / t.exit_price - 1)) * 100 - FEE * 2
            trades.append(t)
            pos = None

        if pos is None and i - last_sig_i >= cooldown:
            a = row["atr"]
            if row["long_signal"] and not np.isnan(a):
                pos = Trade("long", row["time"], price, price - a * SL_MULT, price + a * TP3_MULT,
                            row["rsi"], row["adx"], row["ma_dist_pct"])
                last_sig_i = i
            elif row["short_signal"] and not np.isnan(a):
                pos = Trade("short", row["time"], price, price + a * SL_MULT, price - a * TP3_MULT,
                            row["rsi"], row["adx"], row["ma_dist_pct"])
                last_sig_i = i

    if pos:
        last = df.iloc[-1]
        pos.exit_time, pos.exit_price, pos.exit_reason = last["time"], last["close"], "EOD"
        pos.pnl_pct = ((pos.exit_price / pos.entry - 1) if pos.side == "long" else (pos.entry / pos.exit_price - 1)) * 100 - FEE * 2
        trades.append(pos)
    return trades, df


def analyze_losses(trades: list[Trade]) -> dict:
    losers = [t for t in trades if t.pnl_pct <= 0]
    winners = [t for t in trades if t.pnl_pct > 0]
    if not losers:
        return {"losers": 0}

    def bucket(vals, edges, labels):
        counts = {lb: 0 for lb in labels}
        for v in vals:
            for e, lb in zip(edges, labels):
                if v < e:
                    counts[lb] += 1
                    break
            else:
                counts[labels[-1]] += 1
        return counts

    loss_reasons = {}
    for t in losers:
        loss_reasons[t.exit_reason] = loss_reasons.get(t.exit_reason, 0) + 1

    return {
        "total": len(trades),
        "losers": len(losers),
        "winners": len(winners),
        "loss_rate": round(len(losers) / len(trades) * 100, 1),
        "exit_reasons": loss_reasons,
        "avg_loser_rsi": round(np.mean([t.rsi for t in losers]), 1),
        "avg_winner_rsi": round(np.mean([t.rsi for t in winners]), 1) if winners else 0,
        "avg_loser_adx": round(np.mean([t.adx for t in losers]), 1),
        "avg_winner_adx": round(np.mean([t.adx for t in winners]), 1) if winners else 0,
        "avg_loser_ma_dist": round(np.mean([abs(t.ma_dist) for t in losers]), 3),
        "avg_winner_ma_dist": round(np.mean([abs(t.ma_dist) for t in winners]), 3) if winners else 0,
        "low_adx_losses": sum(1 for t in losers if t.adx < 20),
        "whipsaw_flip_losses": sum(1 for t in losers if t.exit_reason == "Flip"),
        "short_losses_bull_rsi": sum(1 for t in losers if t.side == "short" and t.rsi < 50),
        "long_losses_bear_rsi": sum(1 for t in losers if t.side == "long" and t.rsi > 55),
        "rsi_buckets_losers": bucket([t.rsi for t in losers], [45, 55, 65], ["<45", "45-55", "55-65", ">65"]),
    }


def stats(trades: list[Trade]) -> dict:
    if not trades:
        return {"trades": 0, "win_rate": 0, "pnl": 0, "max_dd": 0}
    pnls = [t.pnl_pct for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    eq, peak, dd = 100.0, 100.0, 0.0
    for p in pnls:
        eq *= 1 + p / 100
        peak = max(peak, eq)
        dd = max(dd, (peak - eq) / peak * 100)
    return {
        "trades": len(trades),
        "win_rate": round(wins / len(trades) * 100, 1),
        "pnl": round(sum(pnls), 2),
        "max_dd": round(dd, 2),
    }


# ── نسخه اصلی vs اصلاح‌شده (بر اساس تحلیل ضعف 1H) ──
ORIGINAL = {"confirm_bars": 2}
FIXED = {
    "confirm_bars": 3,
    "use_adx": True,
    "adx_min": 22,
    "min_ma_dist_pct": 0.15,
    "rsi_momentum": True,
    "avoid_late_rsi": True,
    "max_long_rsi": 68,
    "min_short_rsi": 32,
}


def main():
    targets = [("SOLUSDT", "1h"), ("BTCUSDT", "1h"), ("SOLUSDT", "15m"), ("BTCUSDT", "15m")]
    print("=" * 72)
    print("CARDWELL — تحلیل ضعف سیگنال‌های اشتباه + نسخه اصلاح‌شده")
    print("=" * 72)

    for sym, tf in targets:
        raw = fetch_klines(sym, tf, 31)
        df0 = build_signals(raw, ORIGINAL)
        t0, _ = backtest(df0)
        loss = analyze_losses(t0)

        df1 = build_signals(raw, FIXED)
        t1, _ = backtest(df1, cooldown=4 if tf == "1h" else 2)
        s0, s1 = stats(t0), stats(t1)

        print(f"\n{'─'*72}")
        print(f"  {sym} | {tf} | bars={len(raw)} | {raw['time'].iloc[0].date()} → {raw['time'].iloc[-1].date()}")
        print(f"  ── نسخه اصلی (Cardwell) ──")
        print(f"  Trades={s0['trades']} Win={s0['win_rate']}% PnL={s0['pnl']:+.2f}% DD={s0['max_dd']}%")
        if loss.get("losers"):
            print(f"  ضعف‌های شناسایی‌شده در بازنده‌ها:")
            print(f"    • SL={loss['exit_reasons'].get('SL',0)} | Flip={loss['exit_reasons'].get('Flip',0)} (whipsaw)")
            print(f"    • ADX پایین (<20): {loss['low_adx_losses']}/{loss['losers']} بازنده")
            print(f"    • RSI نامناسب: Short با RSI<50 → {loss['short_losses_bull_rsi']} | Long با RSI>55 → {loss['long_losses_bear_rsi']}")
            print(f"    • میانگین ADX بازنده={loss['avg_loser_adx']} برنده={loss['avg_winner_adx']}")
            print(f"    • میانگین فاصله از MA: بازنده={loss['avg_loser_ma_dist']}% برنده={loss['avg_winner_ma_dist']}%")
        print(f"  ── نسخه اصلاح‌شده ──")
        print(f"  فیلترها: ADX≥22 | Confirm=3 | MA dist≥0.15% | RSI momentum | Late RSI cut | Cooldown")
        print(f"  Trades={s1['trades']} Win={s1['win_rate']}% PnL={s1['pnl']:+.2f}% DD={s1['max_dd']}%")
        delta = s1["pnl"] - s0["pnl"]
        print(f"  بهبود PnL: {delta:+.2f}%")

    print(f"\n{'='*72}")
    print("روش کلی: 1) جدا کردن بازنده‌ها 2) مقایسه RSI/ADX/MA 3) فیلتر روی الگوی تکراری 4) re-test")


if __name__ == "__main__":
    main()
