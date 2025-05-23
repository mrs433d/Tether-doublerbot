import sqlite3
import threading
import time
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Update
from telegram.ext import Application
from telegram.ext import CallbackContext
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import MessageHandler
from telegram.ext import filters

TOKEN = '8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo'
ADMIN_ID = 6644712689  # آیدی عددی ادمین

conn = sqlite3.connect("bot.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users 
             (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, referrer_id INTEGER)''')

c.execute('''CREATE TABLE IF NOT EXISTS deposits 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS support 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT)''')

conn.commit()

def add_user(user_id, username, referrer_id=None):
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        conn.commit()
        if referrer_id:
            ref_user = c.execute("SELECT username FROM users WHERE user_id = ?", (referrer_id,)).fetchone()
            if ref_user:
                app.bot.send_message(chat_id=referrer_id, text=f"{username or user_id} از طریق لینک شما عضو شد.")

def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username
    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except:
            pass

    add_user(user_id, username, referrer_id)

    keyboard = [
        [InlineKeyboardButton("واریز", callback_data="deposit")],
        [InlineKeyboardButton("برداشت", callback_data="withdraw")],
        [InlineKeyboardButton("موجودی", callback_data="balance")],
        [InlineKeyboardButton("زیرمجموعه‌گیری", callback_data="referral")],
        [InlineKeyboardButton("پشتیبانی", callback_data="support")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("به ربات خوش آمدید.", reply_markup=reply_markup)

async def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "deposit":
        context.user_data["action"] = "deposit"
        await query.message.reply_text("لطفاً مبلغ مورد نظر را وارد کنید:")
    elif query.data == "withdraw":
        context.user_data["action"] = "withdraw"
        await query.message.reply_text("لطفاً آدرس کیف پول و مبلغ برداشت را وارد کنید:")
    elif query.data == "balance":
        balance = get_balance(user_id)
        await query.message.reply_text(f"موجودی شما: {balance}")
    elif query.data == "referral":
        await query.message.reply_text(f"لینک دعوت شما:\nhttps://t.me/YourBotUsername?start={user_id}")
    elif query.data == "support":
        context.user_data["action"] = "support"
        await query.message.reply_text("پیام خود را برای پشتیبانی ارسال کنید:")

def double_deposit_later(user_id, amount):
    time.sleep(600)
    update_balance(user_id, amount)

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text

    if context.user_data.get("action") == "deposit":
        try:
            amount = int(text)
            c.execute("INSERT INTO deposits (user_id, amount, status) VALUES (?, ?, ?)", (user_id, amount, "pending"))
            conn.commit()
            await update.message.reply_text("درخواست واریز ثبت شد.")
            app.bot.send_message(chat_id=ADMIN_ID, text=f"واریز جدید از {username or user_id} به مبلغ {amount}")
            threading.Thread(target=double_deposit_later, args=(user_id, amount)).start()
        except:
            await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
    elif context.user_data.get("action") == "withdraw":
        await update.message.reply_text("درخواست برداشت شما ثبت شد و ظرف ۶۰ دقیقه پردازش می‌شود.")
    elif context.user_data.get("action") == "support":
        c.execute("INSERT INTO support (user_id, message) VALUES (?, ?)", (user_id, text))
        conn.commit()
        app.bot.send_message(chat_id=ADMIN_ID, text=f"پیام پشتیبانی از {username or user_id}:\n{text}")
        await update.message.reply_text("پیام شما به پشتیبانی ارسال شد.")
    elif user_id == ADMIN_ID and update.message.reply_to_message:
        target_text = update.message.reply_to_message.text
        if "پیام پشتیبانی از" in target_text:
            lines = target_text.split("\n")
            line = lines[0]
            uid = None
            if "(" in line:
                uid = int(line.split("(")[-1].strip("):"))
            else:
                uid = int(line.split()[-1])
            if uid:
                await context.bot.send_message(chat_id=uid, text=update.message.text)
    else:
        await update.message.reply_text("از دکمه‌های منو استفاده کنید.")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
