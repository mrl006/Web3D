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

BOT_TOKEN = "8077295783:AAEDLMX9I_FqBV_yKPtfrAiB7xEHuuzdLks"  # Replace this with your real token
USER_DB = "active_users.json"
GROUP_DB = "groups.json"

# ---------------------------
# Utilities
# ---------------------------
def load_users():
    if not os.path.exists(USER_DB):
        return {}
    with open(USER_DB, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USER_DB, "w") as f:
        json.dump(data, f)

def load_groups():
    if not os.path.exists(GROUP_DB):
        return []
    with open(GROUP_DB, "r") as f:
        return json.load(f)

def save_group(chat_id):
    data = load_groups()
    if chat_id not in data:
        data.append(chat_id)
        with open(GROUP_DB, "w") as f:
            json.dump(data, f)

# ---------------------------
# Commands & Handlers
# ---------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm Web3D Tag Member Bot.\nUse #admin or #all in your group to tag people.\nType /promo to get project links."
    )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        chat_id = member.chat.id
        user = member.new_chat_member.user
        save_group(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👋 Welcome {user.first_name} to Web3D!\nVisit https://web3decision.com to explore."
        )

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user or not message.text:
        return

    # Track user
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    name = message.from_user.first_name

    data = load_users()
    if chat_id not in data:
        data[chat_id] = {}
    data[chat_id][user_id] = name
    save_users(data)
    save_group(chat_id)
    print(f"[LOG] Tracked user {name} ({user_id}) in group {chat_id}")

    # Mention Logic
    text = message.text.lower()
    print(f"[LOG] Received in {chat_id}: {text}")

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

async def gbroadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    groups = load_groups()
    is_admin = False

    for group_id in groups:
        try:
            admins = await context.bot.get_chat_administrators(group_id)
            if any(admin.user.id == user_id for admin in admins):
                is_admin = True
                break
        except:
            continue

    if not is_admin:
        await update.message.reply_text("❌ You must be an admin in at least one group that added me.")
        return

    message_text = update.message.text.replace("/gbroadcast", "").strip()

    if update.message.photo:
        photo = update.message.photo[-1].file_id
        caption = update.message.caption or message_text or "📢"
        for group_id in groups:
            try:
                await context.bot.send_photo(chat_id=group_id, photo=photo, caption=caption)
            except:
                pass
    elif message_text:
        for group_id in groups:
            try:
                await context.bot.send_message(chat_id=group_id, text=message_text)
            except:
                pass
    else:
        await update.message.reply_text("Usage: /gbroadcast Your message or photo")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    data = load_users()
    total = len(data.get(chat_id, {}))
    await update.message.reply_text(f"📊 Total tracked users: {total}")

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Visit Website", url="https://web3decision.com")],
        [InlineKeyboardButton("DM Admin", url="https://t.me/web3decisiontr")]
    ]
    await update.message.reply_text("🔥 Check out Web3D now!", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------------------
# App Setup
# ---------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
print("✅ Bot started... waiting for messages.")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("gbroadcast", gbroadcast))
app.add_handler(CommandHandler("botstats", stats))
app.add_handler(CommandHandler("promo", promo))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_all_messages))
app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

app.run_polling()
