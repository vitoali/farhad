# ICT 2022 / Silver Reversal — مشخصات مکانیکی

استراتژی اسکالپ/دی‌ترید **دوطرفه** (Long + Short) روی چارت **M1** با فیلترهای HTF.

## زمان‌بندی (مهم برای کاربر ایران)

همهٔ سشن‌ها و Killzoneها با timezone ثابت **`America/New_York`** محاسبه می‌شوند.  
ساعت سیستم یا لوکیشن ایران **هیچ اثری** ندارد؛ فقط `timestamp` چارت + timezone NY مهم است.

| سشن | ساعت NY | کاربرد |
|-----|---------|--------|
| Asian | 20:00–00:00 | جایگزین TP1 اگر ورود در لندن باشد |
| London Open KZ | 02:00–05:00 | ورود مجاز + تعریف London High/Low |
| New York KZ | 07:00–10:00 | ورود مجاز |
| Forex day reset | 17:00 | ریست فلگ‌های سوئیپ/ستاپ همان روز |

ورود جدید **فقط** داخل London Open KZ یا NY KZ.

## مراحل (هر دو جهت)

1. **HTF Sweep (H1 یا H4)** — پیوت پیش‌فرض ۵/۵ (قابل تنظیم)  
   - Short: شدو بالای Swing High، کلوز زیر آن  
   - Long: شدو زیر Swing Low، کلوز بالای آن  
2. **SMT** با جفت هم‌بسته (`request.security`)  
3. **FVG Fill** — تشخیص به سبک LuxAlgo FVG؛ پر شدن = تاچ لبه یا CE (۵۰٪)  
   - Sweep H4 → FVGهای H4 **یا** H1  
   - Sweep فقط H1 → فقط FVG یک‌ساعته  
4. **M5 CHoCH** — کلوز بدنه از آخرین HL/LH معتبر  
5. **M5 OTE** — اصلاح ۶۱٫۸٪–۷۰٫۵٪ از لگ بعد از CHoCH  
6. **M1 Displacement** — بدنه ≥ `1.5 × ATR(10)` + ساخت FVG؛ ورود لیمیت روی لبهٔ FVG  

## خروج

- **SL:** پشت سوئینگ ۱دقیقه + ۲ پیپ/تیک  
- **TP1 (۵۰٪):** London H/L همان روز (اگر لندن تمام شده)؛ وگرنه Asia H/L یا نقدینگی ۵دقیقه  
- بعد از TP1 → SL به ورود (ریسک‌فری)  
- **TP2 (۵۰٪):** Previous Day High/Low  
- فیلتر: R:R تا TP1 حداقل **۱:۳**

## منبع الگوریتم‌های مرجع

- FVG detect: LuxAlgo Fair Value Gap (CC BY-NC-SA 4.0) — فقط هستهٔ تشخیص، با attribution  
- Killzone windows: هم‌راستا با LuxAlgo ICT Killzones + بازهٔ NY طبق اسپک کاربر (07–10)

## بدون ریپینت

- `request.security(..., lookahead=barmerge.lookahead_off)`  
- تصمیم ورود فقط روی `barstate.isconfirmed`  
- پیوت‌ها پس از تکمیل `right` بار تأیید می‌شوند  
