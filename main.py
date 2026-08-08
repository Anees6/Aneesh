import os
import logging
import asyncio
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- FLASK & SELF-PING SERVER -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Powerfully Alive 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# സെർവർ ഉറങ്ങിപ്പോവാതിരിക്കാൻ തനിയെ 4 മിനിറ്റ് കൂടുമ്പോൾ Ping ചെയ്യുന്നു
def keep_alive_ping():
    while True:
        try:
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                requests.get(render_url)
                logging.info("Self-Ping successful!")
            else:
                # Localhost ping as fallback
                requests.get("http://127.0.0.1:8080/")
        except Exception as e:
            logging.error(f"Self-Ping error: {e}")
        # 4 മിനിറ്റ് (240 സെക്കൻഡ്) ഇടവേള
        asyncio.run(asyncio.sleep(240))

def start_background_tasks():
    # Flask Server ഓൺ ചെയ്യുന്നു
    t1 = Thread(target=run_flask)
    t1.daemon = True
    t1.start()
    
    # Self Ping ഓൺ ചെയ്യുന്നു
    t2 = Thread(target=keep_alive_ping)
    t2.daemon = True
    t2.start()
# ------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

connected_groups = {DEFAULT_GROUP_ID}

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല.")

# ബോട്ട് ഉള്ള ഗ്രൂപ്പ് ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# ഫോട്ടോസ് അയക്കാനുള്ള പ്രധാന ഫംഗ്ഷൻ (Retry ഓപ്ഷനോടെ)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    caption = update.message.caption or ""

    sent_success = False
    for group_id in list(connected_groups):
        # എറർ വന്നാൽ 3 തവണ വരെ വീണ്ടും അയക്കാൻ ശ്രമിക്കും
        for attempt in range(3):
            try:
                await context.bot.send_photo(
                    chat_id=group_id,
                    photo=photo,
                    caption=caption
                )
                sent_success = True
                break  # വിജയിച്ചാൽ ലൂപ്പ് നിർത്തും
            except Exception as e:
                logging.error(f"Attempt {attempt+1} failed for group {group_id}: {e}")
                await asyncio.sleep(1) # 1 സെക്കൻഡ് ഗ്യാപ്പ്

    if sent_success:
        await update.message.reply_text("✅ ഫോട്ടോ വിജയകരമായി ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!")
    else:
        await update.message.reply_text("⚠️ ഫോട്ടോ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")

# ടെക്സ്റ്റോ ലിങ്കുകളോ അയച്ചാൽ 5 സെക്കൻഡിൽ ഡിലീറ്റ് ചെയ്യും
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
    # സെർവറും സെൽഫ് പിംഗും സ്റ്റാർട്ട് ചെയ്യുന്നു
    start_background_tasks()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    
    # ഫോട്ടോസ് ഹാൻഡ്‌ലർ
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    
    # ടെക്സ്റ്റ്/ലിങ്ക് തടയൽ
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is powerfully running 24/7...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()