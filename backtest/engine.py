"""Backtest engine with fixed SL/TP and native exit modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

MarketType = Literal["crypto", "forex"]


@dataclass
class Trade:
    direction: str
    entry_bar: int
    entry_price: float
    exit_bar: int = -1
    exit_price: float = 0.0
    outcome: str = ""
    bars_held: int = 0
    r_multiple: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    indicator: str
    symbol: str
    timeframe: str
    market: MarketType
    trades: list[Trade] = field(default_factory=list)
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_r: float = 0.0
    total_trades: int = 0
    notes: list[str] = field(default_factory=list)


def _crypto_cost_pct(slippage_pct: float = 0.05, fee_pct: float = 0.05) -> float:
    return (slippage_pct + fee_pct) / 100.0


def _forex_cost_price(price: float, pips: float = 1.0) -> float:
    pip = 0.0001 if price < 50 else 1.0
    return pips * pip


def simulate_fixed_sl_tp(
    df: pd.DataFrame,
    buy: pd.Series,
    sell: pd.Series,
    market: MarketType,
    sl_pct: float = 0.01,
    tp_pct: float = 0.02,
    sl_pips: float = 3.0,
    tp_rr: float = 1.0,
    max_bars: int = 200,
) -> list[Trade]:
    """Long on buy, short on sell; flip on opposite signal."""
    trades: list[Trade] = []
    position = 0  # 1 long, -1 short, 0 flat
    entry_price = 0.0
    entry_bar = 0
    sl_price = 0.0
    tp_price = 0.0
    risk = 0.0

    closes = df["close"].values
    highs = df["high"].values
    lows = df["low"].values
    buy_v = buy.fillna(False).values
    sell_v = sell.fillna(False).values
    n = len(df)

    def close_trade(bar: int, price: float, reason: str):
        nonlocal position, entry_price, entry_bar, sl_price, tp_price, risk
        if position == 0:
            return
        direction = "long" if position == 1 else "short"
        if market == "crypto":
            cost = entry_price * _crypto_cost_pct() * 2
            pnl = (price - entry_price) * position - cost
            r_mult = pnl / (entry_price * sl_pct) if sl_pct > 0 else 0
        else:
            cost = _forex_cost_price(entry_price, 1.0) * 2
            pnl = (price - entry_price) * position - cost
            pip = 0.0001 if entry_price < 50 else 1.0
            r_mult = pnl / (sl_pips * pip) if sl_pips > 0 else 0
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
        nonlocal position, entry_price, entry_bar, sl_price, tp_price, risk
        position = direction
        entry_price = price
        entry_bar = bar
        if market == "crypto":
            risk = price * sl_pct
            sl_price = price - risk if direction == 1 else price + risk
            tp_price = price + price * tp_pct if direction == 1 else price - price * tp_pct
        else:
            # EURUSD ~1.1 → pip 0.0001; XAUUSD ~2300 → $1 = 1 'pip' unit
            pip = 0.0001 if price < 50 else 1.0
            risk = sl_pips * pip
            sl_price = price - risk if direction == 1 else price + risk
            tp_dist = risk * tp_rr
            tp_price = price + tp_dist if direction == 1 else price - tp_dist

    for i in range(n):
        # enter on next bar after signal (realistic fill)
        if buy_v[i - 1] if i > 0 else False:
            if position == -1:
                close_trade(i, closes[i], "flip")
            if position == 0:
                open_trade(i, 1, closes[i])
        elif sell_v[i - 1] if i > 0 else False:
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
                elif i - entry_bar >= max_bars:
                    close_trade(i, closes[i], "timeout")
            else:
                if highs[i] >= sl_price:
                    close_trade(i, sl_price, "sl")
                elif lows[i] <= tp_price:
                    close_trade(i, tp_price, "tp")
                elif i - entry_bar >= max_bars:
                    close_trade(i, closes[i], "timeout")

    if position != 0:
        close_trade(n - 1, closes[-1], "eod")

    return trades


def simulate_bj_native(df: pd.DataFrame, fee_pct: float = 0.05) -> list[Trade]:
    """Use swing+ATR stop and R:R target from bj_bot_signals columns."""
    buy = df["buy"]
    sell = df["sell"]
    trades: list[Trade] = []
    position = 0
    entry_price = entry_bar = 0
    sl_price = tp_price = 0.0
    risk = 0.0

    for i in range(len(df)):
        row = df.iloc[i]
        c, h, l = row["close"], row["high"], row["low"]

        if position == 1 and i > entry_bar:
            if l <= sl_price:
                pnl = sl_price - entry_price
                trades.append(Trade("long", entry_bar, entry_price, i, sl_price, "loss" if pnl < 0 else "win", i - entry_bar, pnl / risk if risk else 0, "sl"))
                position = 0
            elif h >= tp_price:
                pnl = tp_price - entry_price
                trades.append(Trade("long", entry_bar, entry_price, i, tp_price, "win", i - entry_bar, pnl / risk if risk else 0, "tp"))
                position = 0
        elif position == -1 and i > entry_bar:
            if h >= sl_price:
                pnl = entry_price - sl_price
                trades.append(Trade("short", entry_bar, entry_price, i, sl_price, "loss" if pnl < 0 else "win", i - entry_bar, pnl / risk if risk else 0, "sl"))
                position = 0
            elif l <= tp_price:
                pnl = entry_price - tp_price
                trades.append(Trade("short", entry_bar, entry_price, i, tp_price, "win", i - entry_bar, pnl / risk if risk else 0, "tp"))
                position = 0

        if i > 0 and buy.iloc[i - 1] and position == 0 and df.iloc[i - 1]["long_risk"] > 0:
            prev = df.iloc[i - 1]
            position = 1
            entry_price, entry_bar = c, i
            sl_price = prev["long_stop"]
            tp_price = prev["long_target"]
            risk = prev["long_risk"]
        elif i > 0 and sell.iloc[i - 1] and position == 0 and df.iloc[i - 1]["short_risk"] > 0:
            prev = df.iloc[i - 1]
            position = -1
            entry_price, entry_bar = c, i
            sl_price = prev["short_stop"]
            tp_price = prev["short_target"]
            risk = prev["short_risk"]

    return trades


def aggregate(trades: list[Trade], indicator: str, symbol: str, tf: str, market: MarketType) -> BacktestResult:
    res = BacktestResult(indicator, symbol, tf, market, trades=list(trades))
    if not trades:
        return res

    wins = [t for t in trades if t.outcome == "win"]
    losses = [t for t in trades if t.outcome == "loss"]
    res.total_trades = len(trades)
    res.win_rate = len(wins) / len(trades) * 100

    gross_win = sum(t.r_multiple for t in wins)
    gross_loss = abs(sum(t.r_multiple for t in losses))
    res.profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win > 0 else 0
    res.avg_r = float(np.mean([t.r_multiple for t in trades]))
    res.net_return_pct = sum(t.r_multiple for t in trades) * (1 if market == "forex" else 1)

    equity = np.cumsum([t.r_multiple for t in trades])
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    res.max_drawdown_pct = float(dd.max()) if len(dd) else 0
    return res
