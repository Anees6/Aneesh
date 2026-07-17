const { Telegraf } = require('telegraf');
const express = require('express');

// Render-ൽ ബോട്ട് എപ്പോഴും റൺ ചെയ്യാൻ വേണ്ടിയുള്ള വെബ് സെർവർ സെറ്റപ്പ്
const app = express();
const PORT = process.env.PORT || 3000;
app.get('/', (req, res) => res.send('Bot is running!'));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

// ടെലിഗ്രാം ബോട്ട് സെറ്റപ്പ്
const bot = new Telegraf(process.env.BOT_TOKEN);

// ഗ്രൂപ്പിലേക്ക് പുതിയ ആൾക്കാർ വരുമ്പോൾ വെൽക്കം ചെയ്യാനുള്ള ഫങ്ക്ഷൻ
bot.on('new_chat_members', (ctx) => {
    ctx.message.new_chat_members.forEach((member) => {
        // ആളുടെ ഫസ്റ്റ് നെയിം (First Name) എടുക്കുന്നു
        const name = member.first_name;
        
        // ഗ്രൂപ്പിന്റെ പേര് എടുക്കുന്നു
        const groupName = ctx.chat.title;

        // വെൽക്കം മെസ്സേജ് (നിങ്ങൾക്ക് ഇഷ്ടമുള്ള രീതിയിൽ ഇത് മാറ്റാം)
        const welcomeMessage = `ഹലോ ${name}, നമ്മുടെ **${groupName}** ഗ്രൂപ്പിലേക്ക് സ്വാഗതം! 😍✨`;

        // മെസ്സേജ് അയക്കുന്നു
        ctx.reply(welcomeMessage);
    });
});

// ബോട്ട് സ്റ്റാർട്ട് ചെയ്യുന്നു
bot.launch();