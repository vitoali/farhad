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

## تنظیمات فعلی (relaxed)

| پارامتر | مقدار |
|---------|--------|
| SM min | **1/3** |
| Min score | **30** |
| سشن | **حذف شده** |
| نوع پیوت | Reverse + Pullback + Settlement |
| FTC credible | همچنان لازم |

## بک‌تست آفلاین

```bash
python3 tests/backtest_final_strategy.py          # ۳۰ روز
python3 tests/backtest_final_strategy.py --days 7
```

خروجی: `tests/backtest_final_results.json`

## جدول گوشه چارت

نمایش: جفت TF فعال، SM روی HTF، حداقل امتیاز، سشن (FX)، آیا قیمت در سطح است، تعداد سطوح فعال.
