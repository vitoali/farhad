"""Backtest code 004 (FORGE) over the last month.

Modes:
- native:      honest entry (next open after detection), pattern SL (25% of
               target distance, recomputed from honest entry) and measured-move TP.
- std models:  honest entry with the project risk models.

Outputs appended to results/ledger.csv (code_id=004) and per-trade logs in
results/trades/004_*.csv.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

import engine
from data import SYMBOLS, TF_SECONDS
from forge import ForgeEngine, SL_PCT_TGT
from run import CRYPTO_MODELS, FX_MODELS, load, _row

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
TRADES_DIR = RESULTS / "trades"
WINDOW_DAYS = 30


def simulate(df: pd.DataFrame, sigs: pd.DataFrame, market: str, symbol: str,
             mode: str, sl_spec=None, tp_spec=None, window_start: int = 0) -> list:
    o = df["open"].to_numpy(); h = df["high"].to_numpy(); l = df["low"].to_numpy()
    n = len(df)
    trades = []
    busy_until = -1
    for _, s in sigs.iterrows():
        i = int(s.sig_idx)
        if s.time < window_start or i + 1 >= n or i + 1 <= busy_until:
            continue
        entry = o[i + 1]
        direction = s.direction
        sign = 1 if direction == "long" else -1
        if mode == "native":
            tp = s.target
            if sign * (tp - entry) <= 0:   # target already passed at honest entry
                continue
            sl = entry - sign * abs(tp - entry) * SL_PCT_TGT
        else:
            sl_d = engine._dist(sl_spec, entry, symbol, None)
            tp_d = engine._dist(tp_spec, entry, symbol, sl_d)
            sl = entry - sign * sl_d
            tp = entry + sign * tp_d
        tr = engine.Trade(i + 1, int(s.time), direction, entry, sl, tp)
        tr.features = s.to_dict()
        for j in range(i + 1, n):
            hit_sl = l[j] <= sl if direction == "long" else h[j] >= sl
            hit_tp = h[j] >= tp if direction == "long" else l[j] <= tp
            if hit_sl:
                tr.outcome = "sl"; tr.exit_price = sl; tr.exit_idx = j
                break
            if hit_tp:
                tr.outcome = "tp"; tr.exit_price = tp; tr.exit_idx = j
                break
        if tr.outcome == "open":
            tr.exit_price = df["close"].iloc[-1]; tr.exit_idx = n - 1
        engine._finalize(tr, market, symbol)
        trades.append(tr)
        busy_until = tr.exit_idx
    return trades


def main() -> None:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    end = int(time.time())
    window_start = end - WINDOW_DAYS * 86400
    ledger = pd.read_csv(RESULTS / "ledger.csv")
    ledger = ledger[ledger.code_id != 4]  # idempotent re-run
    new_rows = []
    for symbol, (_, _, market) in SYMBOLS.items():
        is_crypto = market == "crypto"
        eng_market = "crypto" if is_crypto else market
        models = CRYPTO_MODELS if is_crypto else FX_MODELS
        htf = load(symbol, "1h")
        for tf in TF_SECONDS:
            df = load(symbol, tf)
            if df is None:
                continue
            sigs = ForgeEngine(df, htf).scan()
            n_sig = len(sigs[sigs.time >= window_start]) if len(sigs) else 0
            period_start = max(int(df["time"].iloc[0]), window_start)
            configs = [("forge_native", None, None)] + \
                      [(name, sl, tp) for name, sl, tp in models]
            for model_name, sl_spec, tp_spec in configs:
                mode = "native" if model_name == "forge_native" else "std"
                trades = simulate(df, sigs, eng_market, symbol, mode, sl_spec, tp_spec, window_start) if n_sig else []
                m = engine.metrics(trades)
                r = _row(f"004_forge", symbol, tf, model_name, period_start, end, m)
                r["notes"] = f"honest entry; {n_sig} raw signals"
                new_rows.append(r)
                if m.get("trades", 0) > 0:
                    rows = []
                    for tr in trades:
                        d = dict(tr.features)
                        d.update({"outcome": tr.outcome, "pl_pct": round(tr.pl_pct, 4),
                                  "r": round(tr.r, 3) if not np.isnan(tr.r) else "",
                                  "bars_held": tr.exit_idx - tr.idx})
                        rows.append(d)
                    pd.DataFrame(rows).to_csv(TRADES_DIR / f"004_forge_{symbol}_{tf}_{model_name}.csv", index=False)
            print(f"done {symbol} {tf}: {n_sig} signals in window")
    out = pd.concat([ledger, pd.DataFrame(new_rows)], ignore_index=True)
    out.to_csv(RESULTS / "ledger.csv", index=False)
    print(f"ledger now {len(out)} rows")


if __name__ == "__main__":
    main()
