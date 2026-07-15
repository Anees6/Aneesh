const functions = require("firebase-functions");
const admin = require("firebase-admin");
const TelegramBot = require("node-telegram-bot-api");

admin.initializeApp();

const db = admin.firestore();

const token = process.env.BOT_TOKEN;

const bot = new TelegramBot(token);

exports.telegramWebhook = functions.https.onRequest(async (req, res) => {
  if (req.method !== "POST") {
    return res.status(200).send("Telegram Bot Running");
  }

  try {
    const update = req.body;

    if (update.message) {
      const msg = update.message;
      const chatId = msg.chat.id;
      const messageId = msg.message_id;

      const isMedia =
        msg.photo ||
        msg.video ||
        msg.document ||
        msg.audio ||
        msg.voice ||
        msg.sticker ||
        msg.animation ||
        msg.video_note;

      if (isMedia) {
        await db.collection("deleteQueue").add({
          chatId,
          messageId,
          createdAt: admin.firestore.FieldValue.serverTimestamp(),
          deleteAfter: Date.now() + (15 * 60 * 1000)
        });
      }
    }

    res.sendStatus(200);
  } catch (e) {
    console.error(e);
    res.sendStatus(500);
  }
});
