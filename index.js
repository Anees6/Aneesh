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
let autodelStatus = true; 

// ടൈം സെറ്റിംഗ്സ് (Default: രാത്രി 10 മണി മുതൽ രാവിലെ 6 മണി വരെ)
let startHour = 22; 
let endHour = 6;    
const TIMEZONE = "Asia/Kolkata"; // ഇന്ത്യയിലെ സമയക്രമം അനുസരിച്ച് പ്രവർത്തിക്കാൻ

// ടൈമർ സെറ്റിംഗ്സ് (10 സെക്കൻഡ് ആക്കി മാറ്റി)
let linkDeleteMinutes = 15;
let msgDeleteSeconds = 10; // ബോട്ട് മെസ്സേജ് 10 സെക്കൻഡിന് ശേഷം മായും

const userWarnings = {};

// ബോട്ട് മെസ്സേജുകൾ ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ (Default 10 Seconds)
function deleteAfterSeconds(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {
            // എറർ ഒഴിവാക്കാൻ
        }
    }, msgDeleteSeconds * 1000);
}

// 15 മിനിറ്റിന് ശേഷം ലിങ്ക് ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ
function deleteLinkAfter15Minutes(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {
            // എറർ ഒഴിവാക്കാൻ
        }
    }, linkDeleteMinutes * 60 * 1000);
}

