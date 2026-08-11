import os
import logging
import asyncio
from threading import Thread
import urllib.request
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
        logging.warning("⚠️ RENDER_EXTERNAL_URL കണ്ടുപിടിച്ചില്ല! Render Environment Variables-ൽ ഇത് നൽകിയിട്ടുണ്ടെന്ന് ഉറപ്പുവരുത്തുക.")
        return

    while True:
        try:
            url = f"{render_url.rstrip('/')}/health"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            # Non-blocking രീതിയിൽ ping അയക്കുന്നു
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
            logging.info("✅ Self ping successful! Server is awake.")
        except Exception as e:
            logging.error(f"❌ Self ping failed: {e}")
        
        await asyncio.sleep(180) # 3 മിനിറ്റിൽ ഒരിക്കൽ പിങ് ചെയ്യും
# -----------------------------------------------------------

# 5 മിനിറ്റിന് ശേഷം ഗ്രൂപ്പിൽ അയച്ച ഫോട്ടോ ഡിലീറ്റ് ചെയ്യുന്ന ഫങ്ഷൻ
async def delete_photo_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logging.info(f"Deleted photo message {message_id} from group {chat_id} after {delay} seconds.")
    except Exception as e:
        logging.error(f"Failed to delete photo message {message_id} in {chat_id}: {e}")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

# ടെക്സ്റ്റ് മാത്രം പോകേണ്ട പ്രത്യേക ഗ്രൂപ്പ് ഐഡി
INFO_ONLY_GROUP_ID = -1004376973168
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

connected_groups = {INFO_ONLY_GROUP_ID, DEFAULT_GROUP_ID}

# Muted ആയ യൂസർമാരുടെ ലിസ്റ്റ്
muted_users = set()

# യൂസർമാരുടെ ഏറ്റവും അവസാനത്തെ താങ്ക്സ് മെസ്സേജ് ഐഡി സൂക്ഷിക്കാൻ
user_last_thanks_msg = {}

# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല.")

# /id Command
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    await update.message.reply_text(f"📌 Chat ID: <code>{chat_id}</code>\n👤 Your ID: <code>{user_id}</code>", parse_mode="HTML")

# /mute command (ഗ്രൂപ്പിലും പി.എമ്മിലും വർക്ക് ചെയ്യും)
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

# /unmute command (ഗ്രൂപ്പിലും പി.എമ്മിലും വർക്ക് ചെയ്യും)
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

# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

# ഫോട്ടോ ഹാൻഡ്‌ലർ
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # യൂസർ മ്യൂട്ട് ആണെങ്കിൽ പി.എമ്മിൽ വിവരമറിയിക്കും, ഗ്രൂപ്പിലേക്ക് അയക്കില്ല
    if user_id in muted_users:
        await update.message.reply_text("🚫 നിങ്ങളെ തടഞ്ഞിരിക്കുന്നു! നിങ്ങൾ ഫോട്ടോ ഇട്ടാൽ ഗ്രൂപ്പിലേക്ക് പോകില്ല.")
        return

    photo = update.message.photo[-1].file_id
    user_caption = update.message.caption or ""

    # ഗ്രൂപ്പുകളിലേക്ക് അയക്കുന്ന ഇൻലൈൻ ബട്ടണുകൾ
    group_keyboard = [
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")],
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ]
    group_reply_markup = InlineKeyboardMarkup(group_keyboard)

    sent_success = False
    for group_id in list(connected_groups):
        try:
            # പ്രത്യേക ഗ്രൂപ്പിൽ (-1004376973168) ഫോട്ടോ ഇല്ലാതെ വിവരങ്ങൾ (Text/Details) മാത്രം അയക്കുന്നു
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
                # ബാക്കി എല്ലാ ഗ്രൂപ്പുകളിലും ഫോട്ടോയും ബട്ടണുകളും അയക്കുന്നു
                sent_msg = await context.bot.send_photo(
                    chat_id=group_id,
                    photo=photo,
                    caption=user_caption,
                    reply_markup=group_reply_markup
                )
                # 5 മിനിറ്റിന് (300 സെക്കൻഡ്) ശേഷം ഫോട്ടോ ഓട്ടോമാറ്റിക്കായി ഡിലീറ്റ് ചെയ്യാനുള്ള ടാസ്ക് സ്റ്റാർട്ട് ചെയ്യുന്നു
                asyncio.create_task(delete_photo_after_delay(context, group_id, sent_msg.message_id, 300))

            sent_success = True
        except Exception as e:
            logging.error(f"Error processing for group {group_id}: {e}")

    # യൂസറുടെ മുൻപത്തെ താങ്ക്സ് മെസ്സേജ് ഉണ്ടെങ്കിൽ അത് ഡിലീറ്റ് ചെയ്യും
    if user_id in user_last_thanks_msg:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=user_last_thanks_msg[user_id]
            )
        except Exception as e:
            logging.error(f"Error deleting old thanks message: {e}")

    # യൂസറുടെ പി.എമ്മിലേക്ക് (PM) അയക്കുന്ന താങ്ക്സ് ബട്ടൺ
    pm_keyboard = [
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ]
    pm_reply_markup = InlineKeyboardMarkup(pm_keyboard)

    if sent_success:
        thanks_msg = await update.message.reply_text(
            "✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!\nനന്ദി! ഇനിയും ഫോട്ടോകൾ അയക്കുക.",
            reply_markup=pm_reply_markup
        )
        # പുതിയ മെസ്സേജ് ഐഡി സേവ് ചെയ്യുന്നു
        user_last_thanks_msg[user_id] = thanks_msg.message_id
    else:
        await update.message.reply_text("⚠️ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")

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

# പോസ്റ്റ് ആക്ഷൻ എക്സിക്യൂഷൻ (Self-Ping സ്റ്റാർട്ട് ചെയ്യുന്നു)
async def post_init(application):
    asyncio.create_task(self_ping())

def main():
    # Flask web server ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യുന്നു
    t = Thread(target=run_flask, daemon=True)
    t.start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

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