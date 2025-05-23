import logging from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes )

--- تنظیمات اولیه ---

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo" ADMIN_ID = 6644712689  # آی‌دی عددی ادمین را اینجا وارد کنید

--- وضعیت‌ها ---

(DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WITHDRAW_WALLET, SUPPORT_MESSAGE, ADMIN_REPLY) = range(6)

--- دیتابیس ساده ---

user_balances = {} user_requests = {} user_referrals = {} admin_reply_targets = {}

--- توابع کمکی ---

def get_total_balance(user_id): main_balance = user_balances.get(user_id, 0) referrals = user_referrals.get(user_id, []) return main_balance + len(referrals) * 1.5

--- /start ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id if context.args: referrer_id = int(context.args[0]) if referrer_id != user_id: referrals = user_referrals.setdefault(referrer_id, []) if user_id not in referrals: referrals.append(user_id)

keyboard = [
    [InlineKeyboardButton("Deposit", callback_data="deposit")],
    [InlineKeyboardButton("Withdrawal", callback_data="withdraw")],
    [InlineKeyboardButton("Balance", callback_data="balance")],
    [InlineKeyboardButton("Referral", callback_data="referral")],
    [InlineKeyboardButton("Support", callback_data="support")],
]
await update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

--- منو ---

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query if query.data == "deposit": await query.message.reply_text("چه مقدار دلار یا تتر می‌خواهید شارژ کنید؟ (حداقل ۵ دلار)") return DEPOSIT_AMOUNT elif query.data == "withdraw": return await handle_withdrawal(update, context) elif query.data == "balance": user_id = query.from_user.id balance = get_total_balance(user_id) await query.message.reply_text(f"موجودی کل شما: {balance} دلار") elif query.data == "referral": return await handle_referral(update, context) elif query.data == "support": return await handle_support(update, context) return ConversationHandler.END

--- Deposit ---

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): try: amount = float(update.message.text) if amount < 5: await update.message.reply_text("حداقل مبلغ واریز ۵ دلار است.") return ConversationHandler.END context.user_data['deposit_amount'] = amount await update.message.reply_text( "آدرس کیف پول تتر (BEP20):\n" "0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB\n" "لطفاً لینک یا اسکرین شات تراکنش را ارسال کنید." ) return DEPOSIT_PROOF except ValueError: await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.") return DEPOSIT_AMOUNT

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id amount = context.user_data['deposit_amount']

keyboard = [
    [InlineKeyboardButton("تأیید", callback_data=f"confirm_deposit_{user_id}_{amount}"),
     InlineKeyboardButton("رد", callback_data=f"reject_deposit_{user_id}")]
]

