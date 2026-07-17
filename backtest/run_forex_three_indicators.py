#!/usr/bin/env python3
"""Backtest Elliott Wave, CM MACD MTF, EWO/RSI on EURUSD / XAUUSD / USDJPY."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import FOREX_SL_PIPS, FOREX_TP_RR
from engine import aggregate, simulate_fixed_sl_tp
from extra_indicators import elliott_wave_lux_signals, macd_mtf_signals
from fetch_data import fetch_all
from run_backtest import result_to_dict
from zone_indicators import rsi_advanced_signals

RESULTS = Path(__file__).parent / "results"
SYMBOLS = ["EURUSD", "XAUUSD", "USDJPY"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]
MARKET = "forex"

INDICATORS = {
    "elliott_wave": ("Elliott Wave [LuxAlgo]", lambda df: elliott_wave_lux_signals(df)),
    "cm_macd_mtf": ("CM_MacD_Ult_MTF", lambda df: macd_mtf_signals(df)),
    "ewo_rsi": ("EWO/RSI Advanced [Pridarasx]", lambda df: rsi_advanced_signals(df)),
}


def pip_size(symbol: str, price: float) -> float:
    if "JPY" in symbol:
        return 0.01
    if price < 50:
        return 0.0001
    return 1.0


def simulate_forex(df: pd.DataFrame, buy: pd.Series, sell: pd.Series, symbol: str) -> list:
    """Forex sim with correct pip size for JPY pairs."""
    trades = []
    position = 0
    entry_price = entry_bar = 0.0
    sl_price = tp_price = 0.0
    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    buy_v = buy.fillna(False).values
    sell_v = sell.fillna(False).values
    n = len(df)

    def close_trade(bar: int, price: float, reason: str):
        nonlocal position, entry_price, entry_bar
        if position == 0:
            return
        direction = "long" if position == 1 else "short"
        pip = pip_size(symbol, entry_price)
        cost = pip * 2
        pnl = (price - entry_price) * position - cost
        r_mult = pnl / (FOREX_SL_PIPS * pip) if FOREX_SL_PIPS > 0 else 0
        from engine import Trade

        trades.append(
            Trade(
                direction=direction,
                entry_bar=entry_bar,
                entry_price=entry_price,
                exit_bar=bar,
                exit_price=price,
                outcome="win" if pnl > 0 else "loss",
                bars_held=bar - entry_bar,
                r_multiple=r_mult,
                exit_reason=reason,
            )
        )
        position = 0

    def open_trade(bar: int, direction: int, price: float):
        nonlocal position, entry_price, entry_bar, sl_price, tp_price
        position = direction
        entry_price = price
        entry_bar = bar
        pip = pip_size(symbol, price)
        risk = FOREX_SL_PIPS * pip
        sl_price = price - risk if direction == 1 else price + risk
        tp_dist = risk * FOREX_TP_RR
        tp_price = price + tp_dist if direction == 1 else price - tp_dist

    for i in range(n):
        if i > 0 and buy_v[i - 1]:
            if position == -1:
                close_trade(i, closes[i], "flip")
            if position == 0:
                open_trade(i, 1, closes[i])
        elif i > 0 and sell_v[i - 1]:
            if position == 1:
                close_trade(i, closes[i], "flip")
            if position == 0:
                open_trade(i, -1, closes[i])

        if position != 0 and i > entry_bar:
            if position == 1:
                if lows[i] <= sl_price:
                    close_trade(i, sl_price, "sl")
                elif highs[i] >= tp_price:
                    close_trade(i, tp_price, "tp")
            else:
                if highs[i] >= sl_price:
                    close_trade(i, sl_price, "sl")
                elif lows[i] <= tp_price:
                    close_trade(i, tp_price, "tp")

    if position != 0:
        close_trade(n - 1, closes[-1], "eod")
    return trades


def run_all(data: dict) -> list[dict]:
    rows: list[dict] = []
    for ind_key, (ind_label, fn) in INDICATORS.items():
        for sym in SYMBOLS:
            for tf in TIMEFRAMES:
                df = data.get(sym, {}).get(tf)
                if df is None or len(df) < 80:
                    continue
                try:
                    sig = fn(df)
                    trades = simulate_forex(df, sig["buy"], sig["sell"], sym)
                    r = aggregate(trades, ind_key, sym, tf, MARKET)
                    r.notes.append(f"label={ind_label} signals={int(sig['buy'].sum())+int(sig['sell'].sum())}")
                    rows.append(result_to_dict(r))
                except Exception as e:
                    rows.append({
                        "indicator": ind_key,
                        "symbol": sym,
                        "timeframe": tf,
                        "market": MARKET,
                        "total_trades": 0,
                        "win_rate": 0,
                        "profit_factor": 0,
                        "notes": [str(e)],
                    })
    return rows


def rank_indicator(rows: list[dict], ind_key: str) -> dict:
    subset = [r for r in rows if r["indicator"] == ind_key and r["total_trades"] >= 1]
    if not subset:
        return {"indicator": ind_key, "status": "no_trades"}
    ranked = sorted(
        subset,
        key=lambda x: (x["profit_factor"] if x["profit_factor"] < 900 else 0, x["win_rate"]),
        reverse=True,
    )
    best = ranked[0]
    by_sym: dict[str, dict] = {}
    for sym in SYMBOLS:
        sym_rows = [r for r in subset if r["symbol"] == sym and r["total_trades"] >= 1]
        if sym_rows:
            b = max(sym_rows, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
            by_sym[sym] = {
                "best_tf": b["timeframe"],
                "pf": b["profit_factor"],
                "wr": b["win_rate"],
                "trades": b["total_trades"],
            }
    by_tf: dict[str, dict] = {}
    for tf in TIMEFRAMES:
        tf_rows = [r for r in subset if r["timeframe"] == tf and r["total_trades"] >= 1]
        if tf_rows:
            avg_pf = sum(r["profit_factor"] for r in tf_rows if r["profit_factor"] < 900) / len(tf_rows)
            by_tf[tf] = {"avg_pf": round(avg_pf, 3), "runs": len(tf_rows)}
    return {
        "indicator": ind_key,
        "best_overall": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}% ({best['total_trades']} trades)",
        "by_symbol": by_sym,
        "by_timeframe": by_tf,
        "top5": [
            f"{r['symbol']} {r['timeframe']} PF={r['profit_factor']} WR={r['win_rate']}% trades={r['total_trades']}"
            for r in ranked[:5]
        ],
    }


def main():
    print("Fetching EURUSD / XAUUSD / USDJPY — 5m 15m 1h 4h (~31 days)...")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=False)
    rows = run_all(data)
    summaries = {k: rank_indicator(rows, k) for k in INDICATORS}

    out = {"period_days": 31, "symbols": SYMBOLS, "timeframes": TIMEFRAMES, "summaries": summaries, "results": rows}
    path = RESULTS / "backtest_forex_three_indicators.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {path}\n")

    labels = {k: v[0] for k, v in INDICATORS.items()}
    for k, s in summaries.items():
        print(f"=== {labels[k]} ===")
        if s.get("status"):
            print(f"  {s['status']}")
            continue
        print(f"  بهترین کلی: {s['best_overall']}")
        print("  بهترین per symbol:")
        for sym, info in s.get("by_symbol", {}).items():
            print(f"    {sym}: {info['best_tf']} PF={info['pf']} WR={info['wr']}% ({info['trades']} trades)")
        print("  میانگین PF per TF:")
        for tf, info in s.get("by_timeframe", {}).items():
            print(f"    {tf}: avg_PF={info['avg_pf']} ({info['runs']} runs)")


if __name__ == "__main__":
    main()
