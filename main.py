import os
import logging
import asyncio
import json
from threading import Thread
import urllib.request
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    MessageHandler, 
    CommandHandler, 
    ChatMemberHandler, 
    filters
)

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
        logging.warning("⚠️ RENDER_EXTERNAL_URL കണ്ടുപിടിച്ചില്ല! Render Environment Variables-ൽ ഇത് നൽകിയിട്ടുണ്ടെന്ന് ഉറപ്പുവരുത്തുക.")
        return

    while True:
        try:
            url = f"{render_url.rstrip('/')}/health"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
            logging.info("✅ Self ping successful! Server is awake.")
        except Exception as e:
            logging.error(f"❌ Self ping failed: {e}")
        
        await asyncio.sleep(180) # 3 മിനിറ്റിൽ ഒരിക്കൽ പിങ് ചെയ്യും
# -----------------------------------------------------------

# 5 മിനിറ്റിന് ശേഷം ഗ്രൂപ്പിൽ അയച്ച ഫോട്ടോ ഡിലീറ്റ് ചെയ്യുന്ന ഫങ്ഷൻ
async def delete_photo_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logging.info(f"Deleted photo message {message_id} from group {chat_id} after {delay} seconds.")
    except Exception as e:
        logging.error(f"Failed to delete photo message {message_id} in {chat_id}: {e}")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

INFO_ONLY_GROUP_ID = -1004376973168
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

GROUPS_FILE = "connected_groups.json"

# ഗ്രൂപ്പ് ഐഡികൾ ലോഡ് ചെയ്യുന്നു (Env Variables + JSON file)
def load_groups():
    groups = {INFO_ONLY_GROUP_ID, DEFAULT_GROUP_ID}
    
    # Environment variable-ൽ നിന്ന് ഐഡികൾ എടുക്കൽ
    env_groups = os.environ.get("CONNECTED_GROUPS", "")
    if env_groups:
        for gid in env_groups.split(","):
            try:
                groups.add(int(gid.strip()))
            except ValueError:
                pass

    # ഫയലിൽ നിന്ന് ലോഡ് ചെയ്യൽ
    if os.path.exists(GROUPS_FILE):
        try:
            with open(GROUPS_FILE, "r") as f:
                saved_groups = json.load(f)
                groups.update(saved_groups)
        except Exception as e:
            logging.error(f"Error loading groups file: {e}")
    return groups

def save_groups():
    try:
        with open(GROUPS_FILE, "w") as f:
            json.dump(list(connected_groups), f)
    except Exception as e:
        logging.error(f"Error saving groups file: {e}")

connected_groups = load_groups()

muted_users = set()
user_last_thanks_msg = {}

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല.")

# /id Command (ഗ്രൂപ്പിലും പ്രവർത്തിക്കും)
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        connected_groups.add(chat.id)
        save_groups()
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(f"📌 Chat ID: <code>{chat_id}</code>\n👤 Your ID: <code>{user_id}</code>", parse_mode="HTML")

# /mute command
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി User ID നൽകാമോ? (Eg: /mute 12345678)")
        return
    
    try:
        user_to_mute = int(context.args[0])
        muted_users.add(user_to_mute)
        await update.message.reply_text(f"🔇 User <code>{user_to_mute}</code> വിജയകരമായി മ്യൂട്ട് ചെയ്തു (തടഞ്ഞു)!", parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("⚠️ നൽകിയ User ID തെറ്റാണ്.")

# /unmute command
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി User ID നൽകാമോ? (Eg: /unmute 12345678)")
        return
    
    try:
        user_to_unmute = int(context.args[0])
        if user_to_unmute in muted_users:
            muted_users.remove(user_to_unmute)
            await update.message.reply_text(f"🔊 User <code>{user_to_unmute}</code> അൺ-മ്യൂട്ട് ചെയ്തിരിക്കുന്നു!", parse_mode="HTML")
        else:
            await update.message.reply_text("ℹ️ ഈ യൂസർ മ്യൂട്ട് ലിസ്റ്റിൽ ഇല്ല.")
    except ValueError:
        await update.message.reply_text("⚠️ നൽകിയ User ID തെറ്റാണ്.")

# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ (Group & Supergroup ഫിൽട്ടർ)
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        if update.effective_chat.id not in connected_groups:
            connected_groups.add(update.effective_chat.id)
            save_groups()

async def track_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
            if chat.id not in connected_groups:
                connected_groups.add(chat.id)
                save_groups()

# 'halo' എന്ന് അയച്ചാൽ ഗ്രൂപ്പ് ആക്റ്റീവ് ആകുകയും 2 സെക്കൻഡിൽ മെസ്സേജ് ഡിലീറ്റ് ആവുകയും ചെയ്യും
async def activate_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if chat.id not in connected_groups:
            connected_groups.add(chat.id)
            save_groups()
        
        msg = await update.message.reply_text("✅ ബോട്ട് ഈ ഗ്രൂപ്പിൽ ആക്റ്റീവ് ആയി!")
        await asyncio.sleep(2)
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=msg.message_id)
        except Exception as e:
            logging.error(f"Error deleting activation message: {e}")