// സമയപരിധിക്ക് ഉള്ളിലാണോ എന്ന് നോക്കുന്ന ഫങ്ഷൻ
function isWithinTimeRange() {
    const now = new Date();
    const localTimeStr = now.toLocaleString("en-US", { timeZone: TIMEZONE });
    const localDate = new Date(localTimeStr);
    const currentHour = localDate.getHours();

    if (startHour > endHour) {
        return currentHour >= startHour || currentHour < endHour;
    } else {
        return currentHour >= startHour && currentHour < endHour;
    }
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
    deleteAfterSeconds(ctx, sent.message_id);
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
        "🔹 `/antilink on` - Mute & delete non-link messages.\n" +
        "🔹 `/antilink off` - Allow all normal messages.\n" +
        "🔹 `/autodel on` - Auto delete links & mute sender for 5 hours during restricted hours.\n" +
        "🔹 `/autodel off` - Stop auto deleting links.\n" +
        "🔹 `/setlinktime [start] [end]` - Set restricted hours (e.g., `/setlinktime 22 6`).\n" +
        "🔹 `/setdeltime [link_mins] [msg_secs]` - Set custom delete times (e.g., `/setdeltime 15 10`).";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

// --- MANAGEMENT FUNCTIONS ---

bot.command('ban', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ You need to be an admin to use this.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to ban them.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        const sent = await ctx.reply(`⚡ <b>Done. Locked out ${user.first_name}!</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('unban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const userId = parseInt(ctx.match);
    if (isNaN(userId)) {
        const sent = await ctx.reply("⚠️ Usage: `/unban [user_id]`");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    try {
        await ctx.unbanChatMember(userId);
        const sent = await ctx.reply(`✅ <b>User ${userId} has been pardoned.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('kick', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to kick them.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        await ctx.unbanChatMember(user.id);
        const sent = await ctx.reply(`🏃 <b>Removed ${user.first_name} from the chat.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('mute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to mute them.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false });
        const sent = await ctx.reply(`🤐 <b>Shhh... ${user.first_name} is now silenced permanently!</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('tmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to temporary mute.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    
    const minutes = parseInt(ctx.match);
    if (isNaN(minutes) || minutes <= 0) {
        const sent = await ctx.reply("⚠️ Specify time! Example: `/tmute 10`");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const user = ctx.message.reply_to_message.from;
    const untilTime = Math.floor(Date.now() / 1000) + minutes * 60;

    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false }, { until_date: untilTime });
        const sent = await ctx.reply(`⏳ <b>Silenced ${user.first_name} for ${minutes} minutes.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('unmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to unmute.");
        deleteAfterSeconds(ctx, sent.message_id);
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
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {
        const sent = await ctx.reply(`❌ Error: ${err.message}`);
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('warn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user's message to warn them.");
        deleteAfterSeconds(ctx, sent.message_id);
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
            deleteAfterSeconds(ctx, sent.message_id);
        } catch (e) {
            const sent = await ctx.reply(`❌ Error auto-muting: ${e.message}`);
            deleteAfterSeconds(ctx, sent.message_id);
        }
    } else {
        const sent = await ctx.reply(`⚠️ <b>User ${user.first_name} has been warned (${userWarnings[user.id]}/3). Don't break the rules!</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('resetwarn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) {
        const sent = await ctx.reply("⚠️ Reply to a user to reset warnings.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    
    const user = ctx.message.reply_to_message.from;
    userWarnings[user.id] = 0;
    const sent = await ctx.reply(`✅ <b>Warnings reset for ${user.first_name}. Clean slate!</b>`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

bot.command('antilink', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    
    if (args === 'on') {
        antilinkStatus = true;
        const sent = await ctx.reply("✅ <b>Anti-link active. Non-link messages will be purged & users muted!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else if (args === 'off') {
        antilinkStatus = false;
        const sent = await ctx.reply("🛑 <b>Anti-link disabled. All messages allowed.</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else {
        const sent = await ctx.reply("⚠️ Use: `/antilink on` or `/antilink off`");
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('autodel', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    
    if (args === 'on') {
        autodelStatus = true;
        const sent = await ctx.reply("✅ <b>Link Auto-Delete & Time Mute system activated!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else if (args === 'off') {
        autodelStatus = false;
        const sent = await ctx.reply("🛑 <b>Link Auto-Delete & Time Mute system deactivated!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else {
        const sent = await ctx.reply("⚠️ Use: `/autodel on` or `/autodel off`");
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('setlinktime', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }
    
    const matches = ctx.match ? ctx.match.trim().split(/\s+/) : [];
    if (matches.length !== 2) {
        const sent = await ctx.reply("⚠️ <b>Usage:</b> `/setlinktime [Start Hour] [End Hour]`\nExample: `/setlinktime 22 6` (For 10 PM to 6 AM)", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const start = parseInt(matches[0]);
    const end = parseInt(matches[1]);

    if (isNaN(start) || isNaN(end) || start < 0 || start > 23 || end < 0 || end > 23) {
        const sent = await ctx.reply("⚠️ Hours must be between 0 and 23. (24-Hour Format)");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    startHour = start;
    endHour = end;

    const sent = await ctx.reply(`✅ <b>Mute time successfully updated!</b>\nLinks restricted between: <b>${startHour}:00</b> and <b>${endHour}:00</b> (IST)`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

bot.command('setdeltime', async (ctx) => {
    if (!await isAdmin(ctx)) {
        const sent = await ctx.reply("❌ Admins only!");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const matches = ctx.match ? ctx.match.trim().split(/\s+/) : [];
    if (matches.length !== 2) {
        const sent = await ctx.reply("⚠️ <b>Usage:</b> `/setdeltime [Link Mins] [Msg Secs]`\nExample: `/setdeltime 15 10`", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    const linkMins = parseInt(matches[0]);
    const msgSecs = parseInt(matches[1]);

    if (isNaN(linkMins) || isNaN(msgSecs) || linkMins <= 0 || msgSecs <= 0) {
        const sent = await ctx.reply("⚠️ Time values must be numbers greater than 0.");
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    linkDeleteMinutes = linkMins;
    msgDeleteSeconds = msgSecs;

    const sent = await ctx.reply(`✅ <b>Delete configurations updated!</b>\n▪️ Links auto-delete: <b>${linkDeleteMinutes} minutes</b>\n▪️ Normal alerts delete: <b>${msgDeleteSeconds} seconds</b>`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

// --- WELCOME HANDLER (മാറ്റം വരുത്തിയത്) ---

bot.on('message:new_chat_members', async (ctx) => {
    for (const newMember of ctx.message.new_chat_members) {
        if (newMember.id === ctx.me.id) continue;
        try {
            if (lastWelcomeMessageId !== null) {
                try { await ctx.api.deleteMessage(ctx.chat.id, lastWelcomeMessageId); } catch (e) {}
            }
            // ചോദിച്ചതുപോലെയുള്ള സ്വാഗത സന്ദേശം
            const welcomeText = `✨ ഹലോ <a href="tg://user?id=${newMember.id}">${newMember.first_name}</a>, ഇത് ലിങ്ക് ഗ്രൂപ്പ് ആണ് ട്ടോ, ലിങ്ക് മാത്രം മതി!`;
            const sentMessage = await ctx.reply(welcomeText, { parse_mode: "HTML" });
            lastWelcomeMessageId = sentMessage.message_id;
            
            deleteAfterSeconds(ctx, sentMessage.message_id);
        } catch (err) {
            console.error(err);
        }
    }
});

// --- TEXT PURGE & MUTE HANDLERS (മാറ്റം വരുത്തിയത്) ---

bot.on('message:text', async (ctx) => {
    const isAdminUser = await isAdmin(ctx);

    // ലിങ്ക് ചെക്ക് ചെയ്യൽ
    const entities = ctx.message.entities || [];
    const hasLink = entities.some(e => e.type === 'url' || e.type === 'text_link');

    // 1. നിയന്ത്രിത സമയത്ത് ലിങ്ക് അയച്ചാൽ ചെയ്യുന്ന കാര്യം
    if (hasLink && autodelStatus && !isAdminUser) {
        if (isWithinTimeRange()) {
            deleteLinkAfter15Minutes(ctx, ctx.message.message_id);

            const muteUntilTime = Math.floor(Date.now() / 1000) + 5 * 60 * 60;
            try {
                await ctx.restrictChatMember(ctx.from.id, { can_send_messages: false }, { until_date: muteUntilTime });
                
                const alertText = `⏳ <b><a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a> has been muted for 5 hours for sending a link during restricted hours!</b>`;
                const sentAlert = await ctx.reply(alertText, { parse_mode: "HTML" });
                
                deleteAfterSeconds(ctx, sentAlert.message_id);
            } catch (muteError) {
                console.error("Mute failed:", muteError.message);
            }
        } else {
            const successText = `✅ <b><a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, restricted hours are over. Your link is allowed!</b>`;
            const sentSuccess = await ctx.reply(successText, { parse_mode: "HTML" });
            
            deleteAfterSeconds(ctx, sentSuccess.message_id);
        }
    }

    if (!antilinkStatus) return;
    if (isAdminUser) return;

    // ലിങ്ക് ഉള്ള സന്ദേശമാണെങ്കിൽ മുന്നോട്ട് പോകുക
    if (hasLink) return;

    // 2. ലിങ്ക് അല്ലാത്ത മെസ്സേജുകൾ അയക്കുമ്പോൾ: ഡിലീറ്റ് + മ്യൂട്ട് + മെൻഷൻ
    try {
        await ctx.deleteMessage(); // യൂസറുടെ സാധാരണ മെസ്സേജ് ഡിലീറ്റ് ചെയ്യുന്നു

        // യൂസറെ മ്യൂട്ട് ചെയ്യുന്നു
        await ctx.restrictChatMember(ctx.from.id, { can_send_messages: false });

        if (lastWarningMessageId !== null) {
            try { await ctx.api.deleteMessage(ctx.chat.id, lastWarningMessageId); } catch (e) {}
        }

        // മെൻഷൻ ചെയ്തുകൊണ്ട് മ്യൂട്ട് ചെയ്ത കാര്യം അറിയിക്കുന്നു
        const warningText = `⚠️ <a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, <b>ഇത് ലിങ്ക് ഗ്രൂപ്പ് ആണ്! ലിങ്ക് അല്ലാത്ത മെസ്സേജുകൾ അനുവദിക്കില്ല. നിങ്ങളെ മ്യൂട്ട് ചെയ്തിട്ടുണ്ട്.</b>`;
        const sentMessage = await ctx.reply(warningText, { parse_mode: "HTML" });
        lastWarningMessageId = sentMessage.message_id;

        deleteAfterSeconds(ctx, sentMessage.message_id);
    } catch (err) {
        console.error("Error deleting/muting user:", err.message);
    }
});

bot.catch((err) => {
    console.error(`Bot Error: ${err.error.message}`);
});

console.log("Rose-Style Management Bot is starting...");
bot.start();