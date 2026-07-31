const express = require('express');
const { Bot, InlineKeyboard, GrammyError, HttpError } = require('grammy');
const fs = require('fs');

// --- WEB SERVER FOR HOSTING ---
const app = express();
const PORT = process.env.PORT || 8080;
app.get('/', (req, res) => res.send("Rose-Style Management Bot with Leaderboard is running!"));
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

// --- BOT SETUP ---
// Render Environment Variable വഴി നൽകുന്നതാണ് സുരക്ഷിതം (അല്ലെങ്കിൽ നിങ്ങളുടെ ടോക്കൺ ഇവിടെ നൽകുക)
const TOKEN = process.env.BOT_TOKEN || "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4";
const bot = new Bot(TOKEN);

// Global Variables
let lastWarningMessageId = null;
let lastWelcomeMessageId = null;
let antilinkStatus = true;
let autodelStatus = true; 

// ടൈം സെറ്റിംഗ്സ് (Default: രാത്രി 10 മണി മുതൽ രാവിലെ 6 മണി വരെ)
let startHour = 22; 
let endHour = 6;    
const TIMEZONE = "Asia/Kolkata";

// ടൈമർ സെറ്റിംഗ്സ്
let linkDeleteMinutes = 15;
let msgDeleteSeconds = 10; 

const userWarnings = {};
const DATA_FILE = 'data.json';

// --- LEADERBOARD DATA FUNCTIONS ---
function loadData() {
    if (!fs.existsSync(DATA_FILE)) {
        fs.writeFileSync(DATA_FILE, JSON.stringify({}));
    }
    try {
        const rawData = fs.readFileSync(DATA_FILE);
        return JSON.parse(rawData);
    } catch (e) {
        return {};
    }
}

function saveData(data) {
    fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

// ബോട്ട് മെസ്സേജുകൾ ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ
function deleteAfterSeconds(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {}
    }, msgDeleteSeconds * 1000);
}

