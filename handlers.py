from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from config import ADMIN_ID
from db import add_user, update_balance, get_balance
from threading import Timer

main_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("💰 Deposit", callback_data="deposit")],
    [InlineKeyboardButton("💸 Withdrawal", callback_data="withdrawal")],
    [InlineKeyboardButton("📊 Balance", callback_data="balance")],
    [InlineKeyboardButton("👥 Invite Friends", callback_data="invite")],
    [InlineKeyboardButton("🆘 Support", callback_data="support")]
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    invited_by = int(args[0]) if args and args[0].isdigit() and int(args[0]) != user_id else None
    add_user(user_id, invited_by)
    await update.message.reply_text("به ربات خوش آمدید!", reply_markup=main_menu)

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    match query.data:
        case "deposit":
            await query.message.reply_text("مقدار دلاری که واریز کردید رو وارد کنید:")
            context.user_data['awaiting_deposit'] = True
        case "withdrawal":
            await query.message.reply_text("آدرس کیف پول تتر خود را وارد کنید:")
            context.user_data['awaiting_wallet'] = True
        case "balance":
            bal = get_balance(user_id)
            await query.message.reply_text(f"موجودی فعلی شما: {bal:.2f} دلار")
        case "invite":
            bot_username = (await context.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start={user_id}"
            await query.message.reply_text(f"لینک دعوت شما:
{invite_link}

به ازای هر دعوت ۰.۵ دلار پاداش می‌گیرید.")
        case "support":
            await query.message.reply_text("پیام خود را برای پشتیبانی وارد کنید:")
            context.user_data['awaiting_support'] = True

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('awaiting_support'):
        context.user_data['awaiting_support'] = False
        await context.bot.send_message(ADMIN_ID, f"پیام از {user_id}:
{text}")
        await update.message.reply_text("پیام شما برای پشتیبانی ارسال شد.")
        return

    if context.user_data.get('awaiting_wallet'):
        context.user_data['awaiting_wallet'] = False
        await update.message.reply_text(f"درخواست برداشت ثبت شد. مبلغ به کیف پول {text} ارسال خواهد شد.")
        return

    if context.user_data.get('awaiting_deposit'):
        context.user_data['awaiting_deposit'] = False
        try:
            amount = float(text)
            if amount >= 5:
                await update.message.reply_text("در حال تأیید واریز...")
                Timer(60.0, complete_deposit, args=(context, user_id, amount)).start()
            else:
                await update.message.reply_text("حداقل واریز ۵ دلار است.")
        except ValueError:
            await update.message.reply_text("عدد معتبر وارد کنید.")

def complete_deposit(context, user_id, amount):
    update_balance(user_id, amount * 2)
    context.bot.send_message(user_id, f"{amount} دلار واریز شد و موجودی شما به {amount*2:.2f} دلار افزایش یافت.")
