import os
import logging
import asyncio
import re
from threading import Thread
import urllib.request
from flask import Flask
import firebase_admin
from firebase_admin import credentials, db
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

# ----------------- FIREBASE SETUP -----------------
try:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://malluchat-jl7165-default-rtdb.firebaseio.com/'
    })
    logging.info("🔥 Firebase Database വിജയകരമായി കണക്ട് ആയി!")
except Exception as e:
    logging.error(f"❌ Firebase Connection Error: {e}")

# ----------------- ADMIN CONFIG -----------------
ADMIN_USER_ID = 7965472783
NOTIFICATION_ADMIN_ID = 1087968824

# Mute ബട്ടൺ പ്രവർത്തിപ്പിക്കാൻ അനുമതിയുള്ളത് അഡ്മിന് മാത്രം
ALLOWED_ADMINS = {ADMIN_USER_ID}

# ----------------- TARGET GROUP CONFIG -----------------
TARGET_GROUP_ID = -1003898567321

# ----------------- PHOTO TOGGLE FEATURE -----------------
photo_forward_enabled = True  # Default ആയി ON ആയിരിക്കും

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
        logging.error(f"Failed to delete message {message_id} in {chat_id}: {e}")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4")

SPECIFIC_LEAVE_GROUP_ID = -1003748242203

connected_groups = set()
muted_users = set()
banned_users = set()
user_warnings = {}  # {user_id: count}

user_last_thanks_msg = {}
user_last_mute_warning_msg = {}
user_last_photo = {}  # {user_id: photo_file_id}

# മറ്റ് ഗ്രൂപ്പുകളിലെ പഴയ നോട്ടീസ് മെസ്സേജ് ഐഡി സേവ് ചെയ്യാൻ {chat_id: message_id}
last_notice_messages = {}

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

async def broadcast_to_groups(context, text):
    tasks = [context.bot.send_message(chat_id=gid, text=text, parse_mode="HTML") for gid in list(connected_groups)]
    await asyncio.gather(*tasks, return_exceptions=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Firebase-ൽ User വിവരങ്ങൾ സേവ് ചെയ്യുന്നു
    try:
        ref = db.reference(f'users/{user.id}')
        ref.set({
            'name': user.full_name,
            'username': user.username or "None"
        })
    except Exception as e:
        logging.error(f"Firebase-ൽ User ഡാറ്റ നൽകുന്നതിൽ പിഴവ്: {e}")

    await update.message.reply_text("👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക.")

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📌 Chat ID: <code>{update.effective_chat.id}</code>\n👤 Your ID: <code>{update.effective_user.id}</code>", parse_mode="HTML")

# --- ON / OFF COMMANDS FOR PHOTO FORWARDING ---
async def photo_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global photo_forward_enabled
    if update.effective_user.id not in ALLOWED_ADMINS:
        return
    photo_forward_enabled = True
    await update.message.reply_text("🖼️ ഫോട്ടോ ഫോർവേഡിംഗ് **ON** ആക്കിയിരിക്കുന്നു! എല്ലാ ഗ്രൂപ്പുകളിലേക്കും ഫോട്ടോകൾ പോകും.")

async def photo_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global photo_forward_enabled
    if update.effective_user.id not in ALLOWED_ADMINS:
        return
    photo_forward_enabled = False
    await update.message.reply_text("🚫 ഫോട്ടോ ഫോർവേഡിംഗ് **OFF** ആക്കിയിരിക്കുന്നു! ഇനി മെയിൻ ഗ്രൂപ്പിൽ മാത്രം ഫോട്ടോ പോകും, മറ്റു ഗ്രൂപ്പുകളിൽ നോട്ടീസ് കാണിക്കും.")

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
        try: db.reference(f'muted_users/{target_user_id}').set(True)
        except: pass
    
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
            try: db.reference(f'muted_users/{user_to_unmute}').delete()
            except: pass
            await update.message.reply_text(f"🔊 User <code>{user_to_unmute}</code> അൺ-മ്യൂട്ട് ചെയ്തിരിക്കുന്നു!", parse_mode="HTML")
        if user_to_unmute in banned_users:
            banned_users.remove(user_to_unmute)
    except ValueError: pass

# Temporary Mute Command
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

# Temporary Ban Command
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

# Warning Command
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

# Reset Warning
async def unwarn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return
    try:
        user_id = int(context.args[0])
        user_warnings[user_id] = 0
        await update.message.reply_text(f"✅ User {user_id}-ന്റെ വാണിംഗുകൾ 0 ആക്കി മാറ്റിയിട്ടുണ്ട്.")
    except ValueError: pass

# /send Command
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
        [InlineKeyboardButton("🔇 Mute User", callback_data=f"pm_mute_user_{target_user_id}")],
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ])

    try:
        sent_msg = await context.bot.send_photo(
            chat_id=TARGET_GROUP_ID, 
            photo=photo_file_id, 
            reply_markup=group_reply_markup
        )
        asyncio.create_task(delete_photo_after_delay(context, TARGET_GROUP_ID, sent_msg.message_id, 300))
        await update.message.reply_text(f"✅ User <code>{target_user_id}</code>-ന്റെ ഫോട്ടോ ഗ്രൂപ്പിലേക്ക് വിജയകരമായി അയച്ചു!", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error sending photo via /send command: {e}")
        await update.message.reply_text("❌ ഫോട്ടോ അയക്കുന്നതിൽ പിഴവ് സംഭവിച്ചു.")

async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if chat.id == SPECIFIC_LEAVE_GROUP_ID:
            try:
                await context.bot.leave_chat(chat_id=SPECIFIC_LEAVE_GROUP_ID)
            except Exception as e:
                logging.error(f"Error leaving group: {e}")
        else:
            connected_groups.add(chat.id)

async def track_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat and chat.type in ["group", "supergroup"]:
        if chat.id == SPECIFIC_LEAVE_GROUP_ID:
            try:
                await context.bot.leave_chat(chat_id=SPECIFIC_LEAVE_GROUP_ID)
            except Exception as e:
                logging.error(f"Error leaving group on join: {e}")
        elif update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
            connected_groups.add(chat.id)

async def notify_muted_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in user_last_mute_warning_msg:
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_mute_warning_msg[user.id])
        except: pass
    user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    mute_msg = await update.message.reply_text(f"🚫 {user_mention}, അഡ്മിൻ നിങ്ങളെ മ്യൂട്ട്/ബാൻ ആക്കിയിരിക്കുകയാണ്!", parse_mode="HTML")
    user_last_mute_warning_msg[user.id] = mute_msg.message_id

