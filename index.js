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

// ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ ഉള്ള റെസ്‌പോൺസ്
bot.start((ctx) => {
  ctx.reply('ഹലോ! ഞാൻ റെഡിയാണ്. ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ ഞാൻ അവരെ സ്വാഗതം ചെയ്യും! 🤖');
});

// ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ വെൽക്കം ചെയ്യാനും 1 മിനിറ്റിന് ശേഷം അത് ഡിലീറ്റ് ചെയ്യാനും
bot.on('new_chat_members', async (ctx) => {
  ctx.message.new_chat_members.forEach(async (user) => {
    if (user.is_bot) return; // ബോട്ട് ആണെങ്കിൽ വെൽക്കം ചെയ്യേണ്ടതില്ല

    const userId = user.id;
    const firstName = user.first_name;
    
    // ഉപയോക്താവിനെ മെൻഷൻ ചെയ്യുന്ന രീതിയിലുള്ള വെൽക്കം മെസ്സേജ്
    const welcomeText = `ഹലോ [${firstName}](tg://user?id=${userId}), നമ്മുടെ ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 🎉\n\n` +
                        `⚠️ *ഗ്രൂപ്പ് നിയമം:* ഈ ഗ്രൂപ്പിൽ ലിങ്കുകൾ ഇടാൻ മാത്രമേ സാധിക്കുകയുള്ളൂ. മറ്റു മെസ്സേജുകൾ അയച്ചാൽ ഞങ്ങൾ mute ചെയ്യുന്നതായിരിക്കും.`;

    try {
      // മെസ്സേജ് അയക്കുന്നു (Markdown എനേബിൾ ചെയ്തിട്ടുണ്ട് മെൻഷൻ വർക്ക് ആകാൻ)
      const sentMessage = await ctx.replyWithMarkdown(welcomeText);

      // കൃത്യം 1 മിനിറ്റിന് ശേഷം (60000 മില്ലിസെക്കൻഡ്) ആ മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുക
      setTimeout(async () => {
        try {
          await ctx.telegram.deleteMessage(ctx.chat.id, sentMessage.message_id);
          console.log('Welcome message deleted successfully after 1 minute.');
        } catch (err) {
          console.error('Failed to delete message:', err);
        }
      }, 60000);

    } catch (error) {
      console.error('Error sending welcome message:', error);
    }
  });
});

// ബോട്ട് റൺ ചെയ്യുക
bot.launch()
  .then(() => console.log('Telegram Bot Status: Active'))
  .catch((err) => console.error('Bot launch error:', err));

// സുരക്ഷിതമായി നിർത്താൻ
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));