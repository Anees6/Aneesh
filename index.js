const { Telegraf } = require('telegraf');
const express = require('express');

const app = express();
const PORT = process.env.PORT || 3000;

// Render-ൽ ബോട്ട് ഓഫാകാതിരിക്കാൻ വേണ്ടിയുള്ള വെബ് സെർവർ
app.get('/', (req, res) => {
  res.send('Bot is running perfectly!');
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

// നിങ്ങളുടെ ടെലിഗ്രാം ബോട്ട് ടോക്കൺ
const bot = new Telegraf('8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4');

// /start കമാൻഡ് അടിക്കുമ്പോൾ മറുപടി നൽകാൻ
bot.start((ctx) => {
  ctx.reply('ഹലോ! ഞാൻ സജീവമാണ്. ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ ഞാൻ അവർക്ക് സ്വാഗതം ആശംസിക്കും! 🤖');
});

// പുതിയ ആളുകൾ ഗ്രൂപ്പിൽ വരുമ്പോൾ വെൽക്കം മെസ്സേജ് അയക്കാനുള്ള കോഡ്
bot.on('new_chat_members', (ctx) => {
  ctx.message.new_chat_members.forEach((user) => {
    // ബോട്ട് തന്നെയാണ് ഗ്രൂപ്പിൽ കയറിയതെങ്കിൽ വെൽക്കം പറയേണ്ടതില്ല
    if (user.is_bot) return;

    const name = user.first_name;
    const welcomeMessage = `ഹലോ ${name}, നമ്മുടെ ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 🎉`;
    
    ctx.reply(welcomeMessage);
  });
});

// ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുക
bot.launch()
  .then(() => console.log('Telegram Bot successfully started!'))
  .catch((err) => console.error('Error starting bot:', err));

// ബോട്ട് സുരക്ഷിതമായി നിർത്താൻ
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));