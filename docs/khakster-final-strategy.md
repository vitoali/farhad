# Khakster Final Strategy — MTF

استراتژی نهایی بر اساس کتابخانه‌های واقعی پروژه (نه نام‌های جمینای).

## نگاشت کتابخانه‌ها

| جمینای | پروژه ما |
|--------|----------|
| Lib_Khakestar | `MarketStructureEngine` + `KhaksterEntryLib` + `KhaksterTrexAtrLib` |
| Lib_SmartMoney | `KhaksterSmartMoneyLib` |
| Lib_CandlePatterns | `CandleRecognitionLib` |

## فایل

`pine/khakster_final_strategy.pine` — **Khakster Final MTF**

## منطق (طبق پرامپت جمینای)

```
۱. سطوح FTC/RTP روی HTF (Mn/W/D/H4/H1 — قابل انتخاب)
۲. Smart Money: حداقل ۲/۳ (L + OB + V) روی zone سطح
۳. تریگر روی TF پایین (جفت انتخابی):
   - FTC/RTP touch
   - یا هر یک از **۶۴ الگوی** CandleRecognitionLib (صعودی برای خرید / نزولی برای فروش)
۴. سیگنال فقط barstate.isconfirmed (بدون repainting)
۵. request.security با lookahead_off
```

## جفت تایم‌فریم (Dropdown)

| حالت | ساختار | تریگر |
|------|--------|-------|
| H4 + M15 | 240 | 15 |
| **H1 + M5** | 60 | 5 |
| D + H1 | D | 60 |
| W + H4 | W | 240 |

**چارت را روی تایم تریگر بگذارید** (مثلاً M5).

## نصب

Publish به ترتیب:
1. KhaksterTrexAtrLib
2. MarketStructureEngine
3. KhaksterEntryLib
4. KhaksterSmartMoneyLib
5. CandleRecognitionLib
6. `khakster_final_strategy.pine`

## بهبودهای اعمال‌شده

| ویژگی | توضیح |
|--------|--------|
| **فیلتر سشن (FX)** | لندن ۰۷–۱۶ UTC / نیویورک ۱۳–۲۱ UTC — فقط روی فارکس |
| **SM روی HTF** | `request.security` + `confluencePackAtZone` — نه چارت تریگر |
| **pipScale BTC** | `trex.settingsForSymbol()` — ۱ پیپ ≈ ۰.۰۱٪ قیمت |
| **حداقل امتیاز BTC** | `max(minScore, 50)` برای کریپتو |

## بک‌تست آفلاین (۱ هفته)

```bash
python3 tests/backtest_final_strategy.py
```

خروجی: `tests/backtest_final_1w_results.json`

## جدول گوشه چارت

نمایش: جفت TF فعال، SM روی HTF، حداقل امتیاز، سشن (FX)، آیا قیمت در سطح است، تعداد سطوح فعال.
