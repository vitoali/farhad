# Market Structure Engine — فاز ۴

## KhaksterEntryLib

کتابخانه ورود با **تایم فرکتالی خاکستر**:

| لایه | TF | نقش |
|------|-----|-----|
| ساختار | **H1** (`60`) | پیوت + Zone + FTC |
| پترن | **M15** (`15`) | گام حرکتی (آینده) |
| تریگر | **M5** (`5`) | ورود FTC / RTP |

```
H1 پیوت Reverse + FTC معتبر
        ↓
M5 اولین تاچ FTC → ورود Short/Long
        ↓ (اختیاری)
M5 تاچ RTP → ورود دوم
```

## فایل‌ها

| فایل | نقش |
|------|-----|
| `pine/khakster_entry_lib.pine` | کتابخانه Entry |
| `pine/khakster_h1_m5_strategy.pine` | استراتژی روی چارت **M5** |
| `tests/backtest_h1_m5.py` | بک‌تست آفلاین |
| `tests/mse_engine_py.py` | موتور Python (آینه MSE+Entry) |

## نصب TradingView

1. Publish: `KhaksterTrexAtrLib` → `MarketStructureEngine` → `KhaksterEntryLib`
2. چارت را روی **M5** بگذارید
3. Add strategy: `khakster_h1_m5_strategy.pine`

## بک‌تست آفلاین

```bash
pip install yfinance pandas numpy
python3 tests/backtest_h1_m5.py
```

خروجی: تعداد پیوت H1، تعداد ترید، win rate، مجموع پیپ → `tests/backtest_h1_m5_results.json`

## پارامترهای پیش‌فرض

| پارامتر | مقدار |
|---------|-------|
| Min structure score | 40 |
| SL pad | TH × 0.5 |
| TP | TH × 3 |
| FTC entry | روشن |
| RTP entry | روشن |

## API اصلی EntryLib

```pine
import YOUR_USER/KhaksterEntryLib/1 as entry

eS = entry.defaultEntrySettings()  // H1 / M15 / M5
entry.levelEligible(sig, sc, kind, ftcCred, eS)
entry.scanEntry(...)  // ENTRY_FTC | ENTRY_RTP | ENTRY_NONE
entry.entrySlTp(isHigh, zoneTop, zoneBot, pivotPrice, thPips, eS)
```
