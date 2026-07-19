"""Build 4H BTC data: fetch 420 days of 1H from Coinbase, resample to 4H."""
import pandas as pd
from fetch_data import save_csv, fetch_coinbase, OUT_DIR

if __name__ == "__main__":
    rows = fetch_coinbase(420, 3600)
    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close"])
    df["time"] = pd.to_datetime(df["time"])
    r = df.resample("4h", on="time").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last")).dropna().reset_index()
    r["time"] = r["time"].dt.strftime("%Y-%m-%d %H:%M")
    save_csv(f"{OUT_DIR}/btc_4h.csv", r.values.tolist())
