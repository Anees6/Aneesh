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
    CallbackQueryHandler,
    filters
)

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- ADMIN / SPECIAL USER CONFIG -----------------
ADMIN_USER_ID = 7965472783

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

# താങ്കൾ നൽകിയ പുതിയ ഗ്രൂപ്പ് ഐഡി ഇവിടെ നൽകിയിരിക്കുന്നു
INFO_ONLY_GROUP_ID = -1003748242203
DEFAULT_GROUP_ID = int(os.environ.get("GROUP_ID", "-100389856732"))

connected_groups = {INFO_ONLY_GROUP_ID, DEFAULT_GROUP_ID}
muted_users = set()
banned_users = set()
user_warnings = {}  # {user_id: count}

user_last_thanks_msg = {}
user_last_mute_warning_msg = {}
user_last_photo = {}  # യൂസർമാർ അയക്കുന്ന അവസാന ഫോട്ടോ സേവ് ചെയ്തു വെക്കാൻ {user_id: photo_file_id}

# സമയം കണക്കാക്കാൻ സഹായിക്കുന്ന ഫങ്ഷൻ (eg: 10m, 2h, 1d)
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

# ----------------- 15 മിനിറ്റിൽ ഓട്ടോമാറ്റിക് മെസ്സേജ് & പിൻ -----------------
async def periodic_pin_message(context: ContextTypes.DEFAULT_TYPE):
    pin_text = (
        "എന്തിനാ ഫസീന ന്റെ അഡ്മിൻസ് സ്ഥാനം മാറ്റിയത് അത് കൊണ്ട് ഈ ഗ്രൂപ്പിൽ ഫോട്ടോസ് ഫോർഡഡ് ആവില്ല \n"
        "കൂടുതൽ ഫോട്ടോ സ് കാണണം എങ്കിൽ മല്ലു ചാറ്റ് വന്നാൽ പിക്സ് ഗ്രൂപ്പ്‌ കാണും"
    )
    while True:
        try:
            sent_msg = await context.bot.send_message(
                chat_id=INFO_ONLY_GROUP_ID,
                text=pin_text
            )
            # മെസ്സേജ് ഗ്രൂപ്പിൽ പിൻ ചെയ്യുന്നു
            await context.bot.pin_chat_message(
                chat_id=INFO_ONLY_GROUP_ID,
                message_id=sent_msg.message_id,
                disable_notification=True
            )
        except Exception as e:
            logging.error(f"Error in periodic_pin_message: {e}")
        
        # 15 മിനിറ്റ് കാത്തിരിക്കുന്നു (900 സെക്കൻഡ്)
        await asyncio.sleep(900)

# ----------------- ഈ ഗ്രൂപ്പിൽ മാത്രം ഫോർവേഡ് ഫോട്ടോകൾ ബ്ലോക്ക് ചെയ്യൽ -----------------
async def handle_group_forwarded_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    
    # 지정 ചെയ്ത ഗ്രൂപ്പിൽ മാത്രമായി പരിശോധിക്കുന്നു
    if update.effective_chat.id == INFO_ONLY_GROUP_ID:
        # ഫോട്ടോ ഫോർവേഡ് ചെയ്തതാണോ എന്ന് പരിശോധിക്കുന്നു
        if msg.forward_date or msg.forward_from or msg.forward_from_chat or msg.forward_sender_name:
            try:
                await msg.delete()
            except Exception as e:
                logging.error(f"Failed to delete forwarded photo in group: {e}")

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
        await update.message.reply_text("⚠️ സമയം തെറ്റാണ്! 10m (മിനിറ്റ്), 1h (മണിക്കൂർ), 1d (ദിവസം) എന്നീ രീതിയിൽ നൽകുക.")
        return

    target_user_id = int(user_input) if user_input.isdigit() else None
    user_mention = f"<a href='tg://user?id={target_user_id}'>User {target_user_id}</a>" if target_user_id else user_input
    
    if target_user_id:
        muted_users.add(target_user_id)

    await update.message.reply_text(f"⏳ {user_input} എന്ന യൂസറെ {duration_str} സമയത്തേക്ക് മ്യൂട്ട് ചെയ്തു!")
    
    broadcast_msg = f"⏳ {user_mention} നിങ്ങളെ {duration_str} സമയത്തേക്ക് താൽക്കാലികമായി Mute ചെയ്തിരിക്കുന്നു! ഈ സമയത്ത് നിങ്ങളുടെ പോസ്റ്റുകൾ വരുന്നതല്ല."
    await broadcast_to_groups(context, broadcast_msg)

    # അൺമ്യൂട്ട് ചെയ്യുന്നതിനുള്ള ടാസ്ക്
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

