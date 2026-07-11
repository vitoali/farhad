# #86 Stop Hunt Radar [GBB]

**فایل:** `STOP_HUNT_c561.txt`
**تاریخ:** 2026-07-11 19:06 UTC
**نوع:** indicator | Pine v6
**دسته:** zone/smc
**کامل:** بله
**بک‌تست:** partial_manual

## ویژگی‌های فنی

- سیگنال buy/sell: True
- SL/TP در کد: True
- Order Block: False
- FVG: False
- Fib: False
- barstate.isconfirmed: False
- request.security: True

## یادداشت‌های تحلیل استاتیک

- ریسک lookahead در request.security
- سیگنال بدون barstate.isconfirmed

## بک‌تست

نیاز به پورت دستی یا بک‌تستر zone/pattern.
