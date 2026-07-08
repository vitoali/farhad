# Market Structure Engine — فاز ۳

## اضافه‌شده نسبت به فاز ۲

| قابلیت | توضیح |
|--------|--------|
| **نوع پیوت** | Reverse / Pullback / Settlement |
| **امتیاز نوع** | Reverse +15، Pullback −18، Settlement −28 |
| **فیلتر همپوشانی** | سطح TF پایین‌تر اگر با TF بالاتر هم‌جهت همپوشانی دارد → حذف |
| **FTC با گره** | قابل‌استناد = پوشاننده گره ۳ کندل قبل از مستر را بشکند |
| **استراتژی FTC** | ورود فقط Reverse + FTC معتبر روی تاچ اول FTC |

## سه نوع پیوت (فصل ۳ خاکستر)

| نوع | کاربرد | RR پیشنهادی |
|-----|--------|-------------|
| **Reverse** | ترید اصلی | TP ≈ 3× TH |
| **Pullback** | معمولاً معامله نمی‌شود | — |
| **Settlement** | حداکثر ۱:۱ | TP ≈ 1× TH |

### تشخیص

```
Pullback: قیمت قبلاً نزدیک همان سطح بوده + شکست موقت و برگشت
Settlement: برگشت ≤ 1.15× TR + کندل Spinning/Standard
Reverse: بقیه موارد
```

## اندیکاتور Lv3

`market_structure_chart.pine` — نام: **Khakster Structure Lv3**

### تنظیمات جدید

| گزینه | پیش‌فرض |
|-------|---------|
| Only Reverse | روشن |
| Show Pullback | خاموش |
| Show Settlement | خاموش |
| Suppress lower-TF overlap | روشن |

### لیبل نمونه

```
D1 R
Rev S72 ✓
```

## استراتژی

`khakster_structure_strategy.pine` — **Khakster FTC Strategy**

| پارامتر | پیش‌فرض |
|---------|---------|
| Pivot TF | H4 |
| Min score | 40 |
| TP | TH × 3 |
| SL pad | TH × 0.5 (پشت zone) |

### منطق ورود

1. پیوت **Reverse** روی TF انتخابی
2. FTC **قابل استناد** (✓)
3. اولین تاچ FTC (قیمت وارد محدوده FTC شود)
4. SL پشت zone ساختار، TP بر اساس TH

## Pack جدید (۱۴ فیلد)

```
sig, zoneTop, zoneBot, price, time, isHigh,
inTop, inBot, ftcTop, ftcBot, ftcCred, score,
pivotKind, thPips
```

## نصب

1. Publish `KhaksterTrexAtrLib`
2. Publish `MarketStructureEngine` (فاز ۳)
3. اندیکاتور `market_structure_chart.pine` یا استراتژی `khakster_structure_strategy.pine`
4. `YOUR_USER` را با نام کاربری TradingView عوض کنید
