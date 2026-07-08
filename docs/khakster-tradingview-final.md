# Khakster — حالت نهایی برای TradingView

**حالت Structure** — همان منطقی که در بک‌تست کیفیت بهتری داشت (بدون MTF الگو+SM پرنویز).

---

## ۱. Publish کتابخانه‌ها (ترتیب مهم)

در Pine Editor → هر فایل را **Add to chart** نکنید؛ **Publish** کنید:

| # | فایل | نام کتابخانه در TV |
|---|------|-------------------|
| 1 | `pine/khakster_trex_atr_lib.pine` | `KhaksterTrexAtrLib` |
| 2 | `pine/market_structure_engine.pine` | `MarketStructureEngine` |
| 3 | `pine/khakster_entry_lib.pine` | `KhaksterEntryLib` |
| 4 | `pine/khakster_smart_money_lib.pine` | `KhaksterSmartMoneyLib` |
| 5 | `pine/candle_recognition_lib.pine` | `CandleRecognitionLib` |

در هر فایل `YOUR_USER` را با **username TradingView** خود عوض کنید.

---

## ۲. استراتژی نهایی

فایل: `pine/khakster_final_strategy.pine`  
نام روی چارت: **Khakster Final Structure**

### چارت
- نماد: EURUSD، NAS100، BTCUSD و …
- **تایم‌فریم چارت = تریگر** (پیش‌فرض **M5**)

---

## ۳. تنظیمات پیش‌فرض (حالت نهایی)

### TF Pair
| نماد | پیشنهاد |
|------|---------|
| فارکس | **H1 + M5** |
| نزدک | **H1 + M5** |
| کریپتو | **H1 + M5** یا H4+M15 |

### HTF scan
| گزینه | مقدار |
|--------|--------|
| Mn | خاموش |
| W1 | روشن |
| D1 | روشن |
| H4 | روشن |
| H1 | روشن |

### Smart Money
| گزینه | مقدار |
|--------|--------|
| **Min SM confirmations** | **2** (از ۳: L + OB + V) |

### Session
| گزینه | مقدار |
|--------|--------|
| Filter session | **روشن** |
| London | 07–16 UTC |
| NY | 13–21 UTC |

> فارکس: لندن **یا** نیویورک  
> نزدک/فیوچرز: فقط NY  
> کریپتو: فیلتر سشن اعمال نمی‌شود

### Entry
| گزینه | مقدار |
|--------|--------|
| Min structure score | **40** (کریپتو: حداقل **50**) |
| FTC / RTP | روشن |
| Candle in zone | روشن (۶۴ الگو) |
| SL | TH × **0.5** |
| TP | TH × **3.0** |

---

## ۴. منطق سیگنال (خلاصه)

```
سطح Reverse + FTC credible روی HTF (W/D/H4/H1)
    ↓
امتیاز ≥ 40  +  SM ≥ 2/3 روی همان TF سطح
    ↓
سشن L/NY (FX) یا NY (نزدک)
    ↓
تریگر روی M5:
  • لمس FTC یا RTP
  • یا الگوی کندل داخل zone سطح
    ↓
ورود + SL/TP (TH-based)
```

**فقط پیوت Reverse** — Pullback/Settlement در این حالت پذیرفته نمی‌شود.

---

## ۵. جدول گوشه چارت

| ردیف | معنی |
|------|------|
| Mode | Structure |
| Pair | جفت TF |
| Trigger | M5 / M15 / … |
| SM | 2/3 HTF |
| Min score | 40 یا 50 |
| Session | L/NY / NY / off |
| In level | قیمت در zone |
| Active Lv | سطوح watch |

---

## ۶. بک‌تست مرجع (۳۰ روز، همین حالت)

| نماد | ترید | Win% | trex-pip |
|------|------|------|----------|
| EURUSD | ~2–4 | ~75% | +48 |
| NASDAQ | ~4–5 | ~60% | +120–184 |
| BTC | ~0–2 | — | متغیر |

فرکانس کم، کیفیت بالاتر — عمدی است.

---

## ۷. چیزهایی که در حالت نهایی نیست

- ❌ MTF الگو+SM روی H4/H1/M15/M5 (حذف شد — نویز زیاد)
- ❌ SM = 1/3
- ❌ min score = 30
- ❌ Pullback / Settlement

اگر بعداً خواستی سیگنال بیشتر: فقط `Min SM` را 1 کن یا `Min score` را 30 — ولی کیفیت پایین می‌آید.
