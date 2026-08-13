import os
import logging
import asyncio
import re
from threading import Thread
import urllib.request
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    ContextTypes, 
    MessageHandler, 
    CommandHandler, 
    ChatMemberHandler, 
    filters
)

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

async def self_ping():
    await asyncio.sleep(10)
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        return
    while True:
        try:
            url = f"{render_url.rstrip('/')}/health"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            await asyncio.to_thread(urllib.request.urlopen, req, timeout=10)
        except Exception as e:
            logging.error(f"❌ Self ping failed: {e}")
        await asyncio.sleep(180)

# -----------------------------------------------------------

async def delete_photo_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Failed to delete photo message {message_id} in {chat_id}: {e}")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")
INFO_ONLY_GROUP_ID = -1004376973168
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

connected_groups = {INFO_ONLY_GROUP_ID, DEFAULT_GROUP_ID}
muted_users = set()
banned_users = set()
user_warnings = {}  # {user_id: count}

user_last_thanks_msg = {}
user_last_mute_warning_msg = {}
group_user_last_warning_msg = {}  # {(chat_id, user_id): message_id} ഗ്രൂപ്പിലെ മുന്നറിയിപ്പുകൾ ഡിലീറ്റ് ചെയ്യാൻ

# സമയം കണക്കാക്കാൻ സഹായിക്കുന്ന ഫങ്ഷൻ
def parse_duration(time_str: str) -> int:
    match = re.match(r"^(\d+)([mhd])$", time_str.lower())
    if not match:
        return 0
    val, unit = match.groups()
    val = int(val)
    if unit == 'm':
        return val * 60
    elif unit == 'h':
        return val * 3600
    elif unit == 'd':
        return val * 86400
    return 0