// 15 മിനിറ്റിന് ശേഷം ലിങ്ക് ഡിലീറ്റ് ചെയ്യാനുള്ള ഫങ്ഷൻ
function deleteLinkAfter15Minutes(ctx, messageId) {
    setTimeout(async () => {
        try {
            await ctx.api.deleteMessage(ctx.chat.id, messageId);
        } catch (e) {}
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
    "<b>Hey there! I am a Group Management & Leaderboard Bot.</b>\n\n" +
    "I can help you manage your group with warnings, auto-delete, and track top media contributors!\n\n" +
    "<b>Click the buttons below to explore my commands:</b>";

const mainKeyboard = new InlineKeyboard()
    .text("🛡️ Admin Cmds", "help_admin")
    .text("⚠️ Warnings", "help_warn").row()
    .text("🏆 Leaderboard", "help_leaderboard")
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
        "🔹 `/ban` - Bans the user.\n" +
        "🔹 `/unban [user_id]` - Unbans the user.\n" +
        "🔹 `/kick` - Kicks the user.\n" +
        "🔹 `/mute` - Mutes permanently.\n" +
        "🔹 `/tmute [mins]` - Temporary mute.\n" +
        "🔹 `/unmute` - Unmutes user.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_warn", async (ctx) => {
    const text = 
        "<b>⚠️ Warning System:</b>\n\n" +
        "🔹 `/warn` - Warns a user. (Reply to message)\n" +
        "🔹 `/resetwarn` - Resets warnings.\n\n" +
        "📌 Reaching <b>3 warnings</b> auto-mutes the user.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_leaderboard", async (ctx) => {
    const text = 
        "<b>🏆 Leaderboard System:</b>\n\n" +
        "🔹 `/leaderboard` - Shows Top 3 members who sent the most media (photos, videos, documents).\n" +
        "🔹 Tracks media sent in the group automatically.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

bot.callbackQuery("help_settings", async (ctx) => {
    const text = 
        "<b>⚙️ Configuration:</b>\n\n" +
        "🔹 `/antilink on/off` - Toggle anti-link mode.\n" +
        "🔹 `/autodel on/off` - Auto delete links during restricted hours.\n" +
        "🔹 `/setlinktime [start] [end]` - Set restricted hours (e.g. `/setlinktime 22 6`).\n" +
        "🔹 `/setdeltime [link_mins] [msg_secs]` - Set auto-delete times.";
    const backKb = new InlineKeyboard().text("⬅️ Back", "help_main");
    await ctx.editMessageText(text, { parse_mode: "HTML", reply_markup: backKb });
    await ctx.answerCallbackQuery();
});

// --- MEDIA TRACKING HANDLER ---
bot.on([':photo', ':video', ':document', ':animation'], async (ctx) => {
    if (!ctx.from) return;
    const userId = ctx.from.id;
    const userName = ctx.from.first_name || 'User';

    let data = loadData();

    if (!data[userId]) {
        data[userId] = { name: userName, count: 0 };
    }

    data[userId].name = userName;
    data[userId].count += 1;

    saveData(data);
});

// --- LEADERBOARD COMMAND ---
bot.command('leaderboard', async (ctx) => {
    let data = loadData();
    let users = Object.values(data);

    if (users.length === 0) {
        const sent = await ctx.reply("🏆 <b>MEDIA LEADERBOARD</b>\n\nഇതുവരെ ആരും മീഡിയ അയച്ചിട്ടില്ല!", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
        return;
    }

    users.sort((a, b) => b.count - a.count);
    let top3 = users.slice(0, 3);

    let medals = ['🥇', '🥈', '🥉'];
    let text = '🏆 <b>TOP MEDIA CONTRIBUTORS</b> 🏆\n';
    text += '➖➖➖➖➖➖➖➖➖➖➖➖\n\n';

    top3.forEach((user, index) => {
        text += `${medals[index]} <b>${user.name}</b> — <code>${user.count}</code> മീഡിയകൾ\n`;
    });

    text += '\n➖➖➖➖➖➖➖➖➖➖➖➖\n';
    text += '✨ <i>കൂടുതൽ പോസ്റ്റുകൾ അയച്ച് മുൻപിൽ എത്തൂ!</i>';

    const sent = await ctx.reply(text, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

// --- MANAGEMENT COMMANDS ---
bot.command('ban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        const sent = await ctx.reply(`⚡ <b>Done. Locked out ${user.first_name}!</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {}
});

bot.command('unban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const userId = parseInt(ctx.match);
    if (isNaN(userId)) return;
    try {
        await ctx.unbanChatMember(userId);
        const sent = await ctx.reply(`✅ <b>User ${userId} has been pardoned.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {}
});

bot.command('kick', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(user.id);
        await ctx.unbanChatMember(user.id);
        const sent = await ctx.reply(`🏃 <b>Removed ${user.first_name} from the chat.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {}
});

bot.command('mute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const user = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false });
        const sent = await ctx.reply(`🤐 <b>Shhh... ${user.first_name} is now silenced!</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {}
});

bot.command('tmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const minutes = parseInt(ctx.match);
    if (isNaN(minutes) || minutes <= 0) return;
    const user = ctx.message.reply_to_message.from;
    const untilTime = Math.floor(Date.now() / 1000) + minutes * 60;
    try {
        await ctx.restrictChatMember(user.id, { can_send_messages: false }, { until_date: untilTime });
        const sent = await ctx.reply(`⏳ <b>Silenced ${user.first_name} for ${minutes} minutes.</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } catch (err) {}
});

bot.command('unmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
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
    } catch (err) {}
});

bot.command('warn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const user = ctx.message.reply_to_message.from;
    if (!userWarnings[user.id]) userWarnings[user.id] = 0;
    userWarnings[user.id] += 1;

    if (userWarnings[user.id] >= 3) {
        try {
            await ctx.restrictChatMember(user.id, { can_send_messages: false });
            userWarnings[user.id] = 0;
            const sent = await ctx.reply(`🚷 <b>${user.first_name} reached 3/3 warnings and has been muted!</b>`, { parse_mode: "HTML" });
            deleteAfterSeconds(ctx, sent.message_id);
        } catch (e) {}
    } else {
        const sent = await ctx.reply(`⚠️ <b>User ${user.first_name} has been warned (${userWarnings[user.id]}/3).</b>`, { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('resetwarn', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return;
    const user = ctx.message.reply_to_message.from;
    userWarnings[user.id] = 0;
    const sent = await ctx.reply(`✅ <b>Warnings reset for ${user.first_name}. Clean slate!</b>`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

bot.command('antilink', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    if (args === 'on') {
        antilinkStatus = true;
        const sent = await ctx.reply("✅ <b>Anti-link active!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else if (args === 'off') {
        antilinkStatus = false;
        const sent = await ctx.reply("🛑 <b>Anti-link disabled.</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('autodel', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    if (args === 'on') {
        autodelStatus = true;
        const sent = await ctx.reply("✅ <b>Auto-Delete activated!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    } else if (args === 'off') {
        autodelStatus = false;
        const sent = await ctx.reply("🛑 <b>Auto-Delete deactivated!</b>", { parse_mode: "HTML" });
        deleteAfterSeconds(ctx, sent.message_id);
    }
});

bot.command('setlinktime', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const matches = ctx.match ? ctx.match.trim().split(/\s+/) : [];
    if (matches.length !== 2) return;
    const start = parseInt(matches[0]);
    const end = parseInt(matches[1]);
    if (isNaN(start) || isNaN(end) || start < 0 || start > 23 || end < 0 || end > 23) return;
    startHour = start;
    endHour = end;
    const sent = await ctx.reply(`✅ <b>Mute time updated: ${startHour}:00 to ${endHour}:00 (IST)</b>`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

bot.command('setdeltime', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const matches = ctx.match ? ctx.match.trim().split(/\s+/) : [];
    if (matches.length !== 2) return;
    const linkMins = parseInt(matches[0]);
    const msgSecs = parseInt(matches[1]);
    if (isNaN(linkMins) || isNaN(msgSecs) || linkMins <= 0 || msgSecs <= 0) return;
    linkDeleteMinutes = linkMins;
    msgDeleteSeconds = msgSecs;
    const sent = await ctx.reply(`✅ <b>Delete configurations updated!</b>`, { parse_mode: "HTML" });
    deleteAfterSeconds(ctx, sent.message_id);
});

// --- WELCOME HANDLER ---
bot.on('message:new_chat_members', async (ctx) => {
    for (const newMember of ctx.message.new_chat_members) {
        if (newMember.id === ctx.me.id) continue;
        try {
            if (lastWelcomeMessageId !== null) {
                try { await ctx.api.deleteMessage(ctx.chat.id, lastWelcomeMessageId); } catch (e) {}
            }
            const welcomeText = `✨ ഹലോ <a href="tg://user?id=${newMember.id}">${newMember.first_name}</a>, ഇത് ലിങ്ക് ഗ്രൂപ്പ് ആണ് ട്ടോ, ലിങ്ക് മാത്രം മതി!`;
            const sentMessage = await ctx.reply(welcomeText, { parse_mode: "HTML" });
            lastWelcomeMessageId = sentMessage.message_id;
            deleteAfterSeconds(ctx, sentMessage.message_id);
        } catch (err) {}
    }
});

// --- TEXT PURGE & MUTE HANDLERS ---
bot.on('message:text', async (ctx) => {
    const isAdminUser = await isAdmin(ctx);
    const entities = ctx.message.entities || [];
    const hasLink = entities.some(e => e.type === 'url' || e.type === 'text_link');

    if (hasLink && autodelStatus && !isAdminUser) {
        if (isWithinTimeRange()) {
            deleteLinkAfter15Minutes(ctx, ctx.message.message_id);
            const muteUntilTime = Math.floor(Date.now() / 1000) + 5 * 60 * 60;
            try {
                await ctx.restrictChatMember(ctx.from.id, { can_send_messages: false }, { until_date: muteUntilTime });
                const alertText = `⏳ <b><a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a> has been muted for 5 hours for sending a link during restricted hours!</b>`;
                const sentAlert = await ctx.reply(alertText, { parse_mode: "HTML" });
                deleteAfterSeconds(ctx, sentAlert.message_id);
            } catch (muteError) {}
        } else {
            const successText = `✅ <b><a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, restricted hours are over. Your link is allowed!</b>`;
            const sentSuccess = await ctx.reply(successText, { parse_mode: "HTML" });
            deleteAfterSeconds(ctx, sentSuccess.message_id);
        }
    }

    if (!antilinkStatus || isAdminUser || hasLink) return;

    try {
        await ctx.deleteMessage();
        await ctx.restrictChatMember(ctx.from.id, { can_send_messages: false });

        if (lastWarningMessageId !== null) {
            try { await ctx.api.deleteMessage(ctx.chat.id, lastWarningMessageId); } catch (e) {}
        }

        const warningText = `⚠️ <a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, <b>ഇത് ലിങ്ക് ഗ്രൂപ്പ് ആണ്! ലിങ്ക് അല്ലാത്ത മെസ്സേജുകൾ അനുവദിക്കില്ല. നിങ്ങളെ മ്യൂട്ട് ചെയ്തിട്ടുണ്ട്.</b>`;
        const sentMessage = await ctx.reply(warningText, { parse_mode: "HTML" });
        lastWarningMessageId = sentMessage.message_id;

        deleteAfterSeconds(ctx, sentMessage.message_id);
    } catch (err) {}
});

bot.catch((err) => {
    console.error(`Bot Error: ${err.error.message}`);
});

console.log("Rose-Style Management Bot with Leaderboard is starting...");
bot.start();