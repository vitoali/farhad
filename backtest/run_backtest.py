#!/usr/bin/env python3
"""Run 1-month offline backtests for indicators #1-#3."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import CRYPTO_SL_PCT, CRYPTO_TP_PCT, FOREX_SL_PIPS, FOREX_TP_RR
from engine import BacktestResult, Trade, aggregate, simulate_bj_native, simulate_fixed_sl_tp
from fetch_data import fetch_all
from forge_patterns import detect_double_patterns, simulate_forge_signals
from indicators import alpha_trend_signals, bj_bot_signals, fib_fib_signals, ut_bot_signals

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SYMBOL_MARKET = {
    "BTCUSDT": "crypto",
    "HYPEUSDT": "crypto",
    "BEATUSDT": "crypto",
    "EURUSD": "forex",
    "XAUUSD": "forex",
}
TIMEFRAMES = ["15m", "1h", "4h", "1d"]


def run_indicator(name: str, df: pd.DataFrame, symbol: str, tf: str, market: str) -> BacktestResult:
    if len(df) < 50:
        return BacktestResult(name, symbol, tf, market, notes=["insufficient data"])

    if name == "ut_bot":
        sig = ut_bot_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name == "alpha_trend":
        novol = market == "forex" or symbol == "BEATUSDT"
        sig = alpha_trend_signals(df, novolumedata=novol)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name == "bj_bot":
        sig = bj_bot_signals(df)
        if market == "crypto":
            # crypto: fixed SL 5% per user (signals from Bj, exit with unified risk model)
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_bj_native(sig)
        return aggregate(trades, name, symbol, tf, market)

    if name == "forge":
        if len(df) < 650:
            return BacktestResult(name, symbol, tf, market, notes=["need 600+ bars for pivot gate"])
        raw = detect_double_patterns(df)
        # cooldown 5 bars between signals
        filtered = []
        last = -99
        for s in raw:
            if s.bar - last >= 5:
                filtered.append(s)
                last = s.bar
        outcomes = simulate_forge_signals(df, filtered, use_fixed_sl_pct=CRYPTO_SL_PCT if market == "crypto" else None,
                                          use_fixed_tp_pct=CRYPTO_TP_PCT if market == "crypto" else None)
        trades = [
            Trade(
                direction="long" if o["bullish"] else "short",
                entry_bar=o["entry_bar"],
                entry_price=0,
                exit_bar=o["entry_bar"] + o["bars_to_outcome"],
                exit_price=0,
                outcome="win" if o["outcome"] == "win" else "loss",
                bars_held=o["bars_to_outcome"],
                r_multiple=o["r_multiple"],
                exit_reason=o["outcome"],
            )
            for o in outcomes
            if o["outcome"] in ("win", "loss")
        ]
        res = aggregate(trades, name, symbol, tf, market)
        res.notes.append(f"patterns={len(filtered)} grades={[o['grade'] for o in outcomes[:5]]}")
        return res

    if name == "fib_fib":
        min_bars = 265
        if len(df) < min_bars + 10:
            return BacktestResult(name, symbol, tf, market, notes=[f"need {min_bars}+ bars"])
        sig = fib_fib_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        res = aggregate(trades, name, symbol, tf, market)
        touches = sig[sig["buy"] | sig["sell"]]["touch_level"].value_counts().to_dict()
        res.notes.append(f"levels={touches}")
        return res

    raise ValueError(name)


def result_to_dict(r: BacktestResult) -> dict:
    return {
        "indicator": r.indicator,
        "symbol": r.symbol,
        "timeframe": r.timeframe,
        "market": r.market,
        "total_trades": r.total_trades,
        "win_rate": round(r.win_rate, 2),
        "profit_factor": round(r.profit_factor, 3) if r.profit_factor != float("inf") else 999,
        "avg_r": round(r.avg_r, 3),
        "max_drawdown_r": round(r.max_drawdown_pct, 3),
        "notes": r.notes,
    }


def summarize_learning(results: list[dict]) -> dict:
    """Extract cross-cutting strengths/weaknesses per indicator."""
    by_ind: dict[str, list[dict]] = {}
    for r in results:
        by_ind.setdefault(r["indicator"], []).append(r)

    learning = {}
    for ind, rows in by_ind.items():
        valid = [x for x in rows if x["total_trades"] >= 3]
        if not valid:
            learning[ind] = {"status": "insufficient_trades", "rows": len(rows)}
            continue
        avg_wr = sum(x["win_rate"] for x in valid) / len(valid)
        avg_pf = sum(x["profit_factor"] for x in valid if x["profit_factor"] < 900) / max(1, len([x for x in valid if x["profit_factor"] < 900]))
        avg_trades = sum(x["total_trades"] for x in valid) / len(valid)
        best = max(valid, key=lambda x: x["profit_factor"] if x["profit_factor"] < 900 else 0)
        worst = min(valid, key=lambda x: x["profit_factor"])

        learning[ind] = {
            "avg_win_rate": round(avg_wr, 2),
            "avg_profit_factor": round(avg_pf, 3),
            "avg_trades_per_run": round(avg_trades, 1),
            "best": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']}",
            "worst": f"{worst['symbol']} {worst['timeframe']} PF={worst['profit_factor']}",
            "samples": len(valid),
        }
    return learning


def main():
    print("=== Fetching data (~31 days) ===")
    data = fetch_all(days=31, timeframes=TIMEFRAMES, force=True)

    indicators = ["ut_bot", "alpha_trend", "bj_bot", "forge", "fib_fib"]
    all_results: list[dict] = []

    print("\n=== Running backtests ===")
    for sym, tfs in data.items():
        market = SYMBOL_MARKET.get(sym, "crypto")
        for tf, df in tfs.items():
            if df is None or len(df) < 50:
                print(f"SKIP {sym} {tf}: no data")
                continue
            for ind in indicators:
                try:
                    r = run_indicator(ind, df, sym, tf, market)
                    d = result_to_dict(r)
                    all_results.append(d)
                    print(f"  {ind:12} {sym:8} {tf:4} trades={d['total_trades']:3} WR={d['win_rate']:5.1f}% PF={d['profit_factor']}")
                except Exception as e:
                    print(f"  {ind:12} {sym:8} {tf:4} ERROR: {e}")

    learning = summarize_learning(all_results)

    out = {"period_days": 31, "results": all_results, "learning": learning}
    out_path = RESULTS_DIR / "backtest_1m_summary.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")
    print("\n=== Learning summary ===")
    print(json.dumps(learning, indent=2))


if __name__ == "__main__":
    main()
