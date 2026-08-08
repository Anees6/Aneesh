import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- FLASK SERVER (Bot Keep-Alive) -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render നൽകുന്ന PORT ലേക്ക് അല്ലെങ്കിൽ Default PORT 8080 ലേക്ക് റൺ ചെയ്യുന്നു
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# ------------------------------------------------------------------

# Bot Token & Group ID
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("നമസ്കാരം! നിങ്ങൾ അയക്കുന്ന മെസ്സേജുകൾ ഗ്രൂപ്പിലേക്ക് ഫോർവേർഡ് ചെയ്യുന്നതാണ്.")

async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logging.error(f"Error forwarding message: {e}")

def main():
    # Flask Web Server സ്റ്റാർട്ട് ചെയ്യുന്നു
    keep_alive()
    print("Flask Server started for Keep-Alive...")

    # Telegram Bot സ്റ്റാർട്ട് ചെയ്യുന്നു
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, forward_to_group))

    print("Bot starting...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()