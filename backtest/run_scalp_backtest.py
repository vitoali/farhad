#!/usr/bin/env python3
"""Backtest all indicators + Farhad strategies on 5m and 15m only."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from fetch_data import fetch_all
from run_backtest import SYMBOL_MARKET, result_to_dict, run_indicator
from run_combo_backtest import MODES, run_mode

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
SCALP_TFS = ["5m", "15m"]

INDICATORS = [
    "ut_bot", "alpha_trend", "bj_bot", "forge", "fib_fib", "quadapt",
    "supertrend", "chandelier_exit", "lorentzian",
    "ifvg", "breaker_blocks", "smc_pro", "zero_lag", "trendline_breakout", "rsi_advanced", "ml_rsi",
    "supply_demand", "strong_pullback",
    "cardwell_rsi", "fvg_retest", "stop_hunt", "smart_money_structure",
    "smc_pro_alt", "matrix_fvg", "put_call_vp", "ranked_ob", "qqe", "macd_mtf", "power_ob",
    "sr_breaks", "liquidity_pool", "slingshot", "ichimoku_ml", "liquidity_shift", "cm_ma_mtf",
    "fxpip_scob", "buyside_liquidity", "sr_signals_mtf", "divergence", "orderflow_print",
    "fair_value_gap", "fib_ote",
    "mirage_lsp", "trendmaster", "pmax", "volume_ob_retest", "dynamic_trend",
    "quantum_imbalance", "multi_div", "knn_pivot", "hv_pivot_sr",
]


def market_of(symbol: str) -> str:
    return SYMBOL_MARKET.get(symbol, "crypto")


def run_all_indicators(data: dict) -> list[dict]:
    rows: list[dict] = []
    for sym, tfs in data.items():
        market = market_of(sym)
        for tf in SCALP_TFS:
            df = tfs.get(tf)
            if df is None or len(df) < 50:
                continue
            for ind in INDICATORS:
                try:
                    r = run_indicator(ind, df, sym, tf, market)
                    rows.append(result_to_dict(r))
                except Exception as e:
                    rows.append({
                        "indicator": ind, "symbol": sym, "timeframe": tf,
                        "market": market, "total_trades": 0, "win_rate": 0,
                        "profit_factor": 0, "notes": [str(e)],
                    })
    return rows


def run_strategies(data: dict) -> list[dict]:
    scalp_data = {
        sym: {tf: df for tf, df in tfs.items() if tf in SCALP_TFS}
        for sym, tfs in data.items()
    }
    rows: list[dict] = []
    for mode in MODES:
        for r in run_mode(mode, scalp_data):
            if r["timeframe"] in SCALP_TFS:
                rows.append(r)
    return rows


def summarize_by_market(rows: list[dict], market: str, min_trades: int = 3) -> list[dict]:
  """Per-indicator avg PF/WR on 5m+15m for one market."""
  by_ind: dict[str, list[dict]] = defaultdict(list)
  for r in rows:
    if r.get("market") != market or r.get("timeframe") not in SCALP_TFS:
      continue
    by_ind[r["indicator"]].append(r)

  out = []
  for ind, items in by_ind.items():
    valid = [x for x in items if x.get("total_trades", 0) >= min_trades and x.get("profit_factor", 0) < 900]
    if not valid:
      continue
    pfs = [x["profit_factor"] for x in valid]
    wrs = [x["win_rate"] for x in valid]
    trades = sum(x["total_trades"] for x in valid)
    best = max(valid, key=lambda x: x["profit_factor"])
    out.append({
      "indicator": ind,
      "runs": len(valid),
      "total_trades": trades,
      "avg_pf": round(sum(pfs) / len(pfs), 3),
      "avg_wr": round(sum(wrs) / len(wrs), 1),
      "best_combo": f"{best['symbol']} {best['timeframe']} PF={best['profit_factor']} WR={best['win_rate']}%",
      "best_pf": best["profit_factor"],
    })
  out.sort(key=lambda x: (-x["avg_pf"], -x["avg_wr"]))
  return out


def top_per_symbol_tf(rows: list[dict], market: str, top_n: int = 5) -> dict:
  """Best indicator per symbol×TF for a market."""
  buckets: dict[str, list[dict]] = defaultdict(list)
  for r in rows:
    if r.get("market") != market or r.get("timeframe") not in SCALP_TFS:
      continue
    if r.get("total_trades", 0) < 3 or r.get("profit_factor", 0) >= 900:
      continue
    key = f"{r['symbol']}_{r['timeframe']}"
    buckets[key].append(r)

  result = {}
  for key, items in sorted(buckets.items()):
    items.sort(key=lambda x: -x["profit_factor"])
    result[key] = items[:top_n]
  return result


def main():
  print("=== Fetch 5m + 15m (~31 days) ===")
  data = fetch_all(days=31, timeframes=SCALP_TFS, force=False)

  print("\n=== Indicators ===")
  ind_rows = run_all_indicators(data)
  print(f"  {len(ind_rows)} runs")

  print("\n=== Strategies (Farhad) ===")
  strat_rows = run_strategies(data)
  for r in strat_rows:
    r["indicator"] = r.get("indicator", "farhad")
  # run_mode already sets indicator in aggregate
  all_rows = ind_rows + strat_rows
  print(f"  {len(strat_rows)} strategy runs")

  crypto_rank = summarize_by_market(all_rows, "crypto")
  forex_rank = summarize_by_market(all_rows, "forex")
  crypto_detail = top_per_symbol_tf(all_rows, "crypto")
  forex_detail = top_per_symbol_tf(all_rows, "forex")

  out = {
    "period_days": 31,
    "timeframes": SCALP_TFS,
    "symbols": list(SYMBOL_MARKET.keys()),
    "crypto_top": crypto_rank[:25],
    "forex_top": forex_rank[:25],
    "crypto_by_symbol_tf": crypto_detail,
    "forex_by_symbol_tf": forex_detail,
    "results": all_rows,
  }
  path = RESULTS / "backtest_scalp_5m_15m.json"
  path.write_text(json.dumps(out, indent=2), encoding="utf-8")
  print(f"\nSaved {path}")

  print("\n=== CRYPTO TOP 15 (5m+15m avg) ===")
  for i, x in enumerate(crypto_rank[:15], 1):
    print(f"  {i:2}. {x['indicator']:<22} PF={x['avg_pf']:.3f} WR={x['avg_wr']:.1f}% trades={x['total_trades']} | {x['best_combo']}")

  print("\n=== FOREX TOP 15 (5m+15m avg) ===")
  for i, x in enumerate(forex_rank[:15], 1):
    print(f"  {i:2}. {x['indicator']:<22} PF={x['avg_pf']:.3f} WR={x['avg_wr']:.1f}% trades={x['total_trades']} | {x['best_combo']}")


if __name__ == "__main__":
  main()
