# Pine Scripts — کتابخانه کندل‌شناس

## Main library (for strategies)

**`candle_recognition_lib.pine`** → publish as `CandleRecognitionLib`

- 64 Nison candlestick patterns
- `isPatternActive(id, settings)` — detection
- `patternKind(id)` — 0 Reversal, 1 Continuation, 2 Context
- `patternBullish` / `patternBearish` — bias

```pine
import YOUR_USER/CandleRecognitionLib/1 as cr
s = cr.defaultSettings()
if cr.isPatternActive(37, s)  // Morning Star
    ...
```

## Scanner (visual only)

**`nison_candlestick_scanner.pine`** — lines + Reversal/Continuation/Context tags

## Khakster TRex ATR

**`khakster_trex_atr_lib.pine`** → publish as `KhaksterTrexAtrLib`

- TR / TH / Live per fractal TF (M1→Mn)
- Forex pips + crypto mintick
- Candle class (Spinning / Standard / LongBar / Spike)

**`trex_atr_panel.pine`** — panel like MT5 TRex indicator

**`market_structure_engine.pine`** → publish as `MarketStructureEngine`

- Pivot detection using Khakster ATR rules
- Import `KhaksterTrexAtrLib`

Formulas: [`docs/khakster-atr-formulas.md`](../docs/khakster-atr-formulas.md)

Formulas (candles): [`docs/candle-recognition-formulas.md`](../docs/candle-recognition-formulas.md)
