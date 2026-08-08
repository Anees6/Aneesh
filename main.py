import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Logging സെറ്റപ്പ്
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Render Environment Variables വഴി നൽകേണ്ടവ
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

# /start കമാൻഡ്
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("നമസ്കാരം! നിങ്ങൾ അയക്കുന്ന മെസ്സേജുകൾ ഗ്രൂപ്പിലേക്ക് ഫോർവേർഡ് ചെയ്യുന്നതാണ്.")

# യൂസർ അയക്കുന്ന മെസ്സേജുകൾ ഗ്രൂപ്പിലേക്ക് ഫോർവേർഡ് ചെയ്യുന്ന ഫംഗ്ഷൻ
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logging.error(f"Error forwarding message: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, forward_to_group))

    print("Bot starting...")
    app.run_polling()