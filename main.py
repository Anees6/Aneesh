import os
import logging
import asyncio
from threading import Thread
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
    return "Bot is Running Live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# -----------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

# നിങ്ങളുടെ ടെസ്റ്റ് ഗ്രൂപ്പ് ഐഡി
TARGET_GROUP_ID = -1004376973168

DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", str(TARGET_GROUP_ID)))
connected_groups = {DEFAULT_GROUP_ID, TARGET_GROUP_ID}

# Muted ആയ യൂസർമാരുടെ ലിസ്റ്റ് സൂക്ഷിക്കാൻ
muted_users = set()

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല.")

# /id Command
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(f"📌 Chat ID: <code>{chat_id}</code>\n👤 Your ID: <code>{user_id}</code>", parse_mode="HTML")

# /mute command (ഉദാഹരണത്തിന്: /mute 7965472783)
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി User ID നൽകാമോ? (Eg: /mute 7965472783)")
        return
    
    try:
        user_to_mute = int(context.args[0])
        muted_users.add(user_to_mute)
        await update.message.reply_text(f"🔇 User {user_to_mute} മ്യൂട്ട് ചെയ്യപ്പെട്ടിരിക്കുന്നു! ഇനി ഇവരുടെ പോസ്റ്റുകൾ ഗ്രൂപ്പിൽ വരില്ല.")
    except ValueError:
        await update.message.reply_text("⚠️ നൽകിയ User ID തെറ്റാണ്. സംഖ്യകൾ മാത്രം നൽകുക.")

# /unmute command (ഉദാഹരണത്തിന്: /unmute 7965472783)
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി User ID നൽകാമോ? (Eg: /unmute 7965472783)")
        return
    
    try:
        user_to_unmute = int(context.args[0])
        if user_to_unmute in muted_users:
            muted_users.remove(user_to_unmute)
            await update.message.reply_text(f"🔊 User {user_to_unmute} അൺ-മ്യൂട്ട് ചെയ്തിരിക്കുന്നു!")
        else:
            await update.message.reply_text("ℹ️ ഈ യൂസർ മ്യൂട്ട് ലിസ്റ്റിൽ ഇല്ല.")
    except ValueError:
        await update.message.reply_text("⚠️ നൽകിയ User ID തെറ്റാണ്.")

# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# ഫോട്ടോകൾ മാത്രം ഗ്രൂപ്പിലേക്ക് അയക്കുന്നു
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # യൂസർ മ്യൂട്ട് ആണെങ്കിൽ ഫോട്ടോ അയക്കില്ല
    if user_id in muted_users:
        await update.message.reply_text("🚫 നിങ്ങൾ മ്യൂട്ട് ചെയ്യപ്പെട്ടിരിക്കുന്നു. നിങ്ങളുടെ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് പോസ്റ്റ് ആകില്ല.")
        return

    photo = update.message.photo[-1].file_id
    user_caption = update.message.caption or ""

    # @Faseena5bot ലേക്ക് റീഡയറക്ട് ചെയ്യുന്ന URL ബട്ടൺ
    keyboard = [
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    sent_success = False
    for group_id in list(connected_groups):
        try:
            # നിർദ്ദിഷ്ട ഗ്രൂപ്പിൽ (TARGET_GROUP_ID) മാത്രം പേരും യൂസർനേമും കാണിക്കും
            if group_id == TARGET_GROUP_ID:
                user_mention = f"<a href='tg://user?id={user_id}'>{user.full_name}</a>"
                if user.username:
                    user_mention += f" (@{user.username})"
                
                final_caption = f"{user_caption}\n\n👤 <b>Posted by:</b> {user_mention}\n🆔 <b>User ID:</b> <code>{user_id}</code>"
            else:
                final_caption = user_caption

            await context.bot.send_photo(
                chat_id=group_id,
                photo=photo,
                caption=final_caption,
                parse_mode="HTML" if group_id == TARGET_GROUP_ID else None,
                reply_markup=reply_markup
            )
            sent_success = True
        except Exception as e:
            logging.error(f"Error sending photo to {group_id}: {e}")

    if sent_success:
        await update.message.reply_text("✅ ഫോട്ടോ വിജയകരമായി ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")
    else:
        await update.message.reply_text("⚠️ ഫോട്ടോ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")

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

def main():
    t = Thread(target=run_flask, daemon=True)
    t.start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("id", get_id))
    bot_app.add_handler(CommandHandler("mute", mute_user))
    bot_app.add_handler(CommandHandler("unmute", unmute_user))
    
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is starting...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()