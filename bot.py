import sqlite3
import threading
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = '8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo'
ADMIN_ID = 6644712689  # آیدی عددی ادمین

conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    referral_id INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    timestamp INTEGER
)
''')

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    referral_id = int(context.args[0]) if context.args else None

    cursor.execute("SELECT * FROM users WHERE id = ?", (user.id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (id, username, referral_id) VALUES (?, ?, ?)",
                       (user.id, user.username or "", referral_id))
        conn.commit()
        if referral_id:
            context.bot.send_message(referral_id, f"کاربر @{user.username or user.id} از طریق لینک شما وارد ربات شد.")
    context.bot.send_message(user.id, "به ربات خوش آمدید.")

def deposit(update: Update, context: CallbackContext):
    update.message.reply_text("مبلغ مورد نظر برای شارژ را وارد کنید.")
    context.user_data["action"] = "deposit"

def withdraw(update: Update, context: CallbackContext):
    update.message.reply_text("آدرس کیف پول خود را وارد کنید.")
    context.user_data["action"] = "withdraw"

def support(update: Update, context: CallbackContext):
    update.message.reply_text("پیام خود را بنویسید.")
    context.user_data["action"] = "support"

def message_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    text = update.message.text
    action = context.user_data.get("action")

    if action == "deposit":
        try:
            amount = int(text)
            cursor.execute("INSERT INTO deposits (user_id, amount, timestamp) VALUES (?, ?, ?)",
                           (user.id, amount, int(time.time())))
            conn.commit()
            context.bot.send_message(ADMIN_ID, f"درخواست واریز از @{user.username or user.id} ({user.id})\nمبلغ: {amount}")
            update.message.reply_text("درخواست واریز شما ثبت شد. پس از ۱۰ دقیقه موجودی شما دو برابر خواهد شد.")
            threading.Timer(600, complete_deposit, args=(user.id, amount, context.bot)).start()
        except:
            update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
    elif action == "withdraw":
        context.user_data["action"] = None
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user.id,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            cursor.execute("UPDATE users SET balance = 0 WHERE id = ?", (user.id,))
            conn.commit()
            update.message.reply_text("درخواست برداشت ثبت شد و ظرف ۶۰ دقیقه به آدرس کیف پول شما ارسال خواهد شد.")
        else:
            update.message.reply_text("موجودی کافی ندارید.")
    elif action == "support":
        context.bot.send_message(ADMIN_ID, f"پیام پشتیبانی از @{user.username or user.id} ({user.id}):\n{text}")
        update.message.reply_text("پیام شما به پشتیبانی ارسال شد.")
        context.user_data["action"] = None
    elif str(user.id) == str(ADMIN_ID) and update.message.reply_to_message:
        try:
            ref_id = update.message.reply_to_message.text.split("(")[-1].replace("):", "").strip()
            context.bot.send_message(ref_id, f"پاسخ پشتیبانی:\n{text}")
        except:
            update.message.reply_text("خطا در ارسال پاسخ.")
    else:
        update.message.reply_text("دستور ناشناخته.")

def complete_deposit(user_id, amount, bot: Bot):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount * 2, user_id))
    conn.commit()
    bot.send_message(user_id, f"{amount * 2} به موجودی شما اضافه شد.")

def balance(update: Update, context: CallbackContext):
    cursor.execute("SELECT balance FROM users WHERE id = ?", (update.effective_user.id,))
    result = cursor.fetchone()
    balance = result[0] if result else 0
    update.message.reply_text(f"موجودی شما: {balance}")

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("deposit", deposit))
    dp.add_handler(CommandHandler("withdraw", withdraw))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("support", support))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    updater.start_polling()
    updater.idle()

main()
