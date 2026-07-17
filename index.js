const { Telegraf } = require('telegraf');
const express = require('express');

const app = express();
const PORT = process.env.PORT || 3000;

// Render-ൽ ബോട്ട് എപ്പോഴും ആക്ടീവ് ആയിരിക്കാൻ
app.get('/', (req, res) => {
  res.send('Bot is up and running!');
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

// നിങ്ങളുടെ ടെലിഗ്രാം ബോട്ട് ടോക്കൺ
const bot = new Telegraf('8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4');

// ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ ഉടൻ റെസ്‌പോണ്ട് ചെയ്യാൻ
bot.start((ctx) => {
  ctx.reply('ഹലോ! ഞാൻ റെഡിയാണ്. ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ ഞാൻ അവരെ സ്വാഗതം ചെയ്യും! 🤖');
});

// ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ വെൽക്കം ചെയ്യാൻ
bot.on('new_chat_members', (ctx) => {
  ctx.message.new_chat_members.forEach((user) => {
    if (user.is_bot) return; // ബോട്ട് ആണെങ്കിൽ വെൽക്കം വേണ്ട

    const name = user.first_name;
    ctx.reply(`ഹലോ ${name}, നമ്മുടെ ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 🎉`);
  });
});

// ബോട്ട് റൺ ചെയ്യുക
bot.launch()
  .then(() => console.log('Telegram Bot Status: Active'))
  .catch((err) => console.error('Bot launch error:', err));

// സുരക്ഷിതമായി നിർത്താൻ
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));