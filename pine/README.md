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

Formulas: [`docs/candle-recognition-formulas.md`](../docs/candle-recognition-formulas.md)