# ഫോട്ടോ ഹാൻഡ്‌ലർ
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id in muted_users:
        await update.message.reply_text("🚫 നിങ്ങളെ തടഞ്ഞിരിക്കുന്നു! നിങ്ങൾ ഫോട്ടോ ഇട്ടാൽ ഗ്രൂപ്പിലേക്ക് പോകില്ല.")
        return

    photo = update.message.photo[-1].file_id
    user_caption = update.message.caption or ""

    group_keyboard = [
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")],
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ]
    group_reply_markup = InlineKeyboardMarkup(group_keyboard)

    sent_success = False
    for group_id in list(connected_groups):
        try:
            if group_id == INFO_ONLY_GROUP_ID:
                user_mention = f"<a href='tg://user?id={user_id}'>{user.full_name}</a>"
                if user.username:
                    user_mention += f" (@{user.username})"

                info_text = (
                    f"📥 <b>New Photo Submitted</b>\n\n"
                    f"👤 <b>Name:</b> {user_mention}\n"
                    f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
                    f"💬 <b>Caption:</b> {user_caption if user_caption else 'No Caption'}"
                )

                await context.bot.send_message(
                    chat_id=group_id,
                    text=info_text,
                    parse_mode="HTML",
                    reply_markup=group_reply_markup
                )
            else:
                sent_msg = await context.bot.send_photo(
                    chat_id=group_id,
                    photo=photo,
                    caption=user_caption,
                    reply_markup=group_reply_markup
                )
                asyncio.create_task(delete_photo_after_delay(context, group_id, sent_msg.message_id, 300))

            sent_success = True
        except Exception as e:
            logging.error(f"Error processing for group {group_id}: {e}")

    if user_id in user_last_thanks_msg:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=user_last_thanks_msg[user_id]
            )
        except Exception as e:
            logging.error(f"Error deleting old thanks message: {e}")

    pm_keyboard = [
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ]
    pm_reply_markup = InlineKeyboardMarkup(pm_keyboard)

    if sent_success:
        thanks_msg = await update.message.reply_text(
            "✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!\nനന്ദി! ഇനിയും ഫോട്ടോകൾ അയക്കുക.",
            reply_markup=pm_reply_markup
        )
        user_last_thanks_msg[user_id] = thanks_msg.message_id
    else:
        await update.message.reply_text("⚠️ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് മെസ്സേജ് അയക്കാൻ സാധിക്കുന്നില്ലെന്ന് ഉറപ്പാക്കുക.")

# ടെക്സ്റ്റോ ലിങ്കുകളോ വന്നാൽ ഡിലീറ്റ് ചെയ്യും
async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        warning_msg = await update.message.reply_text(
            "⚠️ ലിങ്കുകളോ ടെക്സ്റ്റുകളോ അയക്കാൻ പാടില്ല! ഫോട്ടോകൾ മാത്രം അയക്കുക."
        )
        await asyncio.sleep(5)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=warning_msg.message_id)
    except Exception as e:
        logging.error(f"Error handling text/link: {e}")

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
    
    # GROUP + SUPERGROUP ഫിൽട്ടർ ചേർത്തിരിക്കുന്നു
    group_filter = filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP

    # 'halo' ആക്റ്റിവേഷൻ
    bot_app.add_handler(MessageHandler(group_filter & filters.Regex(r'(?i)^\s*halo\s*$'), activate_group))
    
    # ഗ്രൂപ്പ് മെസ്സേജ് ട്രാക്കിംഗ്
    bot_app.add_handler(ChatMemberHandler(track_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    bot_app.add_handler(MessageHandler(group_filter, track_groups))
    
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is starting...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()