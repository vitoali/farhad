# ATR تیرکس در TradingView — Trex [MrD3v]

مرجع اصلی ATR: **[Trex [MrD3v]](https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/)**

این اندیکاتور فرمول اختصاصی سعید خاکستر را دارد و پنلش شبیه **TRex.ex5** در MT5 است (True Range، Th، Pips، Eng SL و …).

---

## اضافه کردن روی چارت (چک AUDDKK و بقیه)

1. چارت را باز کنید (مثلاً **AUDDKK** / **1H**)
2. **Indicators** (یا `fx`)
3. جستجو: `Trex MrD3v` یا `Trex amirkia27`
4. انتخاب **Trex [MrD3v]**
5. **Add to chart**

لینک مستقیم: https://www.tradingview.com/script/wv9EwdkR-Trex-MrD3v/

### تنظیمات پیشنهادی

- **V2** را روشن کنید (محاسبه دقیق‌تر تایم فعلی)
- برای همه TFها: نسخه ۱ (MTF کامل) — اگر اعداد تایم‌های دیگر غلط بود، V2 فقط TF جاری

### مقایسه با MT5

| MT5 TRex | MrD3v روی TV |
|----------|----------------|
| `[True Range] M1…Mn` | ردیف TR + Live |
| `[توان حرکتی Th]` | APR / TH |
| `Pips(ATR)` / `TP(Th)` | در پنل اندیکاتور |
| `Eng SL` / `Pivot SL` | در پنل |

---

## کنار اندیکاتورهای ما

| لایه | فایل / اندیکاتور |
|------|------------------|
| ATR (دقیق) | **Trex [MrD3v]** — از جامعه TV |
| کندل | `CandleRecognitionLib` |
| پیوت | `MarketStructureEngine` (در حال توسعه) |
| کالیبراسیون | `trex_atr_panel.pine` + [`khakster-atr-calibration.md`](khakster-atr-calibration.md) |

هر سه را روی یک چارت می‌توانید داشته باشید.

---

## استفاده در استراتژی (محدودیت مهم)

**Trex [MrD3v] سورس بسته (Protected)** است — نمی‌توان آن را مثل Library در استراتژی `import` کرد.

| هدف | راه‌حل |
|-----|--------|
| دیدن اعداد روی چارت | MrD3v را Add کنید |
| استراتژی با ATR دقیق در کد | فعلاً: MrD3v فقط بصری + استراتژی جدا؛ یا سورس باز [ipooya](https://www.tradingview.com/script/MeOUBz32-ATR-TRex-ipooya/) را Library کنید |
| اگر سورس MrD3v دارید | در `pine/vendor/` بگذارید تا به Library تبدیل کنیم |

---

## چرا پنل خودمان را ننوشتیم؟

فرمول دقیق داخل `TRex.ex5` / MrD3v است و عمومی نیست. بک‌تست ما با MT5 روی AUDDKK یکی نبود؛ MrD3v همان چیزی است که جامعه برای تطابق با خاکستر استفاده می‌کند.

---

## لینک‌های جایگزین (سورس باز)

اگر برای **کد استراتژی** به Library نیاز دارید:

| اندیکاتور | لینک |
|-----------|------|
| ATR TRex [ipooya] | https://www.tradingview.com/script/MeOUBz32-ATR-TRex-ipooya/ |
| ATR TRex [SHK] | https://www.tradingview.com/script/fYVUKY3q-ATR-TRex-SHK/ |

MrD3v برای **نمایش و ترید دستی**؛ ipooya/SHK برای **فورک به Library**.
