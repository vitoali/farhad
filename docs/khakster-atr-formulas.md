# Khakster TRex ATR — Formulas

> **ATR display:** [Trex [MrD3v]](https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/) on chart  
> Guide: [`trex-atr-tradingview-fa.md`](trex-atr-tradingview-fa.md)

`khakster_trex_atr_lib.pine` — calibrated vs MT5/MrD3v on AUDDKK (see [`khakster-atr-calibration.md`](khakster-atr-calibration.md)).

## Files

| File | Role |
|------|------|
| `pine/khakster_trex_atr_lib.pine` | Core TR / TH / Live / pip conversion |
| `pine/trex_atr_panel.pine` | On-chart panel like MT5 |
| `pine/market_structure_engine.pine` | Pivot detection (uses ATR lib) |
| `pine/market_structure_chart.pine` | H1/H4/D1/W1/Mn level boxes on chart |

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

### TH boost (calibrated vs MT5 AUDDKK — 2026-07-08)

| TF | boost |
|----|-------|
| M1, W1, Mn | 1.000 |
| M5 | 1.071 |
| M15 | 1.250 |
| H1 | 1.154 |
| H4 | 1.494 |
| D1 | 1.573 |

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
