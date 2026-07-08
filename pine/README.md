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

**ATR دقیق (پیشنهادی):** [Trex [MrD3v]](https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/) — مستقیم روی چارت Add کنید

راهنما: [`docs/trex-atr-tradingview-fa.md`](../docs/trex-atr-tradingview-fa.md)

**`khakster_trex_atr_lib.pine`** → `KhaksterTrexAtrLib` — فقط helpers (پیپ، کلاس کندل، TF)

**`market_structure_engine.pine`** → `MarketStructureEngine` — پیوت (ATR دقیق بعد از import ipooya)

**`khakster_entry_lib.pine`** → `KhaksterEntryLib` — تریگر FTC/RTP (H1 ساختار + M5 ورود)

**`khakster_h1_m5_strategy.pine`** — استراتژی روی چارت M5

**`khakster_smart_money_lib.pine`** → `KhaksterSmartMoneyLib` — همگرایی L/OB/V برای تأیید پول در سطح

**`khakster_final_strategy.pine`** — استراتژی نهایی MTF (MSE + Entry + SM + Candle)

**`smart_money_confluence_chart.pine`** — تست بصری SM

**`trex_atr_panel.pine`** — فقط یادآوری؛ از ipooya استفاده کنید

Formulas: [`docs/khakster-atr-formulas.md`](../docs/khakster-atr-formulas.md)

Formulas (candles): [`docs/candle-recognition-formulas.md`](../docs/candle-recognition-formulas.md)
