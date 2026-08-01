"""هندلرهای تلگرام."""

from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import Settings
from bot.db import Database
from bot.keyboards import admin_menu, main_menu
from bot.signals import Signal, parse_manual_signal

logger = logging.getLogger(__name__)

WAIT_BROADCAST = 1
WAIT_SIGNAL = 2

HELP_TEXT = """
سلام 👋 به *ربات سیگنال معاملاتی* خوش آمدید.

با عضویت، سیگنال‌های خرید/فروش برای شما ارسال می‌شود.

*دکمه‌ها:*
• ✅ عضویت در سیگنال
• ⏸ لغو اشتراک
• 🔔 وضعیت اشتراک
• 📡 آخرین راهنما

اگر ادمین هستید، از پنل ادمین می‌توانید سیگنال دستی بفرستید یا پیام همگانی بزنید.
""".strip()

SIGNAL_HELP = """
*ارسال سیگنال دستی*

پیام را دقیقاً با این فرمت بفرستید:

`EURUSD BUY`
`entry: 1.0850`
`sl: 1.0800`
`tp: 1.0950`
`tf: M15`
`note: ICT Judas`

یا برای فروش: `XAUUSD SELL`
""".strip()


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    db: Database = context.application.bot_data["db"]
    settings: Settings = context.application.bot_data["settings"]
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(is_admin(user.id, settings)),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    settings: Settings = context.application.bot_data["settings"]
    await update.message.reply_text(
        HELP_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(is_admin(update.effective_user.id, settings)),
    )


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    db: Database = context.application.bot_data["db"]
    user = update.effective_user
    db.upsert_user(user.id, user.username, user.first_name)
    db.set_subscribed(user.id, True)
    await update.message.reply_text("✅ عضویت شما فعال شد. سیگنال‌ها برایتان ارسال می‌شود.")


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    db: Database = context.application.bot_data["db"]
    db.set_subscribed(update.effective_user.id, False)
    await update.message.reply_text("⏸ اشتراک شما لغو شد. هر وقت خواستید دوباره عضو شوید.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    db: Database = context.application.bot_data["db"]
    user = db.get_user(update.effective_user.id)
    if user is None or not user.subscribed:
        text = "وضعیت: ❌ عضو نیستید"
    else:
        text = "وضعیت: ✅ عضو فعال سیگنال"
    await update.message.reply_text(text)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    settings: Settings = context.application.bot_data["settings"]
    if not is_admin(update.effective_user.id, settings):
        await update.message.reply_text("دسترسی ادمین ندارید.")
        return
    await update.message.reply_text("🛠 پنل ادمین:", reply_markup=admin_menu())


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query or not update.effective_user:
        return ConversationHandler.END
    await query.answer()
    settings: Settings = context.application.bot_data["settings"]
    if not is_admin(update.effective_user.id, settings):
        await query.edit_message_text("دسترسی ادمین ندارید.")
        return ConversationHandler.END

    data = query.data or ""
    if data == "admin:stats":
        db: Database = context.application.bot_data["db"]
        s = db.stats()
        await query.edit_message_text(
            "📊 آمار ربات\n"
            f"کل کاربران: {s['total_users']}\n"
            f"اعضای فعال: {s['subscribers']}\n"
            f"مسدود/ترک‌کرده: {s['blocked']}\n"
            f"تعداد سیگنال‌ها: {s['signals']}"
        )
        return ConversationHandler.END

    if data == "admin:signal_help":
        await query.edit_message_text(SIGNAL_HELP, parse_mode=ParseMode.MARKDOWN)
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="حالا سیگنال را با همان فرمت بفرستید، یا /cancel برای انصراف.",
        )
        return WAIT_SIGNAL

    if data == "admin:broadcast":
        await query.edit_message_text("متن پیام همگانی را بفرستید (یا /cancel).")
        return WAIT_BROADCAST

    return ConversationHandler.END


async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user or not update.message.text:
        return WAIT_BROADCAST
    settings: Settings = context.application.bot_data["settings"]
    if not is_admin(update.effective_user.id, settings):
        return ConversationHandler.END

    text = update.message.text
    sent, failed = await broadcast_text(context.application, text)
    await update.message.reply_text(f"ارسال شد: {sent}\nناموفق: {failed}")
    return ConversationHandler.END


async def receive_signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.effective_user or not update.message.text:
        return WAIT_SIGNAL
    settings: Settings = context.application.bot_data["settings"]
    if not is_admin(update.effective_user.id, settings):
        return ConversationHandler.END

    signal = parse_manual_signal(update.message.text)
    if signal is None:
        await update.message.reply_text(
            "فرمت سیگنال نامعتبر است. دوباره بفرستید یا /cancel\n\n" + SIGNAL_HELP,
            parse_mode=ParseMode.MARKDOWN,
        )
        return WAIT_SIGNAL

    sent, failed = await publish_signal(context.application, signal)
    await update.message.reply_text(f"سیگنال ارسال شد ✅\nموفق: {sent} | ناموفق: {failed}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مسیریابی دکمه‌های فارسی و سیگنال سریع ادمین."""
    if not update.message or not update.effective_user or not update.message.text:
        return

    text = update.message.text.strip()
    settings: Settings = context.application.bot_data["settings"]
    admin = is_admin(update.effective_user.id, settings)

    mapping = {
        "✅ عضویت در سیگنال": subscribe,
        "⏸ لغو اشتراک": unsubscribe,
        "🔔 وضعیت اشتراک": status,
        "📡 آخرین راهنما": help_cmd,
        "🛠 پنل ادمین": admin_panel,
    }
    handler = mapping.get(text)
    if handler:
        await handler(update, context)
        return

    # ادمین می‌تواند مستقیم سیگنال بفرستد بدون وارد شدن به conversation
    if admin:
        signal = parse_manual_signal(text)
        if signal is not None:
            sent, failed = await publish_signal(context.application, signal)
            await update.message.reply_text(
                f"سیگنال ارسال شد ✅\nموفق: {sent} | ناموفق: {failed}"
            )
            return

    await update.message.reply_text(
        "از دکمه‌های پایین استفاده کنید یا /help را بزنید.",
        reply_markup=main_menu(admin),
    )


async def publish_signal(app: Application, signal: Signal) -> tuple[int, int]:
    db: Database = app.bot_data["db"]
    db.save_signal(
        symbol=signal.symbol,
        side=signal.side,
        entry=signal.entry,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        timeframe=signal.timeframe,
        note=signal.note,
        source=signal.source,
    )
    message = signal.format_message()
    return await broadcast_text(app, message, parse_mode=ParseMode.MARKDOWN_V2)


async def broadcast_text(
    app: Application,
    text: str,
    parse_mode: str | None = None,
) -> tuple[int, int]:
    db: Database = app.bot_data["db"]
    subscribers = db.list_subscribers()
    sent = 0
    failed = 0
    for user_id in subscribers:
        try:
            kwargs: dict[str, Any] = {"chat_id": user_id, "text": text}
            if parse_mode:
                kwargs["parse_mode"] = parse_mode
            await app.bot.send_message(**kwargs)
            sent += 1
        except Forbidden:
            db.mark_blocked(user_id)
            failed += 1
        except TelegramError as exc:
            logger.warning("send failed to %s: %s", user_id, exc)
            failed += 1
    return sent, failed


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("admin", admin_panel))

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback, pattern=r"^admin:")],
        states={
            WAIT_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast)
            ],
            WAIT_SIGNAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_signal)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
