# روال پردازش ~۶۰ اندیکاتور

## برای شما — چطور فایل‌ها را بدهید

همه فایل `.txt` یا `.pine` را یکجا آپلود کنید یا در این پوشه بگذارید:
```
/home/ubuntu/.cursor/projects/workspace/uploads/
```

یا در ریپو:
```
backtest/sources/
```

## برای هر فایل این کارها انجام می‌شود

1. **بررسی کامل بودن کد** (ناقص / duplicate / بدون @version)
2. **تحلیل منطق** (محدوده‌ای / روند / الگو / استراتژی)
3. **بررسی فنی** (repaint، lookahead، سیگنال)
4. **بک‌تست آفلاین ۱ ماه** (در صورت امکان)
5. **ثبت نقاط قوت/ضعف** در `results/LEARNING_JOURNAL.md`
6. **فهرست** در `results/INDICATOR_INDEX.json`

## مدل ریسک (ثابت)

| بازار | SL | TP |
|-------|-----|-----|
| کریپتو | 5% | 5% |
| فارکس | 3 pip | RR 1:1 |

## داده

بایننس → OKX → KuCoin → Gate → Yahoo

## اجرای batch

```bash
cd backtest
python3 batch_analyze.py          # اسکن همه فایل‌ها
python3 run_backtest.py           # بک‌تست اندیکاتورهای پیاده‌شده
```

## وضعیت فعلی

| # | اندیکاتور | منبع | وضعیت |
|---|-----------|------|--------|
| 1 | UT Bot v2 | چت | ✅ |
| 2 | AlphaTrend | چت | ✅ |
| 3 | Bj Bot | چت | ✅ |
| 4 | AlphaX FORGE | forg_6b2d.txt | ✅ |
| 5 | FibFib | چت | ✅ |
| 6 | Quadapt ML Trader | quadpad (تکراری) | ✅ |

**فایل‌های در uploads الان: ۳ (۲ تا تکراری Quadapt)**

## فایل‌های ناقص

در پایان پردازش ۶۰ فایل، لیست کامل در:
- `results/INDICATOR_INDEX.json` → `incomplete_files`
- `results/INDICATOR_INDEX.md`
