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

# ----------------- FLASK SERVER (Keep-Alive) -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# ------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

# ബോട്ടിനെ ചേർക്കുന്ന ഗ്രൂപ്പുകളുടെ ഐഡികൾ സൂക്ഷിക്കാൻ ഒരു Set
connected_groups = set()

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോസ് മാത്രം അയക്കുക. ടെക്സ്റ്റ്/ലിങ്കുകൾ അനുവദനീയമല്ല.")

# ബോട്ടിനെ പുതിയ ഒരു ഗ്രൂപ്പിൽ ആഡ് ചെയ്യുമ്പോൾ ആ ഗ്രൂപ്പ് ഐഡി സേവ് ചെയ്യുന്നു
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ["group", "supergroup"]:
        connected_groups.add(chat.id)
        logging.info(f"Added to Group: {chat.title} ({chat.id})")

# ഫോട്ടോസ് സ്വീകരിച്ച് ബോട്ട് ജോയിൻ ചെയ്തിട്ടുള്ള എല്ലാ ഗ്രൂപ്പുകളിലേക്കും അയക്കുന്നു
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not connected_groups:
        await update.message.reply_text("⚠️ ബോട്ട് ഇതുവരെ ഒരു ഗ്രൂപ്പിലും ആഡ് ചെയ്തിട്ടില്ല, അല്ലെങ്കിൽ അഡ്മിൻ പെർമിഷൻ ലഭിച്ചിട്ടില്ല!")
        return

    sent_count = 0
    for group_id in list(connected_groups):
        try:
            # ഫോട്ടോ പേര് ഇല്ലാതെ അയക്കുന്നു (Copy message)
            await context.bot.copy_message(
                chat_id=group_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            sent_count += 1
        except Exception as e:
            logging.error(f"Error sending photo to group {group_id}: {e}")

    if sent_count > 0:
        await update.message.reply_text("✅ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")

# ടെക്സ്റ്റോ ലിങ്കുകളോ അയച്ചാൽ വാർണിംഗ് കൊടുത്ത് ഡിലീറ്റ് ചെയ്യുന്നു
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

    # Handlers
    bot_app.add_handler(CommandHandler("start", start))
    
    # 1. ബോട്ടിനെ ഗ്രൂപ്പിലേക്ക് ആഡ് ചെയ്യുമ്പോൾ / ഗ്രൂപ്പിലെ മെസ്സേജുകൾ വരുമ്പോൾ ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യും
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))

    # 2. യൂസർമാർ അയക്കുന്ന ഫോട്ടോസ് മാത്രം ഹാൻഡ്‌ൽ ചെയ്യും
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    
    # 3. ഫോട്ടോ അല്ലാത്ത മറ്റെല്ലാ മെസ്സേജുകളും റിജക്ട് ചെയ്യും
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is running...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()