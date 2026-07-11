"""Backtest engine.

Rules (per docs/methodology.md):
- Signal confirmed at close of bar i, filled at open of bar i+1.
- Fixed SL/TP risk models; intrabar order: if both SL and TP are inside the same
  bar's range, SL is assumed to fill first (conservative, no tick data).
- Native mode: exit at the fill of the opposite signal (flip).
- Costs are applied to every round trip and expressed in price %.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# round-trip costs in % of price (fees + spread + slippage), per methodology
COSTS_PCT = {
    "crypto": 0.20,          # 2x0.05% taker + 2x0.05% slippage
    "fx": None,              # handled in pips
    "gold": None,
}
FX_PIP = {"EURUSD": 0.0001, "XAUUSD": 0.1}
FX_COST_PIPS = {"EURUSD": 1.1, "XAUUSD": 4.5}  # spread + 2x slippage; XAU in 0.1-pt pips


@dataclass
class Trade:
    idx: int                 # entry bar index
    time: int
    direction: str           # long/short
    entry: float
    sl: float
    tp: float | None
    outcome: str = "open"    # tp / sl / flip / open
    exit_price: float = np.nan
    exit_idx: int = -1
    pl_pct: float = np.nan   # after costs
    r: float = np.nan        # after costs, vs initial risk
    features: dict = field(default_factory=dict)


def _cost_pct(market: str, symbol: str, entry: float) -> float:
    if market == "crypto":
        return COSTS_PCT["crypto"]
    pip = FX_PIP[symbol]
    return FX_COST_PIPS[symbol] * pip / entry * 100


def run_fixed(df: pd.DataFrame, signals: pd.DataFrame, market: str, symbol: str,
              sl_spec: tuple, tp_spec: tuple, window_start: int) -> list[Trade]:
    """sl_spec/tp_spec: ("pct", x) or ("pips", x) or ("rr", mult)."""
    o = df["open"].to_numpy(); h = df["high"].to_numpy(); l = df["low"].to_numpy()
    t = df["time"].to_numpy()
    longs = signals["long"].to_numpy(); shorts = signals["short"].to_numpy()
    n = len(df)
    trades: list[Trade] = []
    open_tr: Trade | None = None
    for i in range(n - 1):
        # manage open trade on bar i+1 range
        if open_tr is not None:
            j = i + 1
            if open_tr.direction == "long":
                hit_sl = l[j] <= open_tr.sl
                hit_tp = h[j] >= open_tr.tp
            else:
                hit_sl = h[j] >= open_tr.sl
                hit_tp = l[j] <= open_tr.tp
            if hit_sl:  # conservative: SL first when both hit
                open_tr.outcome = "sl"; open_tr.exit_price = open_tr.sl; open_tr.exit_idx = j
            elif hit_tp:
                open_tr.outcome = "tp"; open_tr.exit_price = open_tr.tp; open_tr.exit_idx = j
            if open_tr.outcome != "open":
                _finalize(open_tr, market, symbol)
                trades.append(open_tr)
                open_tr = None
        # new entry from signal on bar i (fill at open[i+1]) only inside test window
        if open_tr is None and t[i] >= window_start and (longs[i] or shorts[i]):
            direction = "long" if longs[i] else "short"
            entry = o[i + 1]
            sl_d = _dist(sl_spec, entry, symbol, None)
            tp_d = _dist(tp_spec, entry, symbol, sl_d)
            sl = entry - sl_d if direction == "long" else entry + sl_d
            tp = entry + tp_d if direction == "long" else entry - tp_d
            open_tr = Trade(i + 1, int(t[i + 1]), direction, entry, sl, tp)
    if open_tr is not None:
        open_tr.outcome = "open"; open_tr.exit_price = df["close"].iloc[-1]; open_tr.exit_idx = n - 1
        _finalize(open_tr, market, symbol)
        trades.append(open_tr)
    return trades


def run_native(df: pd.DataFrame, signals: pd.DataFrame, market: str, symbol: str,
               window_start: int) -> list[Trade]:
    o = df["open"].to_numpy(); t = df["time"].to_numpy()
    longs = signals["long"].to_numpy(); shorts = signals["short"].to_numpy()
    n = len(df)
    trades: list[Trade] = []
    open_tr: Trade | None = None
    for i in range(n - 1):
        if not (longs[i] or shorts[i]):
            continue
        direction = "long" if longs[i] else "short"
        fill = o[i + 1]
        if open_tr is not None and open_tr.direction != direction:
            open_tr.outcome = "flip"; open_tr.exit_price = fill; open_tr.exit_idx = i + 1
            # risk proxy for R: 1% of entry (crypto) / cost-adjusted pl only
            _finalize(open_tr, market, symbol)
            trades.append(open_tr)
            open_tr = None
        if open_tr is None and t[i] >= window_start:
            open_tr = Trade(i + 1, int(t[i + 1]), direction, fill, np.nan, None)
    if open_tr is not None:
        open_tr.outcome = "open"; open_tr.exit_price = df["close"].iloc[-1]; open_tr.exit_idx = n - 1
        _finalize(open_tr, market, symbol)
        trades.append(open_tr)
    return trades


def _dist(spec: tuple, entry: float, symbol: str, sl_dist: float | None) -> float:
    kind, val = spec
    if kind == "pct":
        return entry * val / 100
    if kind == "pips":
        return val * FX_PIP[symbol]
    if kind == "rr":
        return val * sl_dist
    raise ValueError(kind)


def _finalize(tr: Trade, market: str, symbol: str) -> None:
    sign = 1 if tr.direction == "long" else -1
    gross = sign * (tr.exit_price - tr.entry) / tr.entry * 100
    cost = _cost_pct(market, symbol, tr.entry)
    tr.pl_pct = gross - cost
    if not np.isnan(tr.sl):
        risk_pct = abs(tr.entry - tr.sl) / tr.entry * 100
        tr.r = tr.pl_pct / risk_pct if risk_pct > 0 else np.nan


def metrics(trades: list[Trade]) -> dict:
    closed = [tr for tr in trades if tr.outcome != "open"]
    if not closed:
        return {"trades": 0}
    pl = np.array([tr.pl_pct for tr in closed])
    wins = pl[pl > 0]; losses = pl[pl <= 0]
    equity = np.cumprod(1 + pl / 100)
    peak = np.maximum.accumulate(equity)
    dd = (equity / peak - 1).min() * 100
    rs = np.array([tr.r for tr in closed if not np.isnan(tr.r)])
    return {
        "trades": len(closed),
        "win_rate": round(len(wins) / len(closed) * 100, 1),
        "profit_factor": round(wins.sum() / -losses.sum(), 2) if losses.sum() < 0 else float("inf"),
        "net_profit_pct": round((equity[-1] - 1) * 100, 2),
        "max_dd_pct": round(dd, 2),
        "avg_r": round(rs.mean(), 3) if len(rs) else None,
        "avg_pl_pct": round(pl.mean(), 3),
    }
