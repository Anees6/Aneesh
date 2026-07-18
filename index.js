const express = require('express');
const { Bot, GrammyError, HttpError } = require('grammy');

// --- EXPRESS WEB SERVER SETUP (FOR HOSTING) ---
const app = express();
const PORT = process.env.PORT || 8080;
app.get('/', (req, res) => res.send("Bot is running successfully!"));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

// --- TELEGRAM BOT SETUP ---
const TOKEN = "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4";
const bot = new Bot(TOKEN);

// ഡാറ്റ സൂക്ഷിക്കാനുള്ള ഗ്ലോബൽ വേരിയബിളുകൾ
let lastWarningMessageId = null;
let lastWelcomeMessageId = null;
let antilinkStatus = true; // ആന്റി-ലിങ്ക് ഫീച്ചർ ഓൺ/ഓഫ് ചെയ്യാൻ
const userWarnings = {}; // യൂസർമാരുടെ വാണിംഗ് കൗണ്ട് സൂക്ഷിക്കാൻ { userId: count }

// അഡ്മിൻ ആണോ എന്ന് പരിശോധിക്കാനുള്ള ഫങ്ഷൻ
async function isAdmin(ctx) {
    if (ctx.chat.type === 'private') return false;
    try {
        const member = await ctx.getChatMember(ctx.from.id);
        return ['creator', 'administrator'].includes(member.status);
    } catch (e) {
        return false;
    }
}

// --- 1. START COMMAND (ALL COMMANDS LIST) ---
bot.command('start', async (ctx) => {
    await ctx.reply(
        "👋 Hello! I am your Advanced Group Management Bot.\n\n" +
        "📜 **Available Commands (Reply to a user's message):**\n" +
        "🔹 `/ban` - Ban a user from the group\n" +
        "🔹 `/unban [user_id]` - Unban a user\n" +
        "🔹 `/kick` - Kick a user out\n" +
        "🔹 `/mute` - Mute a user permanently\n" +
        "🔹 `/tmute [minutes]` - Mute for a specific time (e.g., `/tmute 10`)\n" +
        "🔹 `/unmute` - Unmute a user\n" +
        "🔹 `/warn` - Give a warning (3 warnings = Automatic Mute)\n" +
        "🔹 `/resetwarn` - Reset a user's warnings\n\n" +
        "⚙️ **Admin Configuration:**\n" +
        "🔹 `/antilink on` - Delete all messages except links\n" +
        "🔹 `/antilink off` - Allow all messages"
    );
});

// --- 2. BAN COMMAND ---
bot.command('ban', async (ctx) => {
    if (!await isAdmin(ctx)) return ctx.reply("❌ You do not have permission to use this command!");
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the message of the user you want to ban.");
    
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        await ctx.reply(`🔒 <b>${user.first_name}</b> has been banned from the group.`, { parse_mode: "HTML" });
    } catch (err) {
        await ctx.reply(`❌ Failed to ban: ${err.message}`);
    }
});

// --- 3. UNBAN COMMAND ---
bot.command('unban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const userId = parseInt(ctx.match);
    if (isNaN(userId)) return ctx.reply("⚠️ Usage: `/unban [user_id]`");

    try {
        await ctx.unbanChatMember(userId);
        await ctx.reply(`✅ User (ID: ${userId}) has been unbanned.`);
    } catch (err) {
        await ctx.reply(`❌ Failed to unban: ${err.message}`);
    }
});

// --- 4. KICK COMMAND ---
bot.command('kick', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user you want to kick.");

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        await ctx.unbanChatMember(user.id);
        await ctx.reply(`🏃 <b>${user.first_name}</b> has been kicked out.`, { parse_mode: "HTML" });
    } catch (err) {
        await ctx.reply(`❌ Failed to kick: ${err.message}`);
    }
});

// --- 5. PERMANENT MUTE ---
bot.command('mute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user you want to mute.");

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false });
        await ctx.reply(`🔇 <b>${user.first_name}</b> has been muted permanently.`, { parse_mode: "HTML" });
    } catch (err) {
        await ctx.reply(`❌ Failed to mute: ${err.message}`);
    }
});

// --- 6. TEMPORARY MUTE (ടൈം സെറ്റ് ചെയ്യാൻ) ---
bot.command('tmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user you want to temporary mute.");
    
    const minutes = parseInt(ctx.match);
    if (isNaN(minutes) || minutes <= 0) return ctx.reply("⚠️ Please specify minutes. Example: `/tmute 10`");

    const user = ctx.message.reply_to_message.from;
    const untilTime = Math.floor(Date.now() / 1000) + minutes * 60;

    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false }, { until_date: untilTime });
        await ctx.reply(`⏳ <b>${user.first_name}</b> has been muted for <b>${minutes} minutes</b>.`, { parse_mode: "HTML" });
    } catch (err) {
        await ctx.reply(`❌ Failed to temporary mute: ${err.message}`);
    }
});

