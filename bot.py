import sqlite3
import logging

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

conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, name TEXT, balance REAL DEFAULT 0, referrer INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS referrals (user_id INTEGER, referred_id INTEGER)")
conn.commit()

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
    cursor.execute("INSERT OR IGNORE INTO users (id, username, name) VALUES (?, ?, ?)", (user.id, user.username, user.full_name))
    conn.commit()
    if context.args:
        ref_id = int(context.args[0])
        if ref_id != user.id:
            cursor.execute("SELECT * FROM referrals WHERE user_id = ? AND referred_id = ?", (ref_id, user.id))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO referrals (user_id, referred_id) VALUES (?, ?)", (ref_id, user.id))
                cursor.execute("UPDATE users SET referrer = ? WHERE id = ?", (ref_id, user.id))
                conn.commit()
                await context.bot.send_message(ref_id, f"کاربر {user.full_name} (@{user.username}) با لینک دعوت شما عضو شد.")
    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "menu":
        await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu_keyboard())

    elif query.data == "deposit":
        await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟\nحداقل واریز ۵ دلار است.", reply_markup=back_button())
        return DEPOSIT_AMOUNT

    elif query.data == "withdraw":
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE user_id = ?", (user_id,))
        ref_count = cursor.fetchone()[0]
        if ref_count < 3:
            await query.message.edit_text(f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت:\n{get_referral_link(user_id)}", reply_markup=back_button())
            return ConversationHandler.END
        await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button())
        return WITHDRAW_AMOUNT

    elif query.data == "balance":
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        await query.message.edit_text(f"موجودی شما: {balance} دلار", reply_markup=back_button())

    elif query.data == "referral":
        cursor.execute("SELECT COUNT(*) FROM referrals WHERE user_id = ?", (user_id,))
        ref_count = cursor.fetchone()[0]
        bonus = ref_count * 1.5
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (bonus, user_id))
        conn.commit()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        total = cursor.fetchone()[0]
        await query.message.edit_text(f"لینک دعوت: {get_referral_link(user_id)}\nزیرمجموعه‌ها: {ref_count}\nپاداش کل: {bonus} دلار\nموجودی کل: {total} دلار", reply_markup=back_button())

    elif query.data == "support":
        await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button())
        return SUPPORT_MESSAGE

    elif query.data.startswith("confirm_deposit_"):
        _, _, uid, amount = query.data.split("_")
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (float(amount) * 2, int(uid)))
        conn.commit()
        await context.bot.send_message(int(uid), f"واریز تایید شد. موجودی جدید: {float(amount) * 2} دلار")
        await query.message.delete()

    elif query.data.startswith("reject_deposit_"):
        _, _, uid = query.data.split("_")
        await context.bot.send_message(int(uid), "واریز شما رد شد.")
        await query.message.delete()

    elif query.data.startswith("reply_support_"):
        uid = int(query.data.split("_")[-1])
        context.user_data["reply_to"] = uid
        await query.message.reply_text("لطفاً متن پاسخ را وارد کنید:")
        return ADMIN_REPLY

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار است.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text("لطفاً مبلغ را به آدرس زیر واریز کرده و اسکرین‌شات یا لینک تراکنش را ارسال نمایید:\n\n`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`", reply_markup=back_button("deposit"), parse_mode="Markdown")
        return DEPOSIT_PROOF
    except:
        await update.message.reply_text("مقدار وارد شده معتبر نیست.", reply_markup=back_button("deposit"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("deposit_amount", 0)
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [[
        InlineKeyboardButton("تایید", callback_data=f"confirm_deposit_{user.id}_{amount}"),
        InlineKeyboardButton("رد", callback_data=f"reject_deposit_{user.id}")
    ]]
    await context.bot.send_message(ADMIN_ID, f"درخواست واریز از {user.full_name} (@{user.username})\nمقدار: {amount}\nمدرک:\n{proof}", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("در حال بررسی توسط ادمین.")
    return ConversationHandler.END

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        if amount > balance:
            await update.message.reply_text("مقدار درخواستی بیشتر از موجودی شماست.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("لطفاً آدرس کیف پول خود را وارد کنید (BEP20):", reply_markup=back_button("withdraw"))
        return WALLET_ADDRESS
    except:
        await update.message.reply_text("مقدار وارد شده معتبر نیست.", reply_markup=back_button("withdraw"))
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [[
        InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw_{user.id}_{amount}_{address}"),
        InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user.id}")
    ]]
    await context.bot.send_message(ADMIN_ID, f"درخواست برداشت از {user.full_name} (@{user.username})\nمقدار: {amount}\nآدرس: {address}", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("درخواست برداشت شما ارسال شد.")
    return ConversationHandler.END

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message.text
    await context.bot.send_message(ADMIN_ID, f"پیغام پشتیبانی از {user.full_name} (@{user.username}):\n{msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ", callback_data=f"reply_support_{user.id}")]]))
    await update.message.reply_text("پیغام شما ارسال شد.")
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = context.user_data.get("reply_to")
    msg = update.message.text
    if uid:
        await context.bot.send_message(uid, f"پاسخ ادمین:\n{msg}")
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
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