# എല്ലാ ഗ്രൂപ്പുകളിലേക്കും മെസ്സേജ് ബ്രോഡ്കാസ്റ്റ് ചെയ്യാൻ
async def broadcast_to_groups(context, text):
    tasks = [context.bot.send_message(chat_id=gid, text=text, parse_mode="HTML") for gid in list(connected_groups)]
    await asyncio.gather(*tasks, return_exceptions=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📌 Chat ID: <code>{update.effective_chat.id}</code>\n👤 Your ID: <code>{update.effective_user.id}</code>", parse_mode="HTML")

# Permanent Mute Command
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ഉപയോഗിക്കേണ്ട രീതി: /mute <User_ID/@username>")
        return
    user_input = context.args[0].strip()
    target_user_id = int(user_input) if user_input.isdigit() else None
    user_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>" if target_user_id else user_input
    
    if target_user_id:
        muted_users.add(target_user_id)
    
    await update.message.reply_text(f"🔇 {user_input} വിജയകരമായി മ്യൂട്ട് ചെയ്തു!", parse_mode="HTML")
    broadcast_message = f"{user_mention} നിങ്ങളെ ഞാൻ mute ആക്കി ഇനി ഞാൻ നിങ്ങളുടെ ഒരു പോസ്റ്റും ഗ്രൂപ്പിൽ ഇടില്ല"
    await broadcast_to_groups(context, broadcast_message)

# Permanent Unmute Command
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    try:
        user_to_unmute = int(context.args[0])
        if user_to_unmute in muted_users:
            muted_users.remove(user_to_unmute)
            await update.message.reply_text(f"🔊 User <code>{user_to_unmute}</code> അൺ-മ്യൂട്ട് ചെയ്തിരിക്കുന്നു!", parse_mode="HTML")
        if user_to_unmute in banned_users:
            banned_users.remove(user_to_unmute)
    except ValueError: pass

# Temporary Mute Command (/tempmute 12345678 10m)
async def temp_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ ഉപയോഗിക്കേണ്ട രീതി: /tempmute <User_ID/@username> <സമയം: eg 10m, 1h, 1d>")
        return
    
    user_input = context.args[0].strip()
    duration_str = context.args[1].strip()
    seconds = parse_duration(duration_str)
    
    if seconds == 0:
        await update.message.reply_text("⚠️ സമയം തെറ്റാണ്! 10m, 1h, 1d എന്നീ രീതിയിൽ നൽകുക.")
        return

    target_user_id = int(user_input) if user_input.isdigit() else None
    user_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>" if target_user_id else user_input
    
    if target_user_id:
        muted_users.add(target_user_id)

    await update.message.reply_text(f"⏳ {user_input} എന്ന യൂസറെ {duration_str} സമയത്തേക്ക് മ്യൂട്ട് ചെയ്തു!")
    
    broadcast_msg = f"⏳ {user_mention} നിങ്ങളെ {duration_str} സമയത്തേക്ക് താൽക്കാലികമായി Mute ചെയ്തിരിക്കുന്നു! ഈ സമയത്ത് നിങ്ങളുടെ പോസ്റ്റുകൾ വരുന്നതല്ല."
    await broadcast_to_groups(context, broadcast_msg)

    async def auto_unmute():
        await asyncio.sleep(seconds)
        if target_user_id and target_user_id in muted_users:
            muted_users.remove(target_user_id)
            unmute_msg = f"🔊 {user_mention} നിങ്ങളുടെ താൽക്കാലിക മ്യൂട്ട് സമയം അവസാനിച്ചിരിക്കുന്നു! ഇനി പോസ്റ്റുകൾ അയക്കാം."
            await broadcast_to_groups(context, unmute_msg)

    asyncio.create_task(auto_unmute())

# Temporary Ban Command (/tempban 12345678 30m)
async def temp_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ ഉപയോഗിക്കേണ്ട രീതി: /tempban <User_ID/@username> <സമയം: eg 10m, 1h, 1d>")
        return

    user_input = context.args[0].strip()
    duration_str = context.args[1].strip()
    seconds = parse_duration(duration_str)

    if seconds == 0:
        await update.message.reply_text("⚠️ സമയം തെറ്റാണ്! 10m, 1h, 1d രീതിയിൽ നൽകുക.")
        return

    target_user_id = int(user_input) if user_input.isdigit() else None
    user_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>" if target_user_id else user_input

    if target_user_id:
        banned_users.add(target_user_id)

    await update.message.reply_text(f"🚫 {user_input} എന്ന യൂസറെ {duration_str} സമയത്തേക്ക് ബാൻ ചെയ്തു!")

    broadcast_msg = f"🚫 {user_mention} നിങ്ങളെ {duration_str} സമയത്തേക്ക് ബോട്ട് താൽക്കാലികമായി Ban ചെയ്തിരിക്കുന്നു!"
    await broadcast_to_groups(context, broadcast_msg)

    async def auto_unban():
        await asyncio.sleep(seconds)
        if target_user_id and target_user_id in banned_users:
            banned_users.remove(target_user_id)
            unban_msg = f"✅ {user_mention} നിങ്ങളുടെ താൽക്കാലിക ബാൻ സമയം അവസാനിച്ചിരിക്കുന്നു."
            await broadcast_to_groups(context, unban_msg)

    asyncio.create_task(auto_unban())

# Warning Command (/warn 12345678)
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ഉപയോഗിക്കേണ്ട രീതി: /warn <User_ID/@username>")
        return

    user_input = context.args[0].strip()
    target_user_id = int(user_input) if user_input.isdigit() else None
    user_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>" if target_user_id else user_input

    if not target_user_id:
        await update.message.reply_text("⚠️ Warning നൽകാൻ യൂസറുടെ ഡിജിറ്റ് ID തന്നെ വേണം.")
        return

    current_warns = user_warnings.get(target_user_id, 0) + 1
    user_warnings[target_user_id] = current_warns

    if current_warns >= 3:
        muted_users.add(target_user_id)
        user_warnings[target_user_id] = 0
        await update.message.reply_text(f"⚠️ {user_input} 3 വാണിംഗുകൾ പൂർത്തിയായതിനാൽ മ്യൂട്ട് ചെയ്തു!")
        broadcast_msg = f"⚠️ {user_mention} നിങ്ങൾക്ക് 3/3 വാണിംഗുകൾ ലഭിച്ചതിനാൽ നിങ്ങളെ ബോട്ട് permanently Mute ചെയ്തിരിക്കുന്നു!"
        await broadcast_to_groups(context, broadcast_msg)
    else:
        await update.message.reply_text(f"⚠️ {user_input} എന്ന യൂസർക്ക് Warning നൽകി ({current_warns}/3)")
        broadcast_msg = f"⚠️ {user_mention}, അഡ്മിൻ നിങ്ങൾക്ക് താക്കീത് (Warning) നൽകിയിരിക്കുന്നു! [{current_warns}/3]\n3 വാണിംഗ് ആയാൽ നിങ്ങളെ മ്യൂട്ട് ചെയ്യുന്നതാണ്."
        await broadcast_to_groups(context, broadcast_msg)

# Reset Warning (/unwarn 12345678)
async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    try:
        user_id = int(context.args[0])
        user_warnings[user_id] = 0
        await update.message.reply_text(f"✅ User {user_id}-ന്റെ വാണിംഗുകൾ 0 ആക്കി മാറ്റിയിട്ടുണ്ട്.")
    except ValueError: pass

async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

async def track_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
            connected_groups.add(chat.id)

# അഡ്മിൻ ആയിട്ടുള്ള ഗ്രൂപ്പുകളിൽ 15-ൽ കൂടുതൽ ഇംഗ്ലീഷ് അക്ഷരം വന്നാൽ ഡിലീറ്റ് ചെയ്യുന്ന ഹാൻഡ്‌ലർ
async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    if not chat or not message or not user or user.is_bot:
        return

    connected_groups.add(chat.id)

    # ബോട്ട് അഡ്മിൻ ആണോ എന്ന് പരിശോധിക്കുന്നു
    try:
        bot_member = await context.bot.get_chat_member(chat_id=chat.id, user_id=context.bot.id)
        if bot_member.status != "administrator":
            return  # ബോട്ട് അഡ്മിൻ അല്ലെങ്കിൽ ഒന്നും ചെയ്യില്ല
    except Exception as e:
        logging.error(f"Error checking admin status in {chat.id}: {e}")
        return

    text_content = message.text or message.caption or ""
    
    # ഇംഗ്ലീഷ് അക്ഷരങ്ങൾ എണ്ണുന്നു
    english_chars = len(re.findall(r'[a-zA-Z]', text_content))

    # 15-ൽ കൂടുതൽ ഇംഗ്ലീഷ് അക്ഷരങ്ങൾ വന്നാൽ മാത്രം ഡിലീറ്റ് ചെയ്യും
    if english_chars > 15:
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Error deleting user message in group {chat.id}: {e}")

        key = (chat.id, user.id)

        # പഴയ വാണിംഗ് മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു
        if key in group_user_last_warning_msg:
            try:
                await context.bot.delete_message(chat_id=chat.id, message_id=group_user_last_warning_msg[key])
            except Exception as e:
                logging.error(f"Error deleting old group warning message: {e}")

        user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        warn_text = f"⚠️ {user_mention}, ഇങ്ങനത്തെ സംസാരം ഇവിടെ പറ്റില്ല!"

        try:
            warn_msg = await context.bot.send_message(chat_id=chat.id, text=warn_text, parse_mode="HTML")
            group_user_last_warning_msg[key] = warn_msg.message_id
        except Exception as e:
            logging.error(f"Error sending warn message in group {chat.id}: {e}")

async def notify_muted_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in user_last_mute_warning_msg:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_mute_warning_msg[user.id])
        except: pass
    user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    mute_msg = await update.message.reply_text(f"🚫 {user_mention}, അഡ്മിൻ നിങ്ങളെ മ്യൂട്ട്/ബാൻ ആക്കിയിരിക്കുകയാണ്!", parse_mode="HTML")
    user_last_mute_warning_msg[user.id] = mute_msg.message_id

