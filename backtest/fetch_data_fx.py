"""Fetch EURUSD data (Yahoo EURUSD=X): 1H for ~1 year, 15M for 40 days."""
from fetch_data import save_csv, fetch_yahoo, OUT_DIR

if __name__ == "__main__":
    save_csv(f"{OUT_DIR}/eurusd_1h_6m.csv", fetch_yahoo("EURUSD=X", "1h", "1y"))
    save_csv(f"{OUT_DIR}/eurusd_15m.csv", fetch_yahoo("EURUSD=X", "15m", "40d"))
