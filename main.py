import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta
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

# ⚠️ ടെക്സ്റ്റ് മെസ്സേജ് മാത്രം വരണമെന്നുള്ള പ്രത്യേക ഗ്രൂപ്പ് ഐഡി:
SPECIAL_GROUP_ID = int(os.environ.get("SPECIAL_GROUP_ID", "-1004376973168"))

# 👑 അഡ്മിൻ്റെ Telegram User ID (കമാൻഡ് ഉപയോഗിക്കാൻ)
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7965472783"))

connected_groups = {DEFAULT_GROUP_ID, SPECIAL_GROUP_ID}

# Username ഉം User ID യും മാപ്പ് ചെയ്തു വെക്കാൻ ഒരു നിഘണ്ടു (Dictionary)
user_registry = {}

# ബ്ലോക്ക് ചെയ്ത യൂസർമാരുടെ User ID ലിസ്റ്റ്
blocked_users = set()

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

# ഫോട്ടോകൾ പ്രോസസ്സ് ചെയ്യുന്നു
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    # യൂസർ ബ്ലോക്ക് ചെയ്ത ആളാണോ എന്ന് പരിശോധിക്കുന്നു
    if user.id in blocked_users:
        msg = await update.message.reply_text("🚫 ക്ഷമിക്കണം! നിങ്ങളെ ബാൻ ചെയ്തിരിക്കുകയാണ്. നിങ്ങളുടെ ഫോട്ടോകൾ ഗ്രൂപ്പിലേക്ക് അയക്കില്ല.")
        schedule_message_deletion(context, update.effective_chat.id, msg.message_id)
        return

    photo = update.message.photo[-1].file_id
    
    # യൂസറുടെ ഐഡിയും യൂസർനെയിമും സൂക്ഷിക്കുന്നു
    if user.username:
        user_registry[user.username.lower()] = user.id
        user_mention = f"@{user.username}"
    else:
        user_mention = f'<a href="tg://user?id={user.id}">@{user.full_name}</a>'

    # Indian Standard Time (IST = UTC + 5:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%I:%M %p")

    # പ്രത്യേക ഗ്രൂപ്പിലേക്കുള്ള ടെക്സ്റ്റ് മെസ്സേജ്
    text_info = (
        f"👤 Name: {user_mention}\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📅 Date: {date_str}\n"
        f"⏰ Time: {time_str}"
    )

    sent_success = False
    for group_id in list(connected_groups):
        try:
            # പ്രത്യേക ഗ്രൂപ്പിൽ (-1004376973168) ഫോട്ടോ ഇല്ലാതെ Text മാത്രം അയക്കുന്നു
            if group_id == SPECIAL_GROUP_ID:
                await context.bot.send_message(
                    chat_id=group_id,
                    text=text_info,
                    parse_mode="HTML"
                )
            else:
                # മറ്റ് ഗ്രൂപ്പുകളിൽ ഫോട്ടോ മാത്രം അയക്കുന്നു
                await context.bot.send_photo(
                    chat_id=group_id,
                    photo=photo
                )
            sent_success = True
        except Exception as e:
            logging.error(f"Error sending to group {group_id}: {e}")

    if sent_success:
        msg = await update.message.reply_text("✅ ഫോട്ടോ വിജയകരമായി പ്രോസസ്സ് ചെയ്ത് അയച്ചിട്ടുണ്ട്!")
        schedule_message_deletion(context, update.effective_chat.id, msg.message_id)
    else:
        msg = await update.message.reply_text("⚠️ അയക്കാൻ കഴിഞ്ഞില്ല! ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക.")
        schedule_message_deletion(context, update.effective_chat.id, msg.message_id)

# 🚫 അഡ്മിന് മാത്രം ഒരാളെ ബ്ലോക്ക് ചെയ്യാനുള്ള കമാൻഡ് (/block @username അല്ലെങ്കിൽ /block 12345678)
async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ ഈ കമാൻഡ് ഉപയോഗിക്കാൻ അഡ്മിന് മാത്രമേ അധികാരമുള്ളൂ!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി Username അല്ലെങ്കിൽ User ID നൽകുക.\nഉദാഹരണത്തിന്: `/block @username` അല്ലെങ്കിൽ `/block 123456789`", parse_mode="Markdown")
        return

    target = context.args[0].replace("@", "").lower()
    user_id = user_registry.get(target) if not target.isdigit() else int(target)

    if not user_id:
        await update.message.reply_text("❌ യൂസറെ കണ്ടെത്താൻ കഴിഞ്ഞില്ല. ആ യൂസർ ബോട്ടിന് മുൻപ് മെസ്സേജ് അയച്ചിട്ടുണ്ടെന്ന് ഉറപ്പാക്കുക.")
        return

    blocked_users.add(user_id)
    await update.message.reply_text(f"🚫 User (`{user_id}`) വിജയകരമായി BLOCK ചെയ്തു! ഇനി ഇയാൾ ബോട്ടിന് ഫോട്ടോ അയച്ചാൽ ഗ്രൂപ്പിലേക്ക് പോകില്ല.", parse_mode="Markdown")

# 🟢 ബ്ലോക്ക് മാറ്റാനുള്ള കമാൻഡ് (/unblock @username അല്ലെങ്കിൽ /unblock 12345678)
async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ ഈ കമാൻഡ് ഉപയോഗിക്കാൻ അഡ്മിന് മാത്രമേ അധികാരമുള്ളൂ!")
        return

    if not context.args:
        await update.message.reply_text("⚠️ ദയവായി Username അല്ലെങ്കിൽ User ID നൽകുക.\nഉദാഹരണത്തിന്: `/unblock @username` അല്ലെങ്കിൽ `/unblock 123456789`", parse_mode="Markdown")
        return

    target = context.args[0].replace("@", "").lower()
    user_id = user_registry.get(target) if not target.isdigit() else int(target)

    if not user_id:
        await update.message.reply_text("❌ യൂസറെ കണ്ടെത്താൻ കഴിഞ്ഞില്ല.")
        return

    if user_id in blocked_users:
        blocked_users.remove(user_id)
        await update.message.reply_text(f"✅ User (`{user_id}`) UNBLOCK ചെയ്തു! ഇനി ഇയാൾക്ക് ഫോട്ടോ അയക്കാം.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ ഈ യൂസർ ബ്ലോക്ക് ലിസ്റ്റിൽ ഇല്ല.")

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
    bot_app.add_handler(CommandHandler("block", block_user))
    bot_app.add_handler(CommandHandler("ban", block_user))  # /ban അടടിച്ചാലും block ചെയ്യും
    bot_app.add_handler(CommandHandler("unblock", unblock_user))
    bot_app.add_handler(CommandHandler("unban", unblock_user))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))

    print("Bot is starting...")
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()