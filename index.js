const express = require('express');
const { Bot, InlineKeyboard, GrammyError, HttpError } = require('grammy');

// --- WEB SERVER FOR HOSTING ---
const app = express();
const PORT = process.env.PORT || 8080;
app.get('/', (req, res) => res.send("Rose-Style Management Bot is running!"));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

// --- BOT SETUP ---
const TOKEN = "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4";
const bot = new Bot(TOKEN);

// Global Variables
let lastWarningMessageId = null;
let lastWelcomeMessageId = null;
let antilinkStatus = true;
let autodelStatus = true; // ലിങ്ക് ഓട്ടോ ഡിലീറ്റ് ചെയ്യാനുള്ള സ്റ്റാറ്റസ് (Default: true)
const userWarnings = {};

// 15 സെക്കൻഡിന് ശേഷം മെസ്സേജ് ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ
function deleteAfter15Seconds(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {
            // മെസ്സേജ് നേരത്തെ ഡിലീറ്റ് ചെയ്യപ്പെടുകയോ ബോട്ടിന് പെർമിഷൻ ഇല്ലാതിരിക്കുകയോ ചെയ്താൽ എറർ കാണിക്കാതിരിക്കാൻ
        }
    }, 15000); // 15000 മില്ലിസെക്കൻഡ് = 15 സെക്കൻഡ്
}

// 15 മിനിറ്റിന് ശേഷം ലിങ്ക് ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ
function deleteLinkAfter15Minutes(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {
            // എറർ ഒഴിവാക്കാൻ
        }
    }, 900000); // 900000 മില്ലിസെക്കൻഡ് = 15 മിനിറ്റ്
}

// Admin Checker Function
async function isAdmin(ctx) {
    if (ctx.chat.type === 'private') return false;
    try {
        const member = await ctx.getChatMember(ctx.from.id);
        return ['creator', 'administrator'].includes(member.status);
    } catch (e) {
        return false;
    }
}

// Rose Style Start/Help Text
const helpText = 
    "<b>Hey there! I am a Group Management Bot styled like Rose.</b>\n\n" +
    "I can help you manage your groups easily with warnings, mutes, and bans.\n\n" +
    "<b>Click the buttons below to explore my commands:</b>";

const mainKeyboard = new InlineKeyboard()
    .text("🛡️ Admin Cmds", "help_admin")
    .text("⚠️ Warnings", "help_warn").row()
    .text("⚙️ Settings", "help_settings");

// --- START & HELP COMMANDS ---
bot.command(['start', 'help'], async (ctx) => {
    const sent = await ctx.reply(helpText, { parse_mode: "HTML", reply_markup: mainKeyboard });
    deleteAfter15Seconds(ctx, sent.message_id);
});