async def send_to_single_group(context, group_id, photo, user, user_caption, group_reply_markup):
    try:
        if group_id == INFO_ONLY_GROUP_ID:
            user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
            info_text = f"📥 <b>New Photo Submitted</b>\n\n👤 <b>Name:</b> {user_mention}\n🆔 <b>User ID:</b> <code>{user.id}</code>\n💬 <b>Caption:</b> {user_caption or 'No Caption'}"
            await context.bot.send_message(chat_id=group_id, text=info_text, parse_mode="HTML", reply_markup=group_reply_markup)
        else:
            sent_msg = await context.bot.send_photo(chat_id=group_id, photo=photo, caption=user_caption, reply_markup=group_reply_markup)
            asyncio.create_task(delete_photo_after_delay(context, group_id, sent_msg.message_id, 300))
        return True
    except Exception as e:
        logging.error(f"Error in group {group_id}: {e}")
        return False

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in muted_users or user.id in banned_users:
        await notify_muted_user(update, context)
        return

    photo = update.message.photo[-1].file_id
    user_caption = update.message.caption or ""

    group_reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]])

    tasks = [send_to_single_group(context, gid, photo, user, user_caption, group_reply_markup) for gid in list(connected_groups)]
    results = await asyncio.gather(*tasks)
    sent_success = any(results)

    if user.id in user_last_thanks_msg:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_thanks_msg[user.id])
        except: pass

    if sent_success:
        thanks_msg = await update.message.reply_text("✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]]))
        user_last_thanks_msg[user.id] = thanks_msg.message_id

async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in muted_users or user_id in banned_users:
        await notify_muted_user(update, context)
        return
    warning_msg = await update.message.reply_text("⚠️ ലിങ്കുകളോ ടെക്സ്റ്റുകളോ അയക്കാൻ പാടില്ല!")
    await asyncio.sleep(5)
    try:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=warning_msg.message_id)
    except: pass

async def post_init(application):
    asyncio.create_task(self_ping())

def main():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("id", get_id))
    bot_app.add_handler(CommandHandler("mute", mute_user))
    bot_app.add_handler(CommandHandler("unmute", unmute_user))
    
    bot_app.add_handler(CommandHandler("tempmute", temp_mute))
    bot_app.add_handler(CommandHandler("tempban", temp_ban))
    bot_app.add_handler(CommandHandler("warn", warn_user))
    bot_app.add_handler(CommandHandler("unwarn", unwarn_user))

    bot_app.add_handler(ChatMemberHandler(track_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    
    # ഗ്രൂപ്പ് മെസ്സേജുകൾ ഡിലീറ്റ് ചെയ്യാനുള്ള ഹാൻഡ്‌ലർ
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, handle_group_messages))
    
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))
    
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()