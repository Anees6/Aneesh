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

// വെൽക്കം മെസ്സേജ് ഓൺ ആണോ ഓഫ് ആണോ എന്ന് നോക്കാൻ (ഡിഫോൾട്ട് ആയി ON ആണ്)
let welcomeEnabled = true;

// ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുമ്പോൾ ഉള്ള റെസ്‌പോൺസ്
bot.start((ctx) => {
  ctx.reply('ഹലോ! ഞാൻ റെഡിയാണ്. ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ ഞാൻ അവരെ സ്വാഗതം ചെയ്യും! 🤖');
});

// വെൽക്കം മെസ്സേജ് ഓൺ ആക്കാനുള്ള കമാൻഡ് (/new on)
bot.command('new', (ctx) => {
  const text = ctx.message.text.split(' ')[1]; // കമാൻഡിന് ശേഷമുള്ള വാക്ക് എടുക്കുന്നു (on അല്ലെങ്കിൽ off)

  if (text === 'on') {
    welcomeEnabled = true;
    ctx.reply('✅ പുതിയ ആളുകൾ വരുമ്പോൾ സ്വാഗതം ചെയ്യുന്ന ഫീച്ചർ ഓൺ ആക്കിയിരിക്കുന്നു!');
  } else if (text === 'off') {
    welcomeEnabled = false;
    ctx.reply('❌ പുതിയ ആളുകൾ വരുമ്പോൾ സ്വാഗതം ചെയ്യുന്ന ഫീച്ചർ ഓഫ് ആക്കിയിരിക്കുന്നു!');
  } else {
    ctx.reply('ശരിയായ കമാൻഡ് ഉപയോഗിക്കുക:\n• ഓൺ ചെയ്യാൻ: `/new on`\n• ഓഫ് ചെയ്യാൻ: `/new off`', { parse_mode: 'Markdown' });
  }
});

// ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ
bot.on('new_chat_members', async (ctx) => {
  // വെൽക്കം ഫീച്ചർ ഓഫ് ആണെങ്കിൽ ഒന്നും ചെയ്യേണ്ടതില്ല
  if (!welcomeEnabled) return;

  ctx.message.new_chat_members.forEach(async (user) => {
    if (user.is_bot) return; // ബോട്ട് ആണെങ്കിൽ വെൽക്കം ചെയ്യേണ്ടതില്ല

    const userId = user.id;
    const firstName = user.first_name;
    
    // ഉപയോക്താവിനെ മെൻഷൻ ചെയ്യുന്ന വെൽക്കം മെസ്സേജ്
    const welcomeText = `ഹലോ [${firstName}](tg://user?id=${userId}), നമ്മുടെ ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 🎉\n\n` +
                        `⚠️ *ഗ്രൂപ്പ് നിയമം:* ഈ ഗ്രൂപ്പിൽ ലിങ്കുകൾ ഇടാൻ മാത്രമേ സാധിക്കുകയുള്ളൂ. മറ്റു മെസ്സേജുകൾ അയച്ചാൽ ഞങ്ങൾ mute ചെയ്യുന്നതായിരിക്കും.`;

    try {
      // മെസ്സേജ് അയക്കുന്നു
      const sentMessage = await ctx.replyWithMarkdown(welcomeText);

      // കൃത്യം 1 മിനിറ്റിന് ശേഷം (60000 മില്ലിസെക്കൻഡ്) ആ മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുക
      setTimeout(async () => {
        try {
          await ctx.telegram.deleteMessage(ctx.chat.id, sentMessage.message_id);
          console.log('Welcome message deleted after 1 minute.');
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