# /send Command: ഒരു നിശ്ചിത യൂസറുടെ ഫോട്ടോ INFO_ONLY_GROUP_ID ലേക്ക് അയക്കാൻ
async def send_user_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ഉപയോഗിക്കേണ്ട രീതി: /send <User_ID>")
        return

    try:
        target_user_id = int(context.args[0].strip())
    except ValueError:
        await update.message.reply_text("⚠️ കൃത്യമായ User ID നൽകുക.")
        return

    if target_user_id not in user_last_photo:
        await update.message.reply_text(f"❌ User ID <code>{target_user_id}</code> ബോട്ടിന് ഫോട്ടോ ഒന്നും അയച്ചിട്ടില്ല!", parse_mode="HTML")
        return

    photo_file_id = user_last_photo[target_user_id]

    group_reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ])

    try:
        sent_msg = await context.bot.send_photo(
            chat_id=INFO_ONLY_GROUP_ID, 
            photo=photo_file_id, 
            reply_markup=group_reply_markup
        )
        # 5 മിനിറ്റിന് (300 sec) ശേഷം ഫോട്ടോ ഗ്രൂപ്പിൽ നിന്ന് ഡിലീറ്റ് ആകും
        asyncio.create_task(delete_photo_after_delay(context, INFO_ONLY_GROUP_ID, sent_msg.message_id, 300))
        await update.message.reply_text(f"✅ User <code>{target_user_id}</code>-ന്റെ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് വിജയകരമായി അയച്ചു!", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error sending photo via /send command: {e}")
        await update.message.reply_text(f"❌ ഫോട്ടോ അയക്കുന്നതിൽ പിഴവ് സംഭവിച്ചു: {e}")

async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)

async def track_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
            connected_groups.add(chat.id)

async def notify_muted_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in user_last_mute_warning_msg:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_mute_warning_msg[user.id])
        except: pass
    user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    mute_msg = await update.message.reply_text(f"🚫 {user_mention}, അഡ്മിൻ നിങ്ങളെ മ്യൂട്ട്/ബാൻ ആക്കിയിരിക്കുകയാണ്!", parse_mode="HTML")
    user_last_mute_warning_msg[user.id] = mute_msg.message_id

# 'The View' ബട്ടൺ അമർത്തുമ്പോൾ ഫോട്ടോ കാണിക്കാനുള്ള ഫങ്ഷൻ
async def handle_view_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("view_photo_"):
        target_user_id = int(data.split("_")[2])
        if target_user_id in user_last_photo:
            photo_file_id = user_last_photo[target_user_id]
            group_reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
                [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
            ])
            try:
                # ബട്ടൺ ഉള്ള മെസ്സേജിന് റിപ്ലൈ ആയി ഫോട്ടോ അയക്കുന്നു
                sent_msg = await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo_file_id,
                    reply_to_message_id=query.message.message_id,
                    reply_markup=group_reply_markup
                )
                asyncio.create_task(delete_photo_after_delay(context, query.message.chat_id, sent_msg.message_id, 300))
            except Exception as e:
                logging.error(f"Error displaying photo on view click: {e}")
        else:
            await query.message.reply_text("❌ ഈ ഫോട്ടോ ലഭ്യമല്ല അല്ലെങ്കിൽ വാലിഡിറ്റി അവസാനിച്ചു.")