// --- INLINE KEYBOARD CALLBACK HANDLERS ---
bot.callbackQuery("help_main", async (ctx) => {
    await ctx.editMessageText(helpText, { parse_mode: "HTML", reply_markup: mainKeyboard });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_admin", async (ctx) => {
    const text = 
        "<b>🛡️ Admin Commands:</b>\n" +
        "<i>(Reply to a user's message to execute)</i>\n\n" +
        "🔹 `/ban` - Bans the user from the group.\n" +
        "🔹 `/unban [user_id]` - Unbans the user.\n" +
        "🔹 `/kick` - Kicks the user out of the group.\n" +
        "🔹 `/mute` - Mutes the user permanently.\n" +
        "🔹 `/tmute [mins]` - Mutes user for temporary time (e.g. `/tmute 10`).\n" +
        "🔹 `/unmute` - Unmutes the user.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_warn", async (ctx) => {
    const text = 
        "<b>⚠️ Warning System:</b>\n" +
        "<i>Keep your group clean with warnings.</i>\n\n" +
        "🔹 `/warn` - Warns a user. (Reply to message)\n" +
        "🔹 `/resetwarn` - Resets all warnings of that user.\n\n" +
        "📌 <b>Note:</b> When a user reaches <b>3 warnings</b>, they will be automatically muted by the bot.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_settings", async (ctx) => {
    const text = 
        "<b>⚙️ Configuration:</b>\n\n" +
        "🔹 `/antilink on` - Delete all messages except links.\n" +
        "🔹 `/antilink off` - Allow all normal messages.\n" +
        "🔹 `/autodel on` - Auto delete links after 15 mins.\n" +
        "🔹 `/autodel off` - Stop deleting links after 15 mins.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

// --- MANAGEMENT FUNCTIONS (ROSE STYLE) ---

bot.command('ban', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ You need to be an admin to use this.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to ban them.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        const sent = await ctx.reply(`⚡ <b>Done. Locked out ${user.first_name}!</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('unban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const userId = parseInt(ctx.match);
    if (isNaN(userId)) {
        const sent = await ctx.reply("⚠️ Usage: `/unban [user_id]`");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    try {
        await ctx.unbanChatMember(userId);
        const sent = await ctx.reply(`✅ <b>User ${userId} has been pardoned.</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('kick', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to kick them.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        await ctx.unbanChatMember(user.id);
        const sent = await ctx.reply(`🏃 <b>Removed ${user.first_name} from the chat.</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('mute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to mute them.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false });
        const sent = await ctx.reply(`🤐 <b>Shhh... ${user.first_name} is now silenced permanently!</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('tmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to temporary mute.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    
    const minutes = parseInt(ctx.match);
    if (isNaN(minutes) || minutes <= 0) {
        const sent = await ctx.reply("⚠️ Specify time! Example: `/tmute 10`");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    const untilTime = Math.floor(Date.now() / 1000) + minutes * 60;

    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false }, { until_date: untilTime });
        const sent = await ctx.reply(`⏳ <b>Silenced ${user.first_name} for ${minutes} minutes.</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('unmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to unmute.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, {
            can_send_messages: true, can_send_audios: true, can_send_documents: true,
            can_send_photos: true, can_send_videos: true, can_send_video_notes: true,
            can_send_voice_notes: true, can_send_polls: true, can_send_other_messages: true,
            can_add_web_page_previews: true
        });
        const sent = await ctx.reply(`🔊 <b>${user.first_name} can speak again!</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('warn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to warn them.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    if (!userWarnings[user.id]) userWarnings[user.id] = 0;
    userWarnings[user.id] += 1;

    if (userWarnings[user.id] >= 3) {
        try {
            await ctx.restrictChatMember(user.id, { can_send_messages: false });
            userWarnings[user.id] = 0;
            const sent = await ctx.reply(`🚷 <b>${user.first_name} reached 3/3 warnings and has been muted!</b>`, { parse_mode: "HTML" });
            deleteAfter15Seconds(ctx, sent.message_id);
        } catch (e) {
            const sent = await ctx.reply(`❌ Error auto-muting: ${e.message}`);
            deleteAfter15Seconds(ctx, sent.message_id);
        }
    } else {
        const sent = await ctx.reply(`⚠️ <b>User ${user.first_name} has been warned (${userWarnings[user.id]}/3). Don't break the rules!</b>`, { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

bot.command('resetwarn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user to reset warnings.");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    
    const user = ctx.message.reply_to_message.from;
    userWarnings[user.id] = 0;
    const sent = await ctx.reply(`✅ <b>Warnings reset for ${user.first_name}. Clean slate!</b>`, { parse_mode: "HTML" });
    deleteAfter15Seconds(ctx, sent.message_id);
});

bot.command('antilink', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    
    if (args === 'on') {
        antilinkStatus = true;
        const sent = await ctx.reply("✅ <b>Anti-link active. Non-link messages will be purged!</b>", { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } else if (args === 'off') {
        antilinkStatus = false;
        const sent = await ctx.reply("🛑 <b>Anti-link disabled. All messages allowed.</b>", { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } else {
        const sent = await ctx.reply("⚠️ Use: `/antilink on` or `/antilink off`");
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

// ഓട്ടോ ലിങ്ക് ഡിലീറ്റ് ഓൺ/ഓഫ് ചെയ്യാനുള്ള കമാൻഡ്
bot.command('autodel', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfter15Seconds(ctx, sent.message_id);
        return;
    }
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    
    if (args === 'on') {
        autodelStatus = true;
        const sent = await ctx.reply("✅ <b>Link Auto-Delete active. User links will be deleted after 15 minutes!</b>", { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } else if (args === 'off') {
        autodelStatus = false;
        const sent = await ctx.reply("🛑 <b>Link Auto-Delete disabled. Links will not be deleted.</b>", { parse_mode: "HTML" });
        deleteAfter15Seconds(ctx, sent.message_id);
    } else {
        const sent = await ctx.reply("⚠️ Use: `/autodel on` or `/autodel off`");
        deleteAfter15Seconds(ctx, sent.message_id);
    }
});

// --- WELCOME & TEXT PURGE HANDLERS ---

bot.on('message:new_chat_members', async (ctx) => {
    for (const newMember of ctx.message.new_chat_members) {
        if (newMember.id === ctx.me.id) continue;
        try {
            if (lastWelcomeMessageId !== null) {
                try { await ctx.api.deleteMessage(ctx.chat.id, lastWelcomeMessageId); } catch (e) {}
            }
            const welcomeText = `✨ <b>Welcome</b> <a href="tg://user?id=${newMember.id}">${newMember.first_name}</a> <b>to the group! Stay respectful.</b>`;
            const sentMessage = await ctx.reply(welcomeText, { parse_mode: "HTML" });
            lastWelcomeMessageId = sentMessage.message_id;
            
            // വെൽക്കം മെസ്സേജും 15 സെക്കൻഡിൽ ഡിലീറ്റ് ചെയ്യണമെങ്കിൽ താഴത്തെ വരി ഉപയോഗിക്കാം
            deleteAfter15Seconds(ctx, sentMessage.message_id);
        } catch (err) {
            console.error(err);
        }
    }
});

bot.on('message:text', async (ctx) => {
    const isAdminUser = await isAdmin(ctx);

    // ലിങ്ക് ചെക്ക് ചെയ്യൽ
    const entities = ctx.message.entities || [];
    const hasLink = entities.some(e => e.type === 'url' || e.type === 'text_link');

    // കസ്റ്റം ഫീച്ചർ: 15 മിനിറ്റിനു ശേഷം ലിങ്ക് ഡിലീറ്റ് ചെയ്യൽ (സാധാരണ യൂസർമാർക്ക് മാത്രം)
    if (hasLink && autodelStatus && !isAdminUser) {
        deleteLinkAfter15Minutes(ctx, ctx.message.message_id);
    }

    if (!antilinkStatus) return;
    if (isAdminUser) return;

    if (hasLink) return;

    try {
        await ctx.deleteMessage();
        if (lastWarningMessageId !== null) {
            try { await ctx.api.deleteMessage(ctx.chat.id, lastWarningMessageId); } catch (e) {}
        }
        const warningText = `⚠️ <a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, <b>only links are allowed here!</b>`;
        const sentMessage = await ctx.reply(warningText, { parse_mode: "HTML" });
        lastWarningMessageId = sentMessage.message_id;
    } catch (err) {
        console.error(err);
    }
});

bot.catch((err) => {
    console.error(`Bot Error: ${err.error.message}`);
});

console.log("Rose-Style Management Bot is starting...");
bot.start();