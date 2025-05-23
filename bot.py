import os
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters import CommandStart

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN", "8047284110:AAGLIH-VVWRcTlwimcTQy0zimkiiBKY3vxo")
ADMIN_ID = 6644712689
WALLET_ADDRESS = "0xcD3FcEf99251771a3dc1F6Aa992ff23f1824a1bB"

# Setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# DB
conn = sqlite3.connect("bot.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, referrer INTEGER)")
c.execute("CREATE TABLE IF NOT EXISTS deposits (id INTEGER PRIMARY KEY, user_id INTEGER, tx TEXT, amount REAL, status TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY, user_id INTEGER, address TEXT, amount REAL, status TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS support (id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, reply TEXT)")
conn.commit()

# Keyboards
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Deposit", callback_data="deposit"),
        InlineKeyboardButton("Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("Balance", callback_data="balance"),
        InlineKeyboardButton("Referral", callback_data="referral"),
        InlineKeyboardButton("Support", callback_data="support")
    )
    return kb

def admin_panel(deposit_id=None, withdraw_id=None, user_id=None):
    kb = InlineKeyboardMarkup()
    if deposit_id:
        kb.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_dep_{deposit_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_dep_{deposit_id}")
        )
    if withdraw_id:
        kb.add(
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_wd_{withdraw_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_wd_{withdraw_id}")
        )
    if user_id:
        kb.add(InlineKeyboardButton("✉️ Reply", callback_data=f"reply_{user_id}"))
    return kb

# Helpers
def get_balance(user_id):
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE user_id=? AND status='approved'", (user_id,))
    deposits = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(amount), 0) FROM withdrawals WHERE user_id=? AND status='approved'", (user_id,))
    withdrawals = c.fetchone()[0]
    return round(deposits - withdrawals, 2)

# Handlers
@dp.message_handler(CommandStart())
async def start(message: types.Message):
    ref = message.get_args()
    user_id = message.from_user.id
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, referrer) VALUES (?, ?)", (user_id, int(ref) if ref.isdigit() else None))
        conn.commit()
        if ref.isdigit():
            await bot.send_message(int(ref), f"User {user_id} joined via your referral link.")
    await message.answer("Welcome to USDT Mining Bot!", reply_markup=main_menu())

@dp.callback_query_handler(lambda c: True)
async def menu_callback(call: types.CallbackQuery):
    data = call.data
    user_id = call.from_user.id

    if data == "deposit":
        await call.message.answer(f"Send USDT to this address:\n{WALLET_ADDRESS}\nSend TXID and amount like:\n`TXID amount`")
    elif data == "withdraw":
        await call.message.answer("Send your address and amount like:\n`0xAddress amount`")
    elif data == "balance":
        balance = get_balance(user_id)
        await call.message.answer(f"Your current balance: {balance} USDT")
    elif data == "referral":
        await call.message.answer(f"Your referral link:\nhttps://t.me/YourBotUsername?start={user_id}")
    elif data == "support":
        await call.message.answer("Send your support message and the admin will reply.")

# Deposit Handler
@dp.message_handler(lambda m: len(m.text.split()) == 2 and m.text.split()[0].isalnum())
async def deposit_handler(message: types.Message):
    user_id = message.from_user.id
    tx, amount = message.text.split()
    try:
        amount = float(amount)
        c.execute("INSERT INTO deposits (user_id, tx, amount, status) VALUES (?, ?, ?, 'pending')", (user_id, tx, amount))
        conn.commit()
        dep_id = c.lastrowid
        await bot.send_message(ADMIN_ID, f"New deposit request:\nFrom: {user_id}\nTX: {tx}\nAmount: {amount}", reply_markup=admin_panel(deposit_id=dep_id))
        await message.answer("Deposit submitted for review.")
    except:
        await message.answer("Invalid format. Please send like:\n`TXID amount`")

# Withdraw Handler
@dp.message_handler(lambda m: m.text.startswith("0x") and len(m.text.split()) == 2)
async def withdraw_handler(message: types.Message):
    user_id = message.from_user.id
    address, amount = message.text.split()
    try:
        amount = float(amount)
        if get_balance(user_id) >= amount:
            c.execute("INSERT INTO withdrawals (user_id, address, amount, status) VALUES (?, ?, ?, 'pending')", (user_id, address, amount))
            conn.commit()
            wd_id = c.lastrowid
            await bot.send_message(ADMIN_ID, f"Withdraw request:\nUser: {user_id}\nAmount: {amount}\nTo: {address}", reply_markup=admin_panel(withdraw_id=wd_id))
            await message.answer("Withdraw request submitted.")
        else:
            await message.answer("Insufficient balance.")
    except:
        await message.answer("Invalid format. Please send like:\n`0xAddress amount`")

# Support
@dp.message_handler(lambda m: m.text and m.from_user.id != ADMIN_ID)
async def user_support(message: types.Message):
    user_id = message.from_user.id
    c.execute("INSERT INTO support (user_id, message, reply) VALUES (?, ?, '')", (user_id, message.text))
    conn.commit()
    await bot.send_message(ADMIN_ID, f"Support msg from {user_id}:\n{message.text}", reply_markup=admin_panel(user_id=user_id))
    await message.answer("Message sent to support.")

@dp.message_handler(lambda m: m.reply_to_message and m.from_user.id == ADMIN_ID)
async def admin_reply(message: types.Message):
    try:
        user_id = int(message.reply_to_message.text.split()[3].strip(":"))
        await bot.send_message(user_id, f"Admin reply:\n{message.text}")
    except:
        await message.answer("Failed to parse user ID.")

# Admin Actions
@dp.callback_query_handler(lambda c: c.data.startswith(("approve_", "reject_", "reply_")))
async def admin_actions(call: types.CallbackQuery):
    action, type_, id_ = call.data.split("_")
    id_ = int(id_)

    if type_ == "dep":
        c.execute("SELECT user_id FROM deposits WHERE id=?", (id_,))
        row = c.fetchone()
        if row:
            user_id = row[0]
            if action == "approve":
                c.execute("UPDATE deposits SET status='approved' WHERE id=?", (id_,))
                await bot.send_message(user_id, "Your deposit has been approved.")
            else:
                c.execute("UPDATE deposits SET status='rejected' WHERE id=?", (id_,))
                await bot.send_message(user_id, "Your deposit has been rejected.")
            conn.commit()

    elif type_ == "wd":
        c.execute("SELECT user_id FROM withdrawals WHERE id=?", (id_,))
        row = c.fetchone()
        if row:
            user_id = row[0]
            if action == "approve":
                c.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (id_,))
                await bot.send_message(user_id, "Your withdrawal has been approved.")
            else:
                c.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (id_,))
                await bot.send_message(user_id, "Your withdrawal has been rejected.")
            conn.commit()

    elif type_ == "reply":
        await call.message.answer(f"Reply to user {id_}:", reply_markup=None)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)