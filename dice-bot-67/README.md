# Dice Bot 67 — Six Seven Chat

## راه آسان (پیشنهادی): BotFather — بدون my.telegram.org

1. در تلگرام به [@BotFather](https://t.me/BotFather) برو → `/newbot` → توکن بگیر
2. ربات را به گروه **Six Seven Chat 8** اضافه کن
3. `DiceBot67-Windows.zip` را از `dist/` دانلود کن
4. `config.example.json` را به `config.json` تغییر نام بده
5. فقط این را پر کن:

```json
{
  "mode": "bot",
  "bot_token": "TOKEN_FROM_BOTFATHER",
  "target_chat": "Six Seven Chat 8"
}
```

6. `DiceBot67.exe` → **F8**

### دانلود
https://github.com/vitoali/farhad/raw/cursor/telegram-dice-game-bot-2cf0/dice-bot-67/dist/DiceBot67-Windows.zip

> اگر بازی به ربات امتیاز نداد، یعنی فقط اکانت واقعی قبول می‌کند؛ آن وقت باید از `my.telegram.org` با VPN، `api_id/api_hash` بگیری یا حالت desktop را استفاده کنی.

---

## حالت UserBot (Telethon)
نیاز به `api_id` و `api_hash` از https://my.telegram.org/apps

## حالت Desktop (کلیک موس)
```bat
python main.py --calibrate
python main.py --mode desktop
```

## زمان‌بندی
- صبر تصادفی ۶۱–۱۰۰ ثانیه
- هر ۱۰ چرخه کامل زمان عوض می‌شود
- F8 شروع/توقف
