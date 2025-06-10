
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    ChatMemberHandler,
    filters
)

BOT_TOKEN = "8077295783:AAEDLMX9I_FqBV_yKPtfrAiB7xEHuuzdLks"
USER_DB = "active_users.json"

def load_users():
    if not os.path.exists(USER_DB):
        return {}
    with open(USER_DB, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USER_DB, "w") as f:
        json.dump(data, f)

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    name = message.from_user.first_name

    data = load_users()
    if chat_id not in data:
        data[chat_id] = {}
    data[chat_id][user_id] = name
    save_users(data)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        chat_id = member.chat.id
        user = member.new_chat_member.user
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👋 Welcome {user.first_name} to Web3D!\nVisit https://web3decision.com to explore.",
        )

async def mention_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = str(message.chat.id)
    text = message.text.lower()
    data = load_users()

    if "#admin" in text:
        admins = await context.bot.get_chat_administrators(chat_id)
        mention_list = [
            f"[{admin.user.first_name}](tg://user?id={admin.user.id})"
            for admin in admins if not admin.user.is_bot
        ]
        await send_in_batches(mention_list, message)

    elif "#all" in text:
        if chat_id in data:
            mention_list = [
                f"[{name}](tg://user?id={uid})" for uid, name in data[chat_id].items()
            ]
            await send_in_batches(mention_list, message)
        else:
            await message.reply_text("No active users to tag yet.")

async def send_in_batches(mentions, message):
    for i in range(0, len(mentions), 10):
        batch = mentions[i:i+10]
        await message.reply_text(" ".join(batch), parse_mode=ParseMode.MARKDOWN)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    user_id = update.message.from_user.id
    chat_admins = await context.bot.get_chat_administrators(chat_id)
    admin_ids = [admin.user.id for admin in chat_admins]

    if user_id not in admin_ids:
        await update.message.reply_text("🚫 Only admins can use this command.")
        return

    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return

    data = load_users()
    if chat_id in data:
        mention_list = [
            f"[{name}](tg://user?id={uid})" for uid, name in data[chat_id].items()
        ]
        for i in range(0, len(mention_list), 10):
            batch = mention_list[i:i+10]
            full_msg = f"{message_text}\n\n{' '.join(batch)}"
            await update.message.reply_text(full_msg, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("No users available to broadcast.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    data = load_users()
    total = len(data.get(chat_id, {}))
    await update.message.reply_text(f"📊 Total tracked users: {total}")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Visit Website", url="https://web3decision.com")],
        [InlineKeyboardButton("DM Admin", url="https://t.me/youradmin")]
    ]
    await update.message.reply_text("🔥 Check out Web3D now!", reply_markup=InlineKeyboardMarkup(keyboard))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track_users))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mention_handler))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("botstats", stats))
app.add_handler(CommandHandler("promo", promo))
app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

app.run_polling()