await context.bot.send_message(
    chat_id=ADMIN_ID,
    text=f"درخواست واریز {amount}$ از {user_id}",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
await update.message.reply_text("درخواست شما ارسال شد و در حال بررسی است.")
return ConversationHandler.END

async def handle_admin_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() if "confirm_deposit" in query.data: , user_id, amount = query.data.split("") user_id, amount = int(user_id), float(amount) user_balances[user_id] = user_balances.get(user_id, 0) + amount * 2 await context.bot.send_message(user_id, f"تراکنش شما تایید شد. موجودی شما {amount * 2}$ می‌باشد.") await query.edit_message_text("واریز تایید شد.") elif "reject_deposit" in query.data: , user_id = query.data.split("") await context.bot.send_message(int(user_id), "تراکنش شما رد شد.") await query.edit_message_text("واریز رد شد.")

--- Withdrawal ---

async def handle_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = query.from_user.id if len(user_referrals.get(user_id, [])) < 3: link = f"https://t.me/TetherMinerDouble_Bot?start={user_id}" await query.message.reply_text( f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت شما:\n{link}" ) return ConversationHandler.END await query.message.reply_text("چه مقدار می‌خواهید برداشت کنید؟") return WITHDRAW_AMOUNT

async def receive_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id try: amount = float(update.message.text) if amount > get_total_balance(user_id): await update.message.reply_text("مقدار درخواستی بیشتر از موجودی شما می‌باشد.") return ConversationHandler.END context.user_data['withdraw_amount'] = amount await update.message.reply_text("آدرس کیف پول خود را وارد کنید:") return WITHDRAW_WALLET except: await update.message.reply_text("لطفاً عدد معتبر وارد کنید.") return WITHDRAW_AMOUNT

async def receive_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id amount = context.user_data['withdraw_amount'] wallet = update.message.text user_requests[user_id] = {'amount': amount, 'wallet': wallet}

keyboard = [
    [InlineKeyboardButton("تأیید", callback_data=f"confirm_withdraw_{user_id}"),
     InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user_id}")]
]

await context.bot.send_message(
    chat_id=ADMIN_ID,
    text=f"درخواست برداشت {amount}$ از {user_id}\nآدرس: {wallet}",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
await update.message.reply_text("درخواست شما ارسال شد.")
return ConversationHandler.END

async def handle_admin_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user_id = int(query.data.split("_")[-1])

if "confirm_withdraw" in query.data:
    amount = user_requests[user_id]['amount']
    user_balances[user_id] -= amount
    await context.bot.send_message(user_id, "درخواست شما تایید شد. مبلغ بزودی ارسال خواهد شد.")
    await query.edit_message_text("برداشت تایید شد.")
elif "reject_withdraw" in query.data:
    await context.bot.send_message(user_id, "درخواست شما رد شد. جهت اطلاعات بیشتر با ادمین تماس بگیرید.")
    await query.edit_message_text("برداشت رد شد.")
user_requests.pop(user_id, None)

--- Referral ---

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query user_id = query.from_user.id count = len(user_referrals.get(user_id, [])) total_balance = get_total_balance(user_id) link = f"https://t.me/TetherMinerDouble_Bot?start={user_id}" await query.message.reply_text( f"لینک دعوت شما:\n{link}\nزیرمجموعه‌ها: {count}\n" f"پاداش: ۱.۵ دلار برای هر نفر\nموجودی کل: {total_balance} دلار" ) return ConversationHandler.END

--- Support ---

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.message.reply_text("پیام خود را برای پشتیبانی ارسال کنید:") return SUPPORT_MESSAGE

async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.message.from_user keyboard = [[InlineKeyboardButton("پاسخ", callback_data=f"reply_to_{user.id}")]] await context.bot.send_message( chat_id=ADMIN_ID, text=f"پیام از {user.first_name} ({user.id}):\n{update.message.text}", reply_markup=InlineKeyboardMarkup(keyboard) ) await update.message.reply_text("پیام شما ارسال شد.") return ConversationHandler.END

async def handle_admin_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query target_user_id = int(query.data.split("_")[-1]) admin_reply_targets[query.from_user.id] = target_user_id await query.message.reply_text("متن پاسخ را وارد کنید:") return ADMIN_REPLY

async def receive_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE): admin_id = update.message.from_user.id user_id = admin_reply_targets.pop(admin_id, None) if user_id: await context.bot.send_message(user_id, f"پاسخ پشتیبانی:\n{update.message.text}") await update.message.reply_text("پاسخ شما ارسال شد.") return ConversationHandler.END

--- راه‌اندازی ---

if name == 'main': logging.basicConfig(level=logging.INFO) app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(menu_handler)],
    states={
        DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT, receive_amount)],
        DEPOSIT_PROOF: [MessageHandler(filters.ALL, receive_proof)],
        WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT, receive_withdraw_amount)],
        WITHDRAW_WALLET: [MessageHandler(filters.TEXT, receive_wallet_address)],
        SUPPORT_MESSAGE: [MessageHandler(filters.TEXT, receive_support_message)],
        ADMIN_REPLY: [MessageHandler(filters.TEXT, receive_admin_reply)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(handle_admin_deposit, pattern="confirm_deposit|reject_deposit"))
app.add_handler(CallbackQueryHandler(handle_admin_withdraw, pattern="confirm_withdraw|reject_withdraw"))
app.add_handler(CallbackQueryHandler(handle_admin_reply_button, pattern="reply_to_"))

app.run_polling()