# ----------------- CALLBACK QUERY HANDLER (INSTANT MUTE ACTION) -----------------
async def handle_button_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clicker_id = query.from_user.id

    if clicker_id not in ALLOWED_ADMINS:
        return

    data = query.data

    if data.startswith("pm_mute_user_"):
        target_user_id = int(data.split("_")[3])
        muted_users.add(target_user_id)
        
        try: db.reference(f'muted_users/{target_user_id}').set(True)
        except: pass

        await query.answer(f"⚡ User {target_user_id} തൽക്ഷണം Mute ആക്കപ്പെട്ടു!", show_alert=True)
        
        new_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔊 Unmute User", callback_data=f"pm_unmute_user_{target_user_id}")],
            [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
            [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
        ])
        
        try:
            await query.edit_message_reply_markup(reply_markup=new_markup)
        except Exception as e:
            logging.error(f"Failed to edit markup: {e}")

    elif data.startswith("pm_unmute_user_"):
        target_user_id = int(data.split("_")[3])
        if target_user_id in muted_users:
            muted_users.remove(target_user_id)
            try: db.reference(f'muted_users/{target_user_id}').delete()
            except: pass
            
        await query.answer(f"🔊 User {target_user_id} Unmute ആക്കി!", show_alert=True)
            
        new_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔇 Mute User", callback_data=f"pm_mute_user_{target_user_id}")],
            [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
            [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
        ])
        
        try:
            await query.edit_message_reply_markup(reply_markup=new_markup)
        except Exception as e:
            logging.error(f"Failed to edit markup: {e}")

async def send_photo_to_group(context, group_id, photo_file_id, group_reply_markup, caption=None):
    if group_id == SPECIFIC_LEAVE_GROUP_ID:
        try:
            await context.bot.leave_chat(chat_id=SPECIFIC_LEAVE_GROUP_ID)
        except:
            pass
        return False

    try:
        sent_msg = await context.bot.send_photo(
            chat_id=group_id, 
            photo=photo_file_id, 
            caption=caption,
            reply_markup=group_reply_markup
        )
        asyncio.create_task(delete_photo_after_delay(context, group_id, sent_msg.message_id, 300))
        return True
    except Exception as e:
        logging.error(f"Error sending photo to group {group_id}: {e}")
        return False

