# Khakster Smart Money Library

کتابخانه همگرایی **اسمارت‌مانی** برای تأیید «پول داخل سطح» Khakster.

## سه منبع سیگنال

| # | منبع | اندیکاتور مرجع | چه چیزی تأیید می‌کند |
|---|------|----------------|----------------------|
| 1 | **Liquidity (L)** | LuxAlgo Liquidity Sweeps | سویپ نقدینگی در محدوده سطح |
| 2 | **Order Block (OB)** | LuxAlgo Smart Money Concepts | بلوک سفارش هم‌جهت با سطح |
| 3 | **Volume (V)** | Volume Profile (LonesomeTheBlue) | POC یا Value Area داخل سطح |

## قانون همگرایی

```
تأیید = حداقل ۲ از ۳ (پیش‌فرض) یا هر ۳ تا
```

برای **مقاومت (R / isHigh)**:
- L: سویپ نزولی (wick بالای pivot)
- OB: بلوک Bearish
- V: POC/VA داخل zone

برای **حمایت (S)**:
- L: سویپ صعودی
- OB: بلوک Bullish
- V: POC/VA داخل zone

## فایل‌ها

| فایل | نقش |
|------|-----|
| `pine/khakster_smart_money_lib.pine` | کتابخانه |
| `pine/smart_money_confluence_chart.pine` | تست بصری |
| `pine/vendor/luxalgo/` | سورس مرجع (فقط مطالعه) |

## نصب

1. Publish `KhaksterSmartMoneyLib`
2. در استراتژی نهایی:

```pine
import YOUR_USER/KhaksterSmartMoneyLib/1 as sm

var sm.SmartMoneyState smSt = sm.newSmartMoneyState()
smS = sm.defaultSmartMoneySettings()  // minConfirmations = 2

smSt := sm.tickSmartMoney(smSt, smS)  // هر بار

[ok, cnt, liq, ob, vol] = sm.zoneConfluence(smSt, zTop, zBot, isHigh, smS)
if ok
    // ورود با تأیید اسمارت‌مانی
```

## Pack (۵ فیلد)

```
confirmed, count, liquidity, orderBlock, volume
```

## اتصال به استراتژی Khakster (بعداً)

```
سطح H1 (MSE) + ورود M5 (EntryLib) + smartMoney ok (۲/۳) → ترید
```

## مجوز مرجع

- LuxAlgo: CC BY-NC-SA 4.0 — منطق بازنویسی شده برای کتابخانه Khakster (بدون کپی مستقیم UI)
- Volume Profile: MPL 2.0
