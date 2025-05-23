from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID
import db

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Deposit", callback_data="deposit")],
        [InlineKeyboardButton("Withdrawal", callback_data="withdrawal")],
        [InlineKeyboardButton("Balance", callback_data="balance")],
        [InlineKeyboardButton("Invite Friends", callback_data="invite")],
        [InlineKeyboardButton("Support", callback_data="support")]
    ]
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id if query.from_user else None
    if not user_id:
        await query.message.reply_text("خطا: شناسه کاربری پیدا نشد.")
        return

    data = query.data

    if data == "deposit":
        db.set_user_state(user_id, "awaiting_deposit")
        await query.message.reply_text("Please enter deposit amount (min $5):")
    elif data == "withdrawal":
        db.set_user_state(user_id, "awaiting_wallet")
        await query.message.reply_text("Please send your wallet address:")
    elif data == "balance":
        balance = db.get_balance(user_id)
        await query.message.reply_text(f"Your current balance is ${balance:.2f}")
    elif data == "invite":
        invite_link = f"https://t.me/YourBotUsername?start={user_id}"
        await query.message.reply_text(f"Invite friends with your link:\n{invite_link}")
    elif data == "support":
        await query.message.reply_text("Send your message to support:")
        db.set_user_state(user_id, "awaiting_support")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        await update.message.reply_text("خطا: کاربر شناسایی نشد.")
        return

    text = update.message.text.strip()
    state = db.get_user_state(user.id)

    if state == "awaiting_deposit":
        try:
            amount = float(text)
            if amount >= 5:
                db.add_balance(user.id, amount * 2)
                await update.message.reply_text(f"You deposited ${amount:.2f}. Your new balance is ${amount*2:.2f}")
            else:
                await update.message.reply_text("Minimum deposit is $5.")
        except:
            await update.message.reply_text("Invalid amount. Please send a number.")
        db.set_user_state(user.id, None)

    elif state == "awaiting_wallet":
        await update.message.reply_text("Your withdrawal request has been received. Funds will be sent soon.")
        db.set_user_state(user.id, None)

    elif state == "awaiting_support":
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Support message from {user.id}: {text}")
        await update.message.reply_text("Your message has been sent to support.")
        db.set_user_state(user.id, None)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
