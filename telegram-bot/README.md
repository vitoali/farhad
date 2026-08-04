# ربات سیگنال تلگرام

ربات فارسی برای ارسال سیگنال معاملاتی به اعضا، با پنل ادمین و دریافت هشدار از **TradingView**.

## امکانات

- عضویت / لغو اشتراک کاربران
- ارسال سیگنال دستی توسط ادمین
- پیام همگانی
- وب‌هوک TradingView (`POST /tv`)
- ذخیره کاربران و سیگنال‌ها در SQLite

## راه‌اندازی سریع

### ۱) ساخت ربات در تلگرام

1. به [@BotFather](https://t.me/BotFather) بروید و `/newbot` بزنید.
2. توکن را کپی کنید.
3. آیدی عددی خودتان را از [@userinfobot](https://t.me/userinfobot) بگیرید.

### ۲) نصب

```bash
cd telegram-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

فایل `.env` را ویرایش کنید:

```env
BOT_TOKEN=توکن_ربات
ADMIN_IDS=آیدی_عددی_شما
WEBHOOK_SECRET=یک_رمز_بلند_تصادفی
WEBHOOK_PORT=8080
```

### ۳) اجرا

```bash
python -m bot
```

ربات با *polling* بالا می‌آید و همزمان سرور وب‌هوک روی پورت `8080` گوش می‌دهد.

## ارسال سیگنال دستی (ادمین)

در چت ربات:

```text
EURUSD BUY
entry: 1.0850
sl: 1.0800
tp: 1.0950
tf: M15
note: ICT Judas
```

یا از دکمه «🛠 پنل ادمین».

## اتصال TradingView

در آلرت TradingView، Webhook URL را این‌طور بگذارید (باید از اینترنت در دسترس باشد، مثلاً با ngrok):

```text
https://YOUR_PUBLIC_HOST/tv?secret=YOUR_WEBHOOK_SECRET
```

### نمونه پیام آلرت (متن)

```text
{{ticker}},BUY,entry={{close}},sl=0,tp=0,tf={{interval}},note={{strategy.order.comment}}
```

### نمونه JSON

```json
{
  "symbol": "{{ticker}}",
  "side": "buy",
  "entry": "{{close}}",
  "sl": "2340",
  "tp": "2370",
  "tf": "{{interval}}",
  "note": "Cardwell"
}
```

اگر سرورتان پشت فایروال است:

```bash
ngrok http 8080
```

سپس URL عمومی ngrok را در TradingView قرار دهید.

## دستورات

| دستور | توضیح |
|--------|--------|
| `/start` | شروع و منو |
| `/help` | راهنما |
| `/subscribe` | عضویت |
| `/unsubscribe` | لغو اشتراک |
| `/status` | وضعیت عضویت |
| `/admin` | پنل ادمین |
| `/cancel` | انصراف از مکالمه ادمین |

## تست

```bash
pip install pytest
pytest -q
```

## ساختار

```text
telegram-bot/
  bot/
    config.py      # تنظیمات
    db.py          # SQLite
    handlers.py    # دستورات و دکمه‌ها
    signals.py     # پارس/فرمت سیگنال
    webhook.py     # TradingView HTTP
    __main__.py    # اجرا
  .env.example
  requirements.txt
  tests/
```

## نکات

- بدون `BOT_TOKEN` ربات اجرا نمی‌شود.
- فقط آیدی‌های داخل `ADMIN_IDS` به پنل ادمین دسترسی دارند.
- اگر `WEBHOOK_SECRET` تنظیم شود، درخواست‌های بدون این رمز رد می‌شوند.
