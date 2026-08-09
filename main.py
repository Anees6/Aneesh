import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
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

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# -----------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

# ⚠️ യൂസർനെയിം വരണമെന്നുള്ള നിങ്ങളുടെ പ്രത്യേക ഗ്രൂപ്പ് ഐഡി:
SPECIAL_GROUP_ID = int(os.environ.get("SPECIAL_GROUP_ID", "-1004376973168"))

connected_groups = {DEFAULT_GROUP_ID, SPECIAL_GROUP_ID}

# ടാസ്കുകൾ Garbage Collection വഴി ഡിലീറ്റ് ആകാതിരിക്കാൻ Strong Reference സൂക്ഷിക്കുന്നു
active_tasks = set()

# 15 മിനിറ്റിനു ശേഷം മെസ്സേജ് ഡിലീറ്റ് ചെയ്യാനുള്ള ഹെൽപ്പർ ഫങ്ഷൻ
async def delete_msg_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay_seconds: int = 900):
    await asyncio.sleep(delay_seconds)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Error auto-deleting message {message_id} in chat {chat_id}: {e}")

# ടാസ്ക് സുരക്ഷിതമായി റൺ ചെയ്യുന്ന ഫങ്ഷൻ
def schedule_message_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 900):
    task = asyncio.create_task(delete_msg_after_delay(context, chat_id, message_id, delay))
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല.")
    schedule_message_deletion(context, update.effective_chat.id, msg.message_id)

# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# ഫോട്ടോകൾ ഗ്രൂപ്പുകളിലേക്ക് അയക്കുന്നു
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    user = update.message.from_user
    
    # യൂസറുടെ പേര് കണ്ടെത്തുന്നു (Username ഉണ്ടെങ്കിൽ അത്, ഇല്ലെങ്കിൽ Full Name)
    if user.username:
        user_info = f"👤 Sender: @{user.username}"
    else:
        user_info = f"👤 Sender: {user.full_name}"

    sent_success = False
    for group_id in list(connected_groups):
        try:
            # പ്രത്യേക ഗ്രൂപ്പ് (-1004376973168) ആണെങ്കിൽ പേര്/യൂസർനെയിം കാപ്ഷനായി നൽകും
            if group_id == SPECIAL_GROUP_ID:
                caption_text = user_info
            else:
                caption_text = ""  # മറ്റ് ഗ്രൂപ്പുകളിൽ ഫോട്ടോ മാത്രം

            await context.bot.send_photo(
                chat_id=group_id,
                photo=photo,
                caption=caption_text
            )
            sent_success = True
        except Exception as e:
            logging.error(f"Error sending photo to {group_id}: {e}")

    if sent_success:
        msg = await update.message.reply_text("✅ ഫോട്ടോ വിജയകരമായി ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")
        schedule_message_deletion(context, update.effective_chat.id, msg.message_id)
    else:
        msg = await update.message.reply_text("⚠️ ഫോട്ടോ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")
        schedule_message_deletion(context, update.effective_chat.id, msg.message_id)

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
    keep_alive()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is starting...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()