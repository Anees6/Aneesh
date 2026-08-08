import os
import logging
import asyncio
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Logging Setup (Errors അറിയാൻ)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- FLASK SERVER (Keep-Alive) -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Alive 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
# ------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

# നിങ്ങളുടെ ഗ്രൂപ്പ് ഐഡി ഇവിടെ ചേർത്തിട്ടുണ്ട്
# (നിങ്ങൾ ബോട്ടിനെ ആഡ് ചെയ്യുന്ന ഏതൊരു ഗ്രൂപ്പിലേക്കും ഓട്ടോമാറ്റിക്കായി അയക്കാനും ഇതിൽ സൗകര്യമുണ്ട്)
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))
connected_groups = {DEFAULT_GROUP_ID}

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അയക്കാൻ പാടില്ല.")

# ഗ്രൂപ്പിലേക്ക് ബോട്ടിനെ ചേർത്താൽ ആ ഐഡി സേവ് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# യൂസർമാർ അയക്കുന്ന ഫോട്ടോസ് ഗ്രൂപ്പിലേക്ക് അയക്കുന്നു (അനോണിമസ് ആയി)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id  # ഹൈ ക്വാളിറ്റി ഫോട്ടോ എടുക്കുന്നു
    caption = update.message.caption or ""   # ക്യാപ്ഷൻ ഉണ്ടെങ്കിൽ അത് എടുക്കുന്നു

    sent_success = False
    for group_id in list(connected_groups):
        try:
            # Send Photo വഴി നേരിട്ട് അയക്കുന്നു (അയച്ചയാളുടെ പേര് കാണിക്കില്ല)
            await context.bot.send_photo(
                chat_id=group_id,
                photo=photo,
                caption=caption
            )
            sent_success = True
        except Exception as e:
            logging.error(f"Error sending to group {group_id}: {e}")

    if sent_success:
        await update.message.reply_text("✅ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")
    else:
        await update.message.reply_text("⚠️ ഫോട്ടോ അയക്കാൻ കഴിഞ്ഞില്ല. ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission ഉണ്ടോ എന്ന് ഉറപ്പുവരുത്തുക!")

# ടെക്സ്റ്റോ ലിങ്കുകളോ അയച്ചാൽ ഡിലീറ്റ് ചെയ്യാനും വാർണിംഗ് കൊടുക്കാനും
async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        warning_msg = await update.message.reply_text(
            "⚠️ ലിങ്കുകളോ ടെക്സ്റ്റുകളോ അയക്കാൻ പാടില്ല! ഫോട്ടോകൾ മാത്രം അയക്കുക."
        )
        
        # 5 സെക്കൻഡിന് ശേഷം ഡിലീറ്റ് ചെയ്യുന്നു
        await asyncio.sleep(5)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=warning_msg.message_id)
    except Exception as e:
        logging.error(f"Error deleting message: {e}")

def main():
    # Flask Web Server
    keep_alive()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    
    # ഫോട്ടോകൾ മാത്രം സ്വീകരിക്കുന്നു
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    
    # ഫോട്ടോ അല്ലാത്തവ തടയുന്നു
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is full-time running...")
    # drop_pending_updates=True കൊടുക്കുന്നത് ബോട്ട് ഓഫ് ആയിരുന്നപ്പോൾ വന്ന പഴയ മെസ്സേജുകൾ ഇഗ്നോർ ചെയ്യാൻ സഹായിക്കും
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()