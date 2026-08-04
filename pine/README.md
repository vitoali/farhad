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

## Trex Trend Panel (خاکستر)

**`trex_trend_panel.pine`** — روند صعودی/نزولی روی Mn, W, D, H4, H1, M15, M5

**نیاز:** Publish `KhaksterTrexAtrLib` + `MarketStructureEngine` (از همین ریپو)

```pine
import dorkadehali/KhaksterTrexAtrLib/1 as trex
import dorkadehali/MarketStructureEngine/1 as mse
```

منطق روند: آخرین پیوت **Reverse** + **FTC ✓** روی هر TF؛ شکست zone → «شکست».

Formulas: [`docs/candle-recognition-formulas.md`](../docs/candle-recognition-formulas.md)
