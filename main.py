import os
import logging
import asyncio
from threading import Thread
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
    return "Bot is Running Live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# -----------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")

DEFAULT_GROUP_ID = int(
    os.environ.get("GROUP_ID", "-100389856732")
)

# പേര് / username കാണിക്കേണ്ട പ്രത്യേക ഗ്രൂപ്പ്
NAME_GROUP_ID = -1004376973168

connected_groups = {DEFAULT_GROUP_ID}


# /start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 നമസ്കാരം! ദയവായി നിങ്ങളുടെ ഫോട്ടോകൾ മാത്രം അയക്കുക. "
        "ടെക്സ്റ്റോ ലിങ്കുകളോ അനുവദനീയമല്ല."
    )


# ഗ്രൂപ്പ് ഐഡി ട്രാക്ക് ചെയ്യാൻ
async def track_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat and update.effective_chat.type in ["group", "supergroup"]:
        connected_groups.add(update.effective_chat.id)


# ഫോട്ടോകൾ മാത്രം ഗ്രൂപ്പിലേക്ക് അയക്കുന്നു
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1].file_id
    original_caption = update.message.caption or ""

    user = update.effective_user

    # ---------------- USER NAME / USERNAME ----------------

    if user:

        first_name = user.first_name or ""
        last_name = user.last_name or ""

        full_name = f"{first_name} {last_name}".strip()

        if user.username:
            user_info = f"👤 {full_name}\n🔗 @{user.username}"
        else:
            user_info = f"👤 {full_name}"

    else:
        user_info = "👤 Unknown User"

    # @Faseena5bot ലേക്ക് റീഡയറക്ട് ചെയ്യുന്ന URL ബട്ടൺ
    keyboard = [
        [
            InlineKeyboardButton(
                "🕵️ Anonymously Post",
                url="https://t.me/Faseena5bot"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    sent_success = False

    # ---------------- SEND TO GROUPS ----------------

    for group_id in list(connected_groups):

        try:

            # പ്രത്യേക ഗ്രൂപ്പിൽ മാത്രം Name / Username കാണിക്കും
            if group_id == NAME_GROUP_ID:

                if original_caption:
                    final_caption = f"{user_info}\n\n{original_caption}"
                else:
                    final_caption = user_info

            else:

                # മറ്റ് ഗ്രൂപ്പുകളിൽ Name / Username ചേർക്കില്ല
                final_caption = original_caption

            await context.bot.send_photo(
                chat_id=group_id,
                photo=photo,
                caption=final_caption,
                reply_markup=reply_markup
            )

            sent_success = True

        except Exception as e:

            logging.error(
                f"Error sending photo to {group_id}: {e}"
            )

    if sent_success:

        await update.message.reply_text(
            "✅ ഫോട്ടോ വിജയകരമായി ഗ്രൂപ്പിലേക്ക് അയച്ചിട്ടുണ്ട്!"
        )

    else:

        await update.message.reply_text(
            "⚠️ ഫോട്ടോ അയക്കാൻ കഴിഞ്ഞില്ല! "
            "ബോട്ടിന് ഗ്രൂപ്പിൽ Admin Permission നൽകിയിട്ടുണ്ടോ എന്ന് പരിശോധിക്കുക."
        )


# ടെക്സ്റ്റോ ലിങ്കുകളോ വന്നാൽ ഡിലീറ്റ് ചെയ്യും
async def handle_text_or_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        warning_msg = await update.message.reply_text(
            "⚠️ ലിങ്കുകളോ ടെക്സ്റ്റുകളോ അയക്കാൻ പാടില്ല! "
            "ഫോട്ടോകൾ മാത്രം അയക്കുക."
        )

        await asyncio.sleep(5)

        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=warning_msg.message_id
        )

    except Exception as e:

        logging.error(
            f"Error handling text/link: {e}"
        )


def main():

    # Flask സർവർ ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യുന്നു
    t = Thread(
        target=run_flask,
        daemon=True
    )

    t.start()

    bot_app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    bot_app.add_handler(
        CommandHandler("start", start)
    )

    bot_app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS,
            track_groups
        )
    )

    bot_app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.PHOTO,
            handle_photo
        )
    )

    bot_app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE
            & ~filters.PHOTO
            & ~filters.COMMAND,
            handle_text_or_link
        )
    )

    print("Bot is starting...")

    bot_app.run_polling(
        drop_pending_updates=True
    )


if __name__ == '__main__':
    main()