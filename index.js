const { Telegraf } = require('telegraf');
const express = require('express');

const app = express();
const PORT = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('Bot is up and running!');
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

const bot = new Telegraf('8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4');

// ഓൺ/ഓഫ് സെറ്റിങ്സ് സൂക്ഷിക്കാൻ (ഡിഫോൾട്ട് ആയി ഓൺ ആണ്)
let welcomeEnabled = true;
let autoCleanEnabled = true;

bot.start((ctx) => {
  ctx.reply('ഹലോ! ഞാൻ റെഡിയാണ്. ഗ്രൂപ്പിൽ പുതിയ ആളുകൾ വരുമ്പോൾ ഞാൻ അവരെ സ്വാഗതം ചെയ്യും! 🤖');
});

// വെൽക്കം മെസ്സേജ് കൺട്രോൾ ചെയ്യാൻ (/new on / off)
bot.command('new', (ctx) => {
  const text = ctx.message.text.split(' ')[1];
  if (text === 'on') {
    welcomeEnabled = true;
    ctx.reply('✅ പുതിയ ആളുകൾ വരുമ്പോൾ സ്വാഗതം ചെയ്യുന്ന ഫീച്ചർ ഓൺ ആക്കിയിരിക്കുന്നു!');
  } else if (text === 'off') {
    welcomeEnabled = false;
    ctx.reply('❌ പുതിയ ആളുകൾ വരുമ്പോൾ സ്വാഗതം ചെയ്യുന്ന ഫീച്ചർ ഓഫ് ആക്കിയിരിക്കുന്നു!');
  } else {
    ctx.reply('ശരിയായ കമാൻഡ്:\n• `/new on`\n• `/new off`', { parse_mode: 'Markdown' });
  }
});

// മീഡിയ/ലിങ്ക് ഡിലീറ്റിംഗ് കൺട്രോൾ ചെയ്യാൻ (/clean on / off)
bot.command('clean', (ctx) => {
  const text = ctx.message.text.split(' ')[1];
  if (text === 'on') {
    autoCleanEnabled = true;
    ctx.reply('✅ ഗ്രൂപ്പിലെ ലിങ്കുകളും മീഡിയകളും 15 മിനിറ്റിന് ശേഷം സ്വയം ഡിലീറ്റ് ചെയ്യുന്ന ഫീച്ചർ ഓൺ ആക്കിയിരിക്കുന്നു!');
  } else if (text === 'off') {
    autoCleanEnabled = false;
    ctx.reply('❌ ഓട്ടോമാറ്റിക് ഡിലീറ്റിംഗ് ഫീച്ചർ ഓഫ് ആക്കിയിരിക്കുന്നു!');
  } else {
    ctx.reply('ശരിയായ കമാൻഡ്:\n• `/clean on`\n• `/clean off`', { parse_mode: 'Markdown' });
  }
});

// പുതിയ ആളുകൾ ഗ്രൂപ്പിൽ വരുമ്പോൾ
bot.on('new_chat_members', async (ctx) => {
  if (!welcomeEnabled) return;

  ctx.message.new_chat_members.forEach(async (user) => {
    if (user.is_bot) return;

    const userId = user.id;
    const firstName = user.first_name;
    const welcomeText = `ഹലോ [${firstName}](tg://user?id=${userId}), നമ്മുടെ ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 🎉\n\n` +
                        `⚠️ *ഗ്രൂപ്പ് നിയമം:* ഈ ഗ്രൂപ്പിൽ ലിങ്കുകൾ ഇടാൻ മാത്രമേ സാധിക്കുകയുള്ളൂ. മറ്റു മെസ്സേജുകൾ അയച്ചാൽ ഞങ്ങൾ mute ചെയ്യുന്നതായിരിക്കും.`;

    try {
      const sentMessage = await ctx.replyWithMarkdown(welcomeText);

      // 1 മിനിറ്റിന് ശേഷം വെൽക്കം മെസ്സേജ് ഡിലീറ്റ് ചെയ്യും
      setTimeout(async () => {
        try {
          await ctx.telegram.deleteMessage(ctx.chat.id, sentMessage.message_id);
        } catch (err) {
          console.error('Failed to delete welcome message:', err);
        }
      }, 60000);

    } catch (error) {
      console.error('Error sending welcome message:', error);
    }
  });
});

// ഗ്രൂപ്പിൽ വരുന്ന മറ്റെല്ലാ മെസ്സേജുകളും പരിശോധിക്കാൻ
bot.on('message', async (ctx) => {
  if (!autoCleanEnabled) return; // ഫീച്ചർ ഓഫ് ആണെങ്കിൽ ഒന്നും ചെയ്യേണ്ട

  const message = ctx.message;
  let shouldDelete = false;

  // 1. ലിങ്കുകൾ ഉണ്ടോ എന്ന് നോക്കുന്നു
  if (message.entities) {
    const hasLink = message.entities.some(entity => entity.type === 'url' || entity.type === 'text_link');
    if (hasLink) shouldDelete = true;
  }

  // 2. മീഡിയ ഫയലുകൾ (ഫോട്ടോ, വീഡിയോ, ഓഡിയോ, ഡോക്യുമെന്റ്, വോയ്സ്) ഉണ്ടോ എന്ന് നോക്കുന്നു
  if (
    message.photo || 
    message.video || 
    message.document || 
    message.audio || 
    message.voice || 
    message.video_note ||
    message.sticker
  ) {
    shouldDelete = true;
  }

  // മീഡിയയോ ലിങ്കോ ആണെങ്കിൽ 15 മിനിറ്റിന് ശേഷം ഡിലീറ്റ് ചെയ്യുക
  if (shouldDelete) {
    const chatId = ctx.chat.id;
    const messageId = message.message_id;

    // 15 മിനിറ്റ് = 15 * 60 * 1000 = 900,000 മില്ലിസെക്കൻഡ്
    setTimeout(async () => {
      try {
        await ctx.telegram.deleteMessage(chatId, messageId);
        console.log(`Deleted media/link message ${messageId} after 15 minutes.`);
      } catch (err) {
        console.error(`Failed to delete message ${messageId}:`, err);
      }
    }, 900000);
  }
});

bot.launch()
  .then(() => console.log('Telegram Bot Status: Active'))
  .catch((err) => console.error('Bot launch error:', err));

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));