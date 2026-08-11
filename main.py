import os
import logging
import asyncio
from threading import Thread
import urllib.request
import re
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- FLASK KEEP-ALIVE SERVER -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Live 24/7!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

# Render Sleep ആകാതിരിക്കാൻ 3 മിനിറ്റ് കൂടുമ്പോൾ സ്വന്തം സർവറിലേക്ക് റിക്വസ്റ്റ് അയക്കുന്ന ഫങ്ഷൻ
async def self_ping():
    await asyncio.sleep(10)
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not render_url:
        logging.warning("⚠️ RENDER_EXTERNAL_URL കണ്ടുപിടിച്ചില്ല!")
        return

    while True:
        try:
            url = f"{render_url.rstrip('/')}/health"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
            logging.info("✅ Self ping successful!")
        except Exception as e:
            logging.error(f"❌ Self ping failed: {e}")
        
        await asyncio.sleep(180)
# -----------------------------------------------------------

async def delete_photo_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Failed to delete message: {e}")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
INFO_ONLY_GROUP_ID = -1004376973168
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

connected_groups = {INFO_ONLY_GROUP_ID, DEFAULT_GROUP_ID}
muted_users = set()
user_last_thanks_msg = {}

# --- Helper: Mute/Unmute നോട്ടിഫിക്കേഷൻ അയക്കാൻ ---
async def notify_all_groups(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_name: str, action: str):
    mention = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    message = f"🔇 User {mention} has been MUTED by Admin." if action == "mute" else f"🔊 User {mention} has been UNMUTED by Admin."
    
    for group_id in list(connected_groups):
        try:
            await context.bot.send_message(chat_id=group_id, text=message, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Could not notify group {group_id}: {e}")

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക.")

# /id Command
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(f"📌 Chat ID: <code>{chat_id}</code>\n👤 Your ID: <code>{user_id}</code>", parse_mode="HTML")

# /mute command
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_to_mute = None
    user_name = "User"

    # 1. Reply/Mention വഴി
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        user_to_mute = target.id
        user_name = target.full_name
    elif context.args:
        try:
            user_to_mute = int(context.args[0])
            user_name = str(user_to_mute)
        except:
            await update.message.reply_text("⚠️ Invalid ID.")
            return

    if user_to_mute:
        muted_users.add(user_to_mute)
        await notify_all_groups(context, user_to_mute, user_name, "mute")
        await update.message.reply_text(f"🔇 User <code>{user_to_mute}</code> വിജയകരമായി മ്യൂട്ട് ചെയ്തു!", parse_mode="HTML")

# /unmute command
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_to_unmute = None
    user_name = "User"

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        user_to_unmute = target.id
        user_name = target.full_name
    elif context.args:
        try:
            user_to_unmute = int(context.args[0])
            user_name = str(user_to_unmute)
        except:
            return

    if user_to_unmute and user_to_unmute in muted_users:
        muted_users.remove(user_to_unmute)
        await notify_all_groups(context, user_to_unmute, user_name, "unmute")
        await update.message.reply_text(f"🔊 User <code>{user_to_unmute}</code> അൺ-മ്യൂട്ട് ചെയ്തിരിക്കുന്നു!", parse_mode="HTML")

# /leave Command
async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        if chat.id in connected_groups: connected_groups.remove(chat.id)
        await context.bot.leave_chat(chat.id)

# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# ഫോട്ടോ ഹാൻഡ്‌ലർ
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in muted_users:
        await update.message.reply_text("🚫 നിങ്ങളെ തടഞ്ഞിരിക്കുന്നു! (Muted).")
        return

    photo = update.message.photo[-1].file_id
    user_caption = update.message.caption or ""
    group_keyboard = [[InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")]]
    group_reply_markup = InlineKeyboardMarkup(group_keyboard)

    sent_success = False
    for group_id in list(connected_groups):
        try:
            if group_id == INFO_ONLY_GROUP_ID:
                user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
                info_text = f"📥 <b>New Photo</b>\n👤 <b>Name:</b> {user_mention}\n💬 <b>Caption:</b> {user_caption}"
                await context.bot.send_message(chat_id=group_id, text=info_text, parse_mode="HTML", reply_markup=group_reply_markup)
            else:
                sent_msg = await context.bot.send_photo(chat_id=group_id, photo=photo, caption=user_caption, reply_markup=group_reply_markup)
                asyncio.create_task(delete_photo_after_delay(context, group_id, sent_msg.message_id, 300))
            sent_success = True
        except: pass

    if sent_success:
        await update.message.reply_text("✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!")

async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in muted_users:
        await update.message.reply_text("🚫 നിങ്ങളെ തടഞ്ഞിരിക്കുന്നു!")
        return
    try:
        warning_msg = await update.message.reply_text("⚠️ ഫോട്ടോകൾ മാത്രം അയക്കുക.")
        await asyncio.sleep(5)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=warning_msg.message_id)
    except: pass

async def post_init(application):
    asyncio.create_task(self_ping())

def main():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("id", get_id))
    bot_app.add_handler(CommandHandler("mute", mute_user))
    bot_app.add_handler(CommandHandler("unmute", unmute_user))
    bot_app.add_handler(CommandHandler("leave", leave_group))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()