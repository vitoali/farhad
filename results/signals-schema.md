# اسکیمای ثبت سیگنال‌ها و محدوده‌ها

هر سیگنال/محدوده یک ردیف. این فیچرها بعداً برای آزمون فرضیه‌ها (بخش ۵ هر تحلیل) استفاده می‌شوند.

| ستون | نوع | توضیح |
|---|---|---|
| `code_id` | int | شماره کد (NNN) |
| `symbol` | str | مثلاً BTCUSDT |
| `timeframe` | str | 5m/15m/1h/4h/1d |
| `direction` | str | long/short |
| `formed_at` | datetime | زمان تثبیت (نه زمان رسم اولیه) |
| `zone_top` / `zone_bottom` | float | لبه‌های محدوده (برای سیگنال نقطه‌ای: قیمت سیگنال در هر دو) |
| `first_touch_at` | datetime/null | زمان نخستین لمس معتبر پس از تثبیت |
| `bars_to_touch` | int/null | تعداد کندل تا نخستین لمس |
| `zone_age_at_touch` | int | سن محدوده هنگام لمس (کندل) |
| `touch_count_before` | int | تعداد لمس‌های قبلی همین محدوده |
| `penetration_depth` | float | حداکثر عمق نفوذ به محدوده (نسبت به ارتفاع محدوده، 0–1+) |
| `reaction` | enum | favorable / break / pierce_return / invalidated_before_touch |
| `entry_price` / `sl_price` / `tp_price` | float | مطابق مدل ریسک |
| `risk_model` | str | مثلاً crypto_sl1_tp2 یا fx_sl3_rr2 |
| `outcome` | enum | tp / sl / invalidated / open |
| `outcome_r` | float | نتیجه بر حسب R پس از هزینه‌ها |
| `bars_in_trade` | int | مدت معامله |
| `htf_trend` | enum | up/down/range (روند تایم‌فریم بالاتر در لحظه سیگنال) |
| `sweep_before` | bool | sweep سقف/کف قبل از تشکیل |
| `displacement` | bool | کندل displacement در تشکیل |
| `confluent_fvg` | bool | FVG هم‌جهت در نزدیکی |
| `rel_volume` | float | حجم نسبی کندل تشکیل (نسبت به میانگین ۲۰) |
| `prior_breaks` | int | تعداد شکست‌های قبلی محدوده‌های مشابه اخیر |
| `session` | str | جلسه معاملاتی (برای فارکس/طلا) |
| `notes` | str | آزاد |
