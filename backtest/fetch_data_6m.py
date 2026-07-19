"""Fetch ~7 months of data for the 6-month validation backtest.

Note: Yahoo only serves 15m candles for the last 60 days, so the 6-month
gold test runs on 1H only. Bitcoin (Coinbase) has no such limit.
"""
from fetch_data import save_csv, fetch_yahoo, fetch_coinbase, OUT_DIR

if __name__ == "__main__":
    save_csv(f"{OUT_DIR}/gold_1h_6m.csv", fetch_yahoo("GC=F", "1h", "1y"))
    save_csv(f"{OUT_DIR}/btc_1h_6m.csv", fetch_coinbase(215, 3600))
    save_csv(f"{OUT_DIR}/btc_15m_6m.csv", fetch_coinbase(190, 900))
