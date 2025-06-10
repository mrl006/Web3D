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
# Commands
# ---------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I'm Web3D Tag Member Bot.\nUse #admin or #all in your group to tag people.\nType /promo to get project links."
    )

async def track_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.from_user:
        return
    chat_id = str(message.chat.id)
    user_id = str(message.from_user.id)
    name = message.from_user.first_name
    username = message.from_user.username or ""

    # Save user
    data = load_users()
    if chat_id not in data:
        data[chat_id] = {}
    data[chat_id][user_id] = {"name": name, "username": username}
    save_users(data)

    # Save group
    save_group(chat_id)

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        chat_id = member.chat.id
        user = member.new_chat_member.user
        save_group(chat_id)
        data = load_users()
        if str(chat_id) not in data:
            data[str(chat_id)] = {}
        data[str(chat_id)][str(user.id)] = {
            "name": user.first_name,
            "username": user.username or ""
        }
        save_users(data)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👋 Welcome {user.first_name} to Web3D!\nVisit https://web3decision.com to explore."
        )

async def register_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        if user_id not in [admin.user.id for admin in admins]:
            return await update.message.reply_text("❌ You must be admin to use this.")

        members = await context.bot.get_chat_members_count(chat_id)
        await update.message.reply_text(f"Bot will register active members after they message. Cannot fetch full list via API.")
    except:
        await update.message.reply_text("⚠️ Bot needs admin rights to scan members.")

async def mention_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

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
        mention_list = []
        if chat_id in data:
            for uid, info in data[chat_id].items():
                name = info.get("name", "User")
                username = info.get("username")
                if username:
                    mention_list.append(f"@{username}")
                else:
                    mention_list.append(f"[{name}](tg://user?id={uid})")
        if mention_list:
            await send_in_batches(mention_list, message)
        else:
            await message.reply_text("No users to tag yet.")

async def send_in_batches(mentions, message):
    for i in range(0, len(mentions), 10):
        batch = mentions[i:i+10]
        await message.reply_text(" ".join(batch), parse_mode=ParseMode.MARKDOWN)

async def promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Visit Website", url="https://web3decision.com")],
        [InlineKeyboardButton("DM Admin", url="https://t.me/youradmin")]
    ]
    await update.message.reply_text("🔥 Check out Web3D now!", reply_markup=InlineKeyboardMarkup(keyboard))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    data = load_users()
    total = len(data.get(chat_id, {}))
    await update.message.reply_text(f"📊 Total tracked users: {total}")

# ---------------------------
# App Setup
# ---------------------------
app = ApplicationBuilder().token(BOT_TOKEN).build()
print("✅ Bot is running...")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("promo", promo))
app.add_handler(CommandHandler("botstats", stats))
app.add_handler(CommandHandler("registerall", register_all))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track_users))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), mention_handler))
app.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))

app.run_polling()
