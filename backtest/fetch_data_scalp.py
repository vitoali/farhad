"""Fetch 5m/15m (max ~60d from Yahoo) for gold & EURUSD and build 4H files
from the existing 1-year 1H CSVs."""
import pandas as pd
from fetch_data import save_csv, fetch_yahoo, OUT_DIR


def resample_4h(src, dst):
    df = pd.read_csv(src)
    df["time"] = pd.to_datetime(df["time"])
    r = df.resample("4h", on="time").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last")).dropna().reset_index()
    r["time"] = r["time"].dt.strftime("%Y-%m-%d %H:%M")
    save_csv(dst, r.values.tolist())


if __name__ == "__main__":
    save_csv(f"{OUT_DIR}/gold_5m.csv", fetch_yahoo("GC=F", "5m", "60d"))
    save_csv(f"{OUT_DIR}/eurusd_5m.csv", fetch_yahoo("EURUSD=X", "5m", "60d"))
    save_csv(f"{OUT_DIR}/gold_15m_60d.csv", fetch_yahoo("GC=F", "15m", "60d"))
    save_csv(f"{OUT_DIR}/eurusd_15m_60d.csv", fetch_yahoo("EURUSD=X", "15m", "60d"))
    resample_4h(f"{OUT_DIR}/gold_1h_6m.csv", f"{OUT_DIR}/gold_4h.csv")
    resample_4h(f"{OUT_DIR}/eurusd_1h_6m.csv", f"{OUT_DIR}/eurusd_4h.csv")
