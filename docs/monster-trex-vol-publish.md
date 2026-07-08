# Monster Trex Vol — Publish کتابخانه‌ها در TradingView

خطای `does not have a published library` یعنی **هنوز آن کتابخانه را Publish نکرده‌ای**.

## ترتیب Publish (حتماً به همین ترتیب)

| # | فایل | نام `library()` | وابستگی |
|---|------|-----------------|----------|
| 1 | `khakster_trex_atr_lib.pine` | KhaksterTrexAtrLib | — |
| 2 | `khakster_smart_money_lib.pine` | KhaksterSmartMoneyLib | — |
| 3 | `candle_recognition_lib.pine` | CandleRecognitionLib | — |
| 4 | `market_structure_engine.pine` | MarketStructureEngine | TrexAtrLib |
| 5 | `khakster_entry_lib.pine` | KhaksterEntryLib | همه بالا |
| 6 | `khakster_final_strategy.pine` | Monster Trex Vol | همه |

## مراحل در TradingView

1. Pine Editor → New → کد فایل ۱ را paste کن
2. **Save** → **Publish script** → نوع: **Library** (نه Indicator)
3. نام باید دقیقاً همان `library("...")` باشد (مثلاً `KhaksterTrexAtrLib`)
4. تکرار برای ۲، ۳، ۴، ۵
5. بعد استراتژی Monster Trex Vol را Add to chart

## نکات

- در فایل‌های ۴ و ۵ importها `dorkadehali/...` هستند — فقط بعد از Publish قبلی‌ها کار می‌کند
- اگر نسخه ۲ publish کردی، import را `/2` کن
- Smart Money و Candle **قبل از** Entry باید publish شوند