# ------------------ FAST FORWARD PROCESS ------------------
async def process_photo_broadcast(context, user, photo, caption=None):
    # Firebase-ൽ ലോഗ് ഉണ്ടാക്കുന്നു
    try:
        db.reference('photo_logs').push({
            'user_id': user.id,
            'user_name': user.full_name,
            'file_id': photo,
            'caption': caption
        })
    except Exception as e:
        logging.error(f"Firebase photo log error: {e}")

    photo_reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔇 Mute User", callback_data=f"pm_mute_user_{user.id}")],
        [InlineKeyboardButton("🕵️ Anonymously Post", url="https://t.me/Faseena5bot")], 
        [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
    ])

    await send_photo_to_group(context, TARGET_GROUP_ID, photo, photo_reply_markup, caption=caption)

    if photo_forward_enabled:
        tasks = [
            send_photo_to_group(context, gid, photo, photo_reply_markup, caption=caption)
            for gid in list(connected_groups)
            if gid != TARGET_GROUP_ID and gid != SPECIFIC_LEAVE_GROUP_ID
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    else:
        other_group_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]
        ])
        other_msg = "ഇനി മുതൽ എനിക്ക് അയക്കുന്ന ഫോട്ടോസ് ഈ ഗ്രൂപ്പിൽ കാണിക്കില്ല കാണണം എങ്കിൽ മല്ലു ചാറ്റ് ഗ്രൂപ്പിൽ വന്നാൽ പിക് ഗ്രൂപ്പ്‌ ലിങ്ക് കാണാം"

        async def send_notice(gid):
            try:
                if gid in last_notice_messages:
                    try:
                        await context.bot.delete_message(chat_id=gid, message_id=last_notice_messages[gid])
                    except Exception:
                        pass

                sent_notice = await context.bot.send_message(chat_id=gid, text=other_msg, reply_markup=other_group_markup)
                last_notice_messages[gid] = sent_notice.message_id
            except Exception as e:
                logging.error(f"Failed to send redirect message to {gid}: {e}")

        notice_tasks = [
            send_notice(gid) 
            for gid in list(connected_groups) 
            if gid != TARGET_GROUP_ID and gid != SPECIFIC_LEAVE_GROUP_ID
        ]
        if notice_tasks:
            await asyncio.gather(*notice_tasks, return_exceptions=True)

    try:
        user_mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
        pm_notice_caption = f"📥 <b>New Photo Submitted</b>\n\n👤 <b>Sender:</b> {user_mention}\n🆔 <b>User ID:</b> <code>{user.id}</code>"
        if caption:
            pm_notice_caption += f"\n📝 <b>Caption:</b> {caption}"

        admin_mute_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔇 Mute User", callback_data=f"pm_mute_user_{user.id}")]
        ])
        
        await context.bot.send_photo(
            chat_id=NOTIFICATION_ADMIN_ID,
            photo=photo,
            caption=pm_notice_caption,
            parse_mode="HTML",
            reply_markup=admin_mute_markup
        )
    except Exception as e:
        logging.error(f"Failed to send notification to admin {NOTIFICATION_ADMIN_ID}: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id in muted_users or user.id in banned_users:
        await notify_muted_user(update, context)
        return

    # message.photo അല്ലെങ്കിൽ channel_post വഴി വരുന്ന ഫോട്ടോയും ക്യാപ്ഷനും ശരിയായി എടുക്കുന്നു
    msg = update.message or update.channel_post
    if not msg or not msg.photo:
        return

    photo = msg.photo[-1].file_id
    caption = msg.caption if msg.caption else None

    # ലിങ്ക് അടങ്ങിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുന്നു (http, https, t.me, www മുതലായവ)
    link_pattern = r"(https?://|www\.|t\.me/)"
    if caption and re.search(link_pattern, caption, re.IGNORECASE):
        try:
            await msg.delete()
        except Exception:
            pass
            
        # ലിങ്ക് ഉണ്ടെങ്കിൽ ഫോർവേഡ് ചെയ്യില്ല; യൂസർക്ക് നോട്ടിഫിക്കേഷൻ അയക്കുന്നു (Mute/Warn ചെയ്യില്ല)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ ഫോട്ടോയുടെ കൂടെ ലിങ്കുകൾ അയക്കാൻ പാടില്ല! അതിനാൽ ഈ ഫോട്ടോ ഫോർവേഡ് ചെയ്യുന്നതല്ല.",
            parse_mode="HTML"
        )
        return
    
    try:
        await msg.delete()
    except Exception as e:
        logging.error(f"Failed to delete PM photo: {e}")

    user_last_photo[user.id] = photo

    if user.id in user_last_thanks_msg:
        try: 
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=user_last_thanks_msg[user.id])
        except: 
            pass

    thanks_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ വിജയകരമായി അയച്ചിട്ടുണ്ട്!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("മല്ലു ചാറ്റ്", url="https://t.me/+-KKPdBquED1lOTZl")]])
    )
    user_last_thanks_msg[user.id] = thanks_msg.message_id

    asyncio.create_task(process_photo_broadcast(context, user, photo, caption=caption))

async def handle_text_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if user_id in muted_users or user_id in banned_users:
        await notify_muted_user(update, context)
        return

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
            ) for gid in list(connected_groups) if gid != SPECIFIC_LEAVE_GROUP_ID
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        await update.message.reply_text("✅ നിങ്ങളുടെ മെസ്സേജ് എല്ലാ ഗ്രൂപ്പുകളിലേക്കും വിജയകരമായി അയച്ചു!")
        return

    await update.message.reply_text("⚠️ ടെക്സ്റ്റുകളോ ലിങ്കുകളോ അയക്കാൻ പാടില്ല! ദയവായി ഫോട്ടോകൾ മാത്രം അയക്കുക.")

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
    bot_app.add_handler(CommandHandler("send", send_user_photo))

    bot_app.add_handler(CommandHandler("photoon", photo_on))
    bot_app.add_handler(CommandHandler("photooff", photo_off))

    bot_app.add_handler(CallbackQueryHandler(handle_button_clicks))

    bot_app.add_handler(ChatMemberHandler(track_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
    bot_app.add_handler(MessageHandler(filters.ChatType.GROUPS, track_groups))

    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.PHOTO & ~filters.COMMAND, handle_text_or_link))
    
    bot_app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()