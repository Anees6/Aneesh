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

# Bot Credentials
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോസ് മാത്രം അയക്കുക. ടെക്സ്റ്റ്/ലിങ്കുകൾ അനുവദനീയമല്ല.")

# ഫോട്ടോസ് മാത്രം ഗ്രൂപ്പിലേക്ക് അയക്കുന്ന ഫംഗ്ഷൻ (പേര് ഇല്ലാതെ)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # ഫോട്ടോ മാത്രം എടുത്ത് ഗ്രൂപ്പിലേക്ക് അയക്കുന്നു (Copy message ഉപയോഗിച്ചാൽ അയച്ചയാളുടെ പേര് കാണില്ല)
        await context.bot.copy_message(
            chat_id=GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
        await update.message.reply_text("✅ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")
    except Exception as e:
        logging.error(f"Error handling photo: {e}")

# ടെക്സ്റ്റോ ലിങ്കുകളോ അയച്ചാൽ വാർണിംഗ് കൊടുത്ത് ഡിലീറ്റ് ചെയ്യുന്ന ഫംഗ്ഷൻ
async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # വാർണിംഗ് മെസ്സേജ് അയക്കുന്നു
        warning_msg = await update.message.reply_text(
            "⚠️ ലിങ്കുകളോ ടെക്സ്റ്റുകളോ അയക്കാൻ പാടില്ല! ഫോട്ടോകൾ മാത്രം അയക്കുക."
        )
        
        # 5 സെക്കൻഡിന് ശേഷം യൂസറുടെ മെസ്സേജും ബോട്ടിന്റെ മെസ്സേജും ഡിലീറ്റ് ചെയ്യും
        await asyncio.sleep(5)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=warning_msg.message_id)
    except Exception as e:
        logging.error(f"Error handling text/link: {e}")

def main():
    # Keep-alive സെർവർ സ്റ്റാർട്ട് ചെയ്യൽ
    keep_alive()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    bot_app.add_handler(CommandHandler("start", start))
    
    # 1. ഫോട്ടോസ് മാത്രം പ്രൊസസ് ചെയ്യും
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    
    # 2. ഫോട്ടോ അല്ലാത്ത മറ്റെല്ലാ മെസ്സേജുകളും (Text, Link, Documents, Videos etc.) റിജക്ട് ചെയ്യും
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is running...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()