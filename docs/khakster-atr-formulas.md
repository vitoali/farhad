# Khakster TRex ATR — Formulas

> **ATR display:** use TradingView community indicator **ATR TRex [ipooya]**  
> Guide: [`trex-atr-tradingview-fa.md`](trex-atr-tradingview-fa.md)

`khakster_trex_atr_lib.pine` provides helpers only; `fetchMetrics()` is approximate.

## Files

| File | Role |
|------|------|
| `pine/khakster_trex_atr_lib.pine` | Core TR / TH / Live / pip conversion |
| `pine/trex_atr_panel.pine` | On-chart panel like MT5 |
| `pine/market_structure_engine.pine` | Pivot detection (uses ATR lib) |

## Fractal SMA periods (per timeframe)

| TF | Period | Note |
|----|--------|------|
| M1 | 3 | Trex MT4/5 fractal |
| M5 | 12 | Khakestar suggested |
| M15 | 16 | Khakestar suggested |
| H1 | 24 | Khakestar suggested |
| H4 | 42 | Khakestar suggested |
| D1 | 30 | Khakestar suggested |
| W1 | 52 | Khakestar suggested |
| Mn | **55** | ATR55 (monthly) |

## Core metrics

```
TR  = round_pips( SMA( true_range, period_tf ) )
TH  = round_pips( TR × boost_tf )     // توان حرکتی / APR
Live = round_pips( high - low )       // حرکت کندل جاری
```

### TH boost (calibrated vs AUDDKK sample)

| TF | boost |
|----|-------|
| M1, W1, Mn | 1.00 |
| M5 | 1.07 |
| M15 | 1.30 |
| H1 | 1.20 |
| H4 | 1.49 |
| D1 | 1.57 |

## Panel rows (MT5 TRex)

- **True Range:** `TR ==> Live` per fractal TF
- **Pips(ATR):** `round(TP(Th) × 5/6)` for structure / pattern / trigger TF
- **TP(Th):** `round(TH × 3)` for same three TFs
- **Eng SL:** `round(TR × 0.25)` on structure TF
- **Pivot SL:** `TR + Eng SL`

## Candle classes (vs TR)

| Class | Range |
|-------|-------|
| Spinning | < 80% TR |
| Standard | 80–120% TR |
| Long bar | 120–240% TR |
| Spike | > 240% TR |

## Forex vs Crypto

- **Forex:** pip = 0.0001 (0.01 for JPY pairs)
- **Crypto:** uses `syminfo.mintick` as unit (adjust in settings if needed)

## Pivot rules (Market Structure Engine)

1. Move ≥ **2.4 × TR** on left (3 candles)
2. Revert ≥ **1 × TR**
3. Master candle at tip OR ATR line rule
4. Engulf + close in final third of range
5. Zone: from tip to body (open/close overlap)

## Reference files (local)

- `docs/khakster-atr/TRex.ex5` — original compiled indicator (not in git)
- `docs/khakster-atr/trex-eurusd-m1-template.chr` — MT5 chart template

## TradingView setup

1. Publish `KhaksterTrexAtrLib` as library
2. Publish `MarketStructureEngine` (imports ATR lib)
3. Add `trex_atr_panel.pine` to chart; fix `import YOUR_USER/...`
