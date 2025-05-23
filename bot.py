import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# --- تنظیمات ---
TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

# --- لاگ ---
logging.basicConfig(level=logging.INFO)

# --- وضعیت‌ها ---
(DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS,
 SUPPORT_MESSAGE, ADMIN_REPLY) = range(6)

# --- دیتابیس ---
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    referred_by INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    user_id INTEGER,
    referred_user_id INTEGER
)
""")
conn.commit()

# --- منوها ---
def get_referral_link(user_id):
    return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Deposit", callback_data="deposit"),
         InlineKeyboardButton("Withdrawal", callback_data="withdraw"),
         InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Referral", callback_data="referral"),
         InlineKeyboardButton("Support", callback_data="support")]
    ])

def back_button(callback_data="menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=callback_data)]])

# --- شروع ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user.id,))
    conn.commit()

    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                cursor.execute("SELECT * FROM referrals WHERE user_id=? AND referred_user_id=?", (referrer_id, user.id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO referrals (user_id, referred_user_id) VALUES (?, ?)", (referrer_id, user.id))
                    cursor.execute("UPDATE users SET referred_by=? WHERE id=? AND referred_by IS NULL", (referrer_id, user.id))
                    await context.bot.send_message(referrer_id, f"کاربر {user.full_name} با لینک شما عضو شد.")
                    conn.commit()
        except:
            pass

    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu_keyboard())

# --- دکمه‌ها ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match query.data:
        case "menu":
            await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu_keyboard())

        case "deposit":
            await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟ (حداقل ۵ دلار)", reply_markup=back_button("menu"))
            return DEPOSIT_AMOUNT

        case "withdraw":
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE user_id=?", (user_id,))
            if cursor.fetchone()[0] < 3:
                link = get_referral_link(user_id)
                await query.message.edit_text(f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت: {link}", reply_markup=back_button())
                return ConversationHandler.END
            await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button("menu"))
            return WITHDRAW_AMOUNT

        case "balance":
            cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
            balance = cursor.fetchone()[0]
            await query.message.edit_text(f"موجودی شما: {balance:.2f} دلار", reply_markup=back_button())

        case "referral":
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE user_id=?", (user_id,))
            count = cursor.fetchone()[0]
            bonus = count * 1.5
            cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (bonus, user_id))
            conn.commit()
            cursor.execute("SELECT balance FROM users WHERE id=?", (user_id,))
            total = cursor.fetchone()[0]
            await query.message.edit_text(
                f"زیرمجموعه‌ها: {count}\nپاداش: {bonus:.2f} دلار\nموجودی کل: {total:.2f} دلار\n"
                f"لینک دعوت: {get_referral_link(user_id)}",
                reply_markup=back_button()
            )

        case "support":
            await query.message.edit_text("پیام خود را وارد کنید:", reply_markup=back_button("menu"))
            return SUPPORT_MESSAGE

# --- واریز ---
async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار است.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            "آدرس واریز:\n`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`\nاسکرین‌شات یا TXID را ارسال کنید.",
            reply_markup=back_button("menu"), parse_mode="Markdown"
        )
        return DEPOSIT_PROOF
    except ValueError:
        await update.message.reply_text("عدد نامعتبر است.", reply_markup=back_button("menu"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data.get("deposit_amount")
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [
        [InlineKeyboardButton("تأیید", callback_data=f"approve_{user_id}_{amount}"),
         InlineKeyboardButton("رد", callback_data=f"reject_{user_id}")]
    ]
    await context.bot.send_message(ADMIN_ID,
        f"درخواست واریز\nکاربر: {user_id}\nمقدار: {amount}\nمدرک:\n{proof}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("در حال بررسی توسط ادمین.")
    return ConversationHandler.END

# --- برداشت ---
async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("آدرس کیف پول خود را وارد کنید:", reply_markup=back_button("menu"))
        return WALLET_ADDRESS
    except ValueError:
        await update.message.reply_text("عدد نامعتبر.", reply_markup=back_button("menu"))
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [
        [InlineKeyboardButton("تأیید", callback_data=f"approve_withdraw_{user_id}_{amount}_{address}"),
         InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user_id}")]
    ]
    await context.bot.send_message(ADMIN_ID,
        f"درخواست برداشت\nکاربر: {user_id}\nمقدار: {amount}\nآدرس: {address}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما ارسال شد.")
    return ConversationHandler.END

# --- ادمین: تأیید/رد ---
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split("_")
    user_id, amount = int(data[1]), float(data[2])
    cursor.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount * 2, user_id))
    conn.commit()
    await context.bot.send_message(user_id, f"واریز تأیید شد. موجودی فعلی: {amount * 2:.2f} دلار")
    await update.callback_query.message.delete()

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = int(update.callback_query.data.split("_")[1])
    await context.bot.send_message(user_id, "واریز شما رد شد.")
    await update.callback_query.message.delete()

async def approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _, _, user_id, amount, *_ = update.callback_query.data.split("_")
    user_id, amount = int(user_id), float(amount)
    cursor.execute("UPDATE users SET balance = balance - ? WHERE id=?", (amount, user_id))
    conn.commit()
    await context.bot.send_message(user_id, "برداشت شما تأیید شد.")
    await update.callback_query.message.delete()

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = int(update.callback_query.data.split("_")[2])
    await context.bot.send_message(user_id, "برداشت شما رد شد.")
    await update.callback_query.message.delete()

# --- پشتیبانی ---
async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    context.user_data["support_reply_to"] = user_id
    await context.bot.send_message(ADMIN_ID, f"پیام از {user_id}:\n{msg}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("پاسخ", callback_data=f"reply_{user_id}")]]))
    await update.message.reply_text("پیام شما ارسال شد.")
    return ConversationHandler.END

async def reply_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = int(update.callback_query.data.split("_")[1])
    context.user_data["reply_to"] = user_id
    await update.callback_query.message.reply_text("پاسخ خود را وارد کنید:")
    return ADMIN_REPLY

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get("reply_to")
    if user_id:
        await context.bot.send_message(user_id, f"پاسخ ادمین:\n{update.message.text}")
        await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

# --- اجرای ربات ---
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
    app.add_handler(CallbackQueryHandler(approve, pattern=r"^approve_"))
    app.add_handler(CallbackQueryHandler(reject, pattern=r"^reject_"))
    app.add_handler(CallbackQueryHandler(approve_withdraw, pattern=r"^approve_withdraw_"))
    app.add_handler(CallbackQueryHandler(reject_withdraw, pattern=r"^reject_withdraw_"))
    app.add_handler(CallbackQueryHandler(reply_to_support, pattern=r"^reply_"))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == "__main__":
    main()
