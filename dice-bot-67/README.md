# Dice Bot 67 — Six Seven Chat

از روی اسکرین‌شات‌ها مشخص شد جریان بازی این است:

1. ایموجی 🎲 یا 🎰 انتخاب می‌شود  
2. باکس سیاه تلگرام ظاهر می‌شود: *Send a 🎲 emoji to any chat to try your luck*  
3. روی **Send** داخل همان باکس کلیک می‌شود  

برای این کار **دو حالت** داریم:

| حالت | توضیح | پیشنهاد |
|------|--------|---------|
| `userbot` | با Telethon مستقیم تاس می‌فرستد | ✅ بهتر و پایدار |
| `desktop` | با موس روی تلگرام دسکتاپ کلیک می‌کند | اگر UserBot نخواهید |

> استفاده شخصی با مسئولیت خودتان. اتوماسیون ممکن است خلاف قوانین بازی/تلگرام باشد.

---

## حالت ۱ — UserBot (پیشنهادی)

بدون نیاز به مختصات صفحه؛ مستقیم به گروه `Six Seven Chat 8` تاس می‌فرستد.

### ۱) گرفتن api_id / api_hash
از [my.telegram.org/apps](https://my.telegram.org/apps)

### ۲) نصب و تنظیم
```bat
cd dice-bot-67
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.example.json config.json
```

در `config.json`:
```json
{
  "mode": "userbot",
  "api_id": 12345678,
  "api_hash": "abcd...",
  "target_chat": "Six Seven Chat 8",
  "min_delay_sec": 61,
  "max_delay_sec": 100,
  "delay_change_every_cycles": 10
}
```

اگر گروه username دارد همان را بگذارید؛ وگرنه نام دقیق گروه کافی است (باید عضو باشید).

### ۳) اجرا
```bat
python main.py
```
بار اول شماره تلفن و کد تلگرام را می‌پرسد. بعد **F8** = شروع/توقف.

چرخه:
```
🎲 → صبر(T) → 🎰 → صبر(T) → ...
هر ۱۰ چرخه کامل، T جدید بین 61..100
```

---

## حالت ۲ — Desktop (کلیک موس)

برای وقتی که می‌خواهید همان UI تلگرام دسکتاپ را شبیه‌سازی کنید.

```bat
python main.py --calibrate
python main.py --mode desktop
```

در کالیبره به‌ترتیب این‌ها را علامت بزنید:
1. دکمه ایموجی کنار کادر پیام  
2. خود 🎲  
3. خود 🎰  
4. کلمه **Send** داخل باکس سیاه (نه میکروفون)

اختیاری:
```bat
python main.py --capture-templates
```

---

## تنظیمات مشترک

| کلید | معنی |
|------|------|
| `min_delay_sec` / `max_delay_sec` | بازه صبر (۶۱–۱۰۰) |
| `delay_change_every_cycles` | هر چند چرخه زمان عوض شود (۱۰) |
| `send_delay_min_sec` / `max` | تأخیر انسانی بین اکشن‌ها |
| `hotkey_toggle` | پیش‌فرض `f8` |

## ساخت exe
```bat
build_exe.bat
```

## تست
```bat
pytest -q
```
