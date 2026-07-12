#!/usr/bin/env python3
"""Run 1-month offline backtests for indicators #1-#3."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import CRYPTO_SL_PCT, CRYPTO_TP_PCT, FOREX_SL_PIPS, FOREX_TP_RR
from engine import BacktestResult, Trade, aggregate, simulate_bj_native, simulate_fixed_sl_tp
from farhad_strategy import farhad_combo_signals
from farhad_master_strategy import farhad_master_signals
from fetch_data import fetch_all
from forge_patterns import detect_double_patterns, simulate_forge_signals
from ml_indicators import ml_rsi_signals
from extra_indicators import (
    cardwell_rsi_signals,
    fvg_retest_signals,
    macd_mtf_signals,
    matrix_fvg_signals,
    power_ob_signals,
    put_call_vp_signals,
    qqe_signals,
    ranked_ob_signals,
    smart_money_structure_signals,
    smc_pro_alt_signals,
    stop_hunt_signals,
    sr_breaks_signals,
    liquidity_pool_signals,
    slingshot_signals,
    ichimoku_ml_signals,
    liquidity_shift_signals,
    cm_ma_mtf_signals,
    fxpip_scob_signals,
    buyside_liquidity_signals,
    sr_signals_mtf_signals,
    divergence_signals,
    orderflow_print_signals,
    fair_value_gap_signals,
    fib_ote_signals,
    mirage_lsp_signals,
    trendmaster_signals,
    pmax_signals,
    volume_ob_retest_signals,
    dynamic_trend_signals,
    quantum_imbalance_signals,
    multi_div_signals,
    knn_pivot_signals,
    hv_pivot_sr_signals,
)
from zone_engine import extract_zone_signals_from_df, simulate_zone_native
from zone_indicators import (
    breaker_blocks_signals,
    ifvg_signals,
    rsi_advanced_signals,
    smc_pro_signals,
    strong_pullback_signals,
    supply_demand_signals,
    trendline_breakout_signals,
    zero_lag_signals,
)
from indicators import (
    alpha_trend_signals,
    bj_bot_signals,
    chandelier_exit_signals,
    fib_fib_signals,
    lorentzian_signals,
    quadapt_signals,
    supertrend_signals,
    ut_bot_signals,
)

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

ZONE_NATIVE = {
    "ifvg", "breaker_blocks", "smc_pro", "trendline_breakout",
    "supply_demand", "strong_pullback", "fvg_retest", "stop_hunt",
    "smart_money_structure", "smc_pro_alt", "matrix_fvg", "ranked_ob", "power_ob",
    "cardwell_rsi",
    "liquidity_pool",
    "liquidity_shift",
    "buyside_liquidity", "sr_signals_mtf", "fair_value_gap", "fib_ote",
    "mirage_lsp", "volume_ob_retest", "quantum_imbalance", "multi_div", "hv_pivot_sr",
}


def _run_zone(name: str, df: pd.DataFrame, symbol: str, tf: str, market: str) -> BacktestResult:
    if name == "ifvg":
        sig = ifvg_signals(df)
    elif name == "breaker_blocks":
        sig = breaker_blocks_signals(df)
    elif name == "smc_pro":
        sig = smc_pro_signals(df)
    elif name == "trendline_breakout":
        sig = trendline_breakout_signals(df)
    elif name == "supply_demand":
        sig = supply_demand_signals(df)
    elif name == "strong_pullback":
        sig = strong_pullback_signals(df)
    elif name == "fvg_retest":
        sig = fvg_retest_signals(df)
    elif name == "stop_hunt":
        sig = stop_hunt_signals(df)
    elif name == "smart_money_structure":
        sig = smart_money_structure_signals(df)
    elif name == "smc_pro_alt":
        sig = smc_pro_alt_signals(df)
    elif name == "matrix_fvg":
        sig = matrix_fvg_signals(df)
    elif name == "ranked_ob":
        sig = ranked_ob_signals(df)
    elif name == "power_ob":
        sig = power_ob_signals(df)
    elif name == "cardwell_rsi":
        sig = cardwell_rsi_signals(df)
    elif name == "liquidity_pool":
        sig = liquidity_pool_signals(df)
    elif name == "liquidity_shift":
        sig = liquidity_shift_signals(df)
    elif name == "buyside_liquidity":
        sig = buyside_liquidity_signals(df)
    elif name == "sr_signals_mtf":
        sig = sr_signals_mtf_signals(df)
    elif name == "fair_value_gap":
        sig = fair_value_gap_signals(df)
    elif name == "fib_ote":
        sig = fib_ote_signals(df)
    elif name == "mirage_lsp":
        sig = mirage_lsp_signals(df)
    elif name == "volume_ob_retest":
        sig = volume_ob_retest_signals(df)
    elif name == "quantum_imbalance":
        sig = quantum_imbalance_signals(df)
    elif name == "multi_div":
        sig = multi_div_signals(df)
    elif name == "hv_pivot_sr":
        sig = hv_pivot_sr_signals(df)
    else:
        raise ValueError(name)
    zlist = extract_zone_signals_from_df(sig)
    trades = simulate_zone_native(df, zlist, market)
    res = aggregate(trades, name, symbol, tf, market)
    res.notes.append(f"signals={len(zlist)}")
    return res


def _run_fixed(name: str, df: pd.DataFrame, symbol: str, tf: str, market: str, sig: pd.DataFrame) -> BacktestResult:
    if market == "crypto":
        trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
    else:
        trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
    return aggregate(trades, name, symbol, tf, market)


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

    if name.startswith("farhad_"):
        mode = name.replace("farhad_", "")
        novol = market == "forex" or symbol == "BEATUSDT"
        if mode.startswith("master"):
            sig = farhad_master_signals(df, mode=mode, novolumedata=novol)
            zlist = extract_zone_signals_from_df(sig)
            trades = simulate_zone_native(df, zlist, market)
            res = aggregate(trades, name, symbol, tf, market)
            res.notes.append(f"signals={len(zlist)} avg_score={sig['score_long'].max():.1f}")
            return res
        sig = farhad_combo_signals(df, mode=mode, novolumedata=novol)
        trades = simulate_bj_native(sig)
        res = aggregate(trades, name, symbol, tf, market)
        res.notes.append(f"zone_avg={sig['zone_score'].mean():.2f}")
        return res

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

    if name == "quadapt":
        if len(df) < 150:
            return BacktestResult(name, symbol, tf, market, notes=["need 150+ bars"])
        sig = quadapt_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name == "supertrend":
        sig = supertrend_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name == "chandelier_exit":
        sig = chandelier_exit_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name == "lorentzian":
        if len(df) < 200:
            return BacktestResult(name, symbol, tf, market, notes=["need 200+ bars"])
        sig = lorentzian_signals(df)
        if market == "crypto":
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pct=CRYPTO_SL_PCT, tp_pct=CRYPTO_TP_PCT)
        else:
            trades = simulate_fixed_sl_tp(sig, sig["buy"], sig["sell"], market, sl_pips=FOREX_SL_PIPS, tp_rr=FOREX_TP_RR)
        return aggregate(trades, name, symbol, tf, market)

    if name in ZONE_NATIVE:
        return _run_zone(name, df, symbol, tf, market)

    if name == "zero_lag":
        sig = zero_lag_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "rsi_advanced":
        sig = rsi_advanced_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "ml_rsi":
        if len(df) < 200:
            return BacktestResult(name, symbol, tf, market, notes=["need 200+ bars"])
        sig = ml_rsi_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "put_call_vp":
        sig = put_call_vp_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "sr_breaks":
        sig = sr_breaks_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "slingshot":
        sig = slingshot_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "ichimoku_ml":
        sig = ichimoku_ml_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "cm_ma_mtf":
        sig = cm_ma_mtf_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "fxpip_scob":
        sig = fxpip_scob_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "divergence":
        sig = divergence_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "orderflow_print":
        sig = orderflow_print_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "qqe":
        sig = qqe_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "macd_mtf":
        sig = macd_mtf_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "trendmaster":
        sig = trendmaster_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "pmax":
        sig = pmax_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "dynamic_trend":
        sig = dynamic_trend_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "knn_pivot":
        sig = knn_pivot_signals(df)
        return _run_fixed(name, df, symbol, tf, market, sig)

    if name == "monster":
        return BacktestResult(name, symbol, tf, market, notes=["blocked: external pine libraries — use monster_trex"])

    if name == "monster_trex":
        from monster_trex_strategy import monster_trex_signals
        pair = "H1_M5" if tf == "5m" else "H4_M15" if tf == "15m" else "H1_M5"
        sig = monster_trex_signals(df, chart_tf=tf, market=market, pair_mode=pair, use_trend_filter=True)
        zlist = extract_zone_signals_from_df(sig)
        trades = simulate_zone_native(df, zlist, market)
        return aggregate(trades, name, symbol, tf, market)

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

    indicators = [
        "ut_bot", "alpha_trend", "bj_bot", "forge", "fib_fib", "quadapt",
        "supertrend", "chandelier_exit", "lorentzian",
        "ifvg", "breaker_blocks", "smc_pro", "zero_lag", "trendline_breakout", "rsi_advanced", "ml_rsi",
        "supply_demand", "strong_pullback",
        "cardwell_rsi", "fvg_retest", "stop_hunt", "smart_money_structure",
        "smc_pro_alt", "matrix_fvg", "put_call_vp", "ranked_ob", "qqe", "macd_mtf", "power_ob",
        "sr_breaks", "liquidity_pool",         "slingshot", "ichimoku_ml", "liquidity_shift", "cm_ma_mtf",
        "fxpip_scob", "buyside_liquidity", "sr_signals_mtf", "divergence", "orderflow_print",
        "fair_value_gap", "fib_ote",
        "mirage_lsp", "trendmaster", "pmax", "volume_ob_retest", "dynamic_trend",
        "quantum_imbalance", "multi_div", "knn_pivot", "hv_pivot_sr",
    ]
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
