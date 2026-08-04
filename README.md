# Indicator Win-Rate Analysis + Cardwell Hybrid

Persian analysis report: [`docs/ANALYSIS_FA.md`](docs/ANALYSIS_FA.md)

## Quick start
```bash
python3 backtest/download_data.py
python3 backtest/run_backtest.py
python3 backtest/run_improved.py
```

## Deliverables
- `indicators/Cardwell_Hybrid_Improved.pine` — Cardwell core + MACD/EWO/ADX/HTF filters, anti-flip lock, SL/TP state machine
- `backtest/results/` — CSV/JSON win-rate tables
- `docs/ANALYSIS_FA.md` — full strengths/weaknesses + hybrid rationale (FA)