async def send_to_single_group(context, group_id, photo, user, user_caption, group_reply_markup):
    try:
        if group_id == INFO_ONLY_GROUP_ID:
            user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
            info_text = f"📥 <b>New Photo Submitted</b>\n\n👤 <b>Name:</b> {user_mention}\n🆔 <b>User ID:</b> <code>{user.id}</code>\n💬 <b>Caption:</b> {user_caption or 'No Caption'}"
            
            # INFO_ONLY_GROUP_ID -ൽ ചിത്രങ്ങൾക്ക് പകരം "The View" ബട്ടൺ കാണിക്കുന്നു
            view_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("👁️ The View", callback_data=f"view_photo_{user.id}")],
                [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
                [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
            ])
            await context.bot.send_message(chat_id=group_id, text=info_text, parse_mode="HTML", reply_markup=view_markup)
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
    user_last_photo[user.id] = photo  # യൂസറുടെ അവസാന ഫോട്ടോയുടെ ID സേവ് ചെയ്യുന്നു
    
    raw_caption = update.message.caption or ""

    # നിങ്ങളുടെ (ADMIN) ഫോട്ടോ ആണെങ്കിൽ caption മാറ്റമില്ലാതെ അയക്കും
    if user.id == ADMIN_USER_ID:
        user_caption = raw_caption
    else:
        # മറ്റു യൂസർമാരുടെ ഫോട്ടോകളിൽ നിന്ന് Text നീക്കുന്നു
        user_caption = ""

    group_reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ])

    tasks = [send_to_single_group(context, gid, photo, user, user_caption, group_reply_markup) for gid in list(connected_groups)]
    results = await asyncio.gather(*tasks)
    sent_success = any(results)

    if user.id in user_last_thanks_msg:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_thanks_msg[user.id])
        except: pass

    if sent_success:
        thanks_msg = await update.message.reply_text("✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]]))
        user_last_thanks_msg[user.id] = thanks_msg.message_id

# Text/Link കൈകാര്യം ചെയ്യുന്ന ഫങ്ഷൻ
async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if user_id in muted_users or user_id in banned_users:
        await notify_muted_user(update, context)
        return

    # നിങ്ങളുടെ (ADMIN_USER_ID) മെസ്സേജ് ആണെങ്കിൽ എല്ലാ ഗ്രൂപ്പുകളിലേക്കും ബോട്ട് വഴി അയക്കും
    if user_id == ADMIN_USER_ID:
        text_content = update.message.text
        
        group_reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")],
            [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
        ])
        
        tasks = [
            context.bot.send_message(
                chat_id=gid, 
                text=text_content, 
                parse_mode="HTML", 
                reply_markup=group_reply_markup
            ) for gid in list(connected_groups)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        await update.message.reply_text("✅ നിങ്ങളുടെ മെസ്സേജ് എല്ലാ ഗ്രൂപ്പുകളിലേക്കും വിജയകരമായി അയച്ചു!")
        return

    # മറ്റ് യൂസർമാർ ബോട്ട് ഇൻബോക്സിൽ മെസ്സേജ് അയച്ചാൽ ഇൻബോക്സിൽ മാത്രം വാണിംഗ് നൽകും (ഗ്രൂപ്പിലേക്ക് പോകില്ല)
    await update.message.reply_text("⚠️ ടെക്സ്റ്റുകളോ ലിങ്കുകളോ അയക്കാൻ പാടില്ല! ദയവായി ഫോട്ടോകൾ മാത്രം അയക്കുക.")

async def post_init(application):
    asyncio.create_task(self_ping())
    # 15 മിനിറ്റിൽ അയക്കുന്ന ഓട്ടോമാറ്റിക് പിൻ മെസ്സേജ് ടാസ്ക്
    asyncio.create_task(periodic_pin_message(application))

def main():
    t = Thread(target=run_flask, daemon=True)
    t.start()
    bot_app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("id", get_id))
    bot_app.add_handler(CommandHandler("mute", mute_user))
    bot_app.add_handler(CommandHandler("unmute", unmute_user))
    
    # കമാൻഡുകൾ
    bot_app.add_handler(CommandHandler("tempmute", temp_mute))
    bot_app.add_handler(CommandHandler("tempban", temp_ban))
    bot_app.add_handler(CommandHandler("warn", warn_user))
    bot_app.add_handler(CommandHandler("unwarn", unwarn_user))
    bot_app.add_handler(CommandHandler("send", send_user_photo))

    # 'The View' ബട്ടൺ ഹാന്റിൽ ചെയ്യാനുള്ള Callback Handler
    bot_app.add_handler(CallbackQueryHandler(handle_view_button, pattern="^view_photo_"))

    # ഈ ഗ്രൂപ്പിൽ (-1003748242203) ഫോർവേഡ് ചെയ്യുന്ന ഫോട്ടോകൾ ഡിലീറ്റ് ചെയ്യാനുള്ള ഹാന്റ്‌ലർ
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.PHOTO, handle_group_forwarded_photos), group=1)

    bot_app.add_handler(ChatMemberHandler(track_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))
    
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()