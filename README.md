# farhad

## Auto Trend Line Indicator (اندیکاتور ترند لاین)

A TradingView **Pine Script v5** indicator that automatically draws trend lines on your
chart. It detects swing pivots and connects them to plot dynamic **support** and
**resistance** trend lines, extends them into the future, and can highlight/alert on
breakouts.

File: [`trend_line.pine`](./trend_line.pine)

### Features

- **Automatic trend lines** – connects the two most recent pivot highs (resistance /
  descending line) and the two most recent pivot lows (support / ascending line).
- **Right extension** – lines project forward so you can anticipate future reactions.
- **Breakout detection** – marks bars where price closes beyond a trend line and exposes
  ready-to-use `alertcondition`s.
- **Fully configurable** – pivot sensitivity, colors, line width, pivot markers, and
  breakout highlighting.

### Inputs

| Input | Description |
| --- | --- |
| Pivot Left / Right Bars | How many bars confirm a swing pivot. Higher = fewer, stronger pivots. |
| Extend Lines to the Right | Project trend lines into the future. |
| Line Width | Thickness of the trend lines. |
| Resistance / Support color | Colors of the two lines. |
| Show Pivot Markers | Draw `H`/`L` labels at detected pivots. |
| Highlight Breakouts | Show `B`/`S` markers when price breaks a line. |

### How to use

1. Open [TradingView](https://www.tradingview.com/) and go to **Pine Editor**.
2. Paste the contents of `trend_line.pine`.
3. Click **Add to chart**.
4. (Optional) Create an alert and pick one of the breakout conditions.

---

### فارسی

این یک اندیکاتور **Pine Script نسخه ۵** برای تریدینگ‌ویو است که به‌صورت خودکار خطوط
روند (ترند لاین) را روی نمودار رسم می‌کند. با شناسایی نقاط پیوت (سقف‌ها و کف‌های نوسانی)،
خطوط **حمایت** و **مقاومت** پویا را رسم کرده، آن‌ها را به سمت آینده امتداد می‌دهد و
شکست خطوط را با هشدار و نشانه‌گذاری نمایش می‌دهد.

**نحوهٔ استفاده:**

۱. در تریدینگ‌ویو وارد **Pine Editor** شوید.

۲. محتوای فایل `trend_line.pine` را کپی و جای‌گذاری کنید.

۳. روی **Add to chart** کلیک کنید.

۴. در صورت نیاز، از شرط‌های شکست برای ساخت آلارم استفاده کنید.
