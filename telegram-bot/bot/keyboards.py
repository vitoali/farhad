"""کیبوردهای اینلاین و ریپلای."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        ["📡 آخرین راهنما", "🔔 وضعیت اشتراک"],
        ["✅ عضویت در سیگنال", "⏸ لغو اشتراک"],
    ]
    if is_admin:
        rows.append(["🛠 پنل ادمین"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 ارسال پیام همگانی", callback_data="admin:broadcast"),
                InlineKeyboardButton("📊 آمار", callback_data="admin:stats"),
            ],
            [
                InlineKeyboardButton(
                    "📝 راهنمای ارسال سیگنال", callback_data="admin:signal_help"
                )
            ],
        ]
    )