// --- 7. UNMUTE COMMAND ---
bot.command('unmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user you want to unmute.");

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, {
            can_send_messages: true,
            can_send_audios: true,
            can_send_documents: true,
            can_send_photos: true,
            can_send_videos: true,
            can_send_video_notes: true,
            can_send_voice_notes: true,
            can_send_polls: true,
            can_send_other_messages: true,
            can_add_web_page_previews: true
        });
        await ctx.reply(`🔊 <b>${user.first_name}</b> has been unmuted.`, { parse_mode: "HTML" });
    } catch (err) {
        await ctx.reply(`❌ Failed to unmute: ${err.message}`);
    }
});

// --- 8. WARNING SYSTEM (Max 3 Warnings -> Auto Mute) ---
bot.command('warn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user you want to warn.");

    const user = ctx.message.reply_to_message.from;
    
    // വാണിംഗ് കൗണ്ട് കൂട്ടുന്നു
    if (!userWarnings[user.id]) userWarnings[user.id] = 0;
    userWarnings[user.id] += 1;

    if (userWarnings[user.id] >= 3) {
        // 3 വാണിംഗ് ആയാൽ ഓട്ടോമാറ്റിക് മ്യൂട്ട് ചെയ്യും
        try {
            await ctx.restrictChatMember(user.id, { can_send_messages: false });
            userWarnings[user.id] = 0; // കൗണ്ട് റീസെറ്റ് ചെയ്യുന്നു
            await ctx.reply(`🚷 <b>${user.first_name}</b> reached 3 warnings and has been <b>MUTED</b> automatically.`, { parse_mode: "HTML" });
        } catch (e) {
            await ctx.reply(`❌ Failed to auto-mute user: ${e.message}`);
        }
    } else {
        await ctx.reply(`⚠️ <b>${user.first_name}</b> has been warned. (${userWarnings[user.id]}/3)`, { parse_mode: "HTML" });
    }
});

// വാണിംഗ് കൗണ്ട് റീസെറ്റ് ചെയ്യാനുള്ള കമാൻഡ്
bot.command('resetwarn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Please reply to the user to reset warnings.");
    
    const user = ctx.message.reply_to_message.from;
    userWarnings[user.id] = 0;
    await ctx.reply(`✅ Warnings reset for <b>${user.first_name}</b>.`, { parse_mode: "HTML" });
});

// --- 9. ANTILINK TOGGLE COMMAND ---
bot.command('antilink', async (ctx) => {
    if (!await isAdmin(ctx)) return ctx.reply("❌ You do not have permission!");
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    
    if (args === 'on') {
        antilinkStatus = true;
        await ctx.reply("✅ Anti-link system enabled! Only links are allowed.");
    } else if (args === 'off') {
        antilinkStatus = false;
        await ctx.reply("🛑 Anti-link system disabled! All messages allowed.");
    } else {
        await ctx.reply("⚠️ Usage: `/antilink on` or `/antilink off`");
    }
});

// --- 10. WELCOME NEW MEMBERS ---
bot.on('message:new_chat_members', async (ctx) => {
    for (const newMember of ctx.message.new_chat_members) {
        if (newMember.id === ctx.me.id) continue;
        try {
            if (lastWelcomeMessageId !== null) {
                try { await ctx.api.deleteMessage(ctx.chat.id, lastWelcomeMessageId); } catch (e) {}
            }
            const welcomeText = `👋 Hello <a href="tg://user?id=${newMember.id}">${newMember.first_name}</a>, welcome to our group!`;
            const sentMessage = await ctx.reply(welcomeText, { parse_mode: "HTML" });
            lastWelcomeMessageId = sentMessage.message_id;
        } catch (err) {
            console.error(err);
        }
    }
});

// --- 11. HANDLE MESSAGES (DELETE NON-LINKS IF ANTILINK IS ON) ---
bot.on('message:text', async (ctx) => {
    if (!antilinkStatus) return;
    if (await isAdmin(ctx)) return;

    const entities = ctx.message.entities || [];
    const hasLink = entities.some(e => e.type === 'url' || e.type === 'text_link');
    if (hasLink) return;

    try {
        await ctx.deleteMessage(); // മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു
        
        if (lastWarningMessageId !== null) {
            try { await ctx.api.deleteMessage(ctx.chat.id, lastWarningMessageId); } catch (e) {}
        }

        const warningText = `⚠️ <a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, only links are allowed in this group!`;
        const sentMessage = await ctx.reply(warningText, { parse_mode: "HTML" });
        lastWarningMessageId = sentMessage.message_id;
    } catch (err) {
        console.error(err);
    }
});

// Error handling
bot.catch((err) => {
    console.error(`Error in bot execution: ${err.error.message}`);
});

console.log("Bot is starting...");
bot.start();