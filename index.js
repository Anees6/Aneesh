const express = require('express');
const { Bot, GrammyError, HttpError } = require('grammy');

// --- FLASK/EXPRESS WEB SERVER SETUP ---
const app = express();
const PORT = process.env.PORT || 8080;

app.get('/', (req, res) => {
    res.send("Bot is running successfully!");
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});

// --- TELEGRAM BOT SETUP ---
// Replace with your actual token if not using environment variables
const TOKEN = "8397424887:AAEyNXWcGS6e9NoJ_JrUw_TB6ulRlcm-vL4";
const bot = new Bot(TOKEN);

// Global variables for status tracking
let lastWarningMessageId = null;
let lastWelcomeMessageId = null;
let antilinkStatus = true; // Enabled by default

// Helper function to check if user is admin
async function isAdmin(ctx) {
    if (ctx.chat.type === 'private') return false;
    const member = await ctx.getChatMember(ctx.from.id);
    return ['creator', 'administrator'].includes(member.status);
}

// /start command
bot.command('start', async (ctx) => {
    await ctx.reply(
        "Hello! I am your Group Management Bot.\n\n" +
        "**Commands (Reply to a user's message):**\n" +
        "/ban - Ban a user\n" +
        "/kick - Kick a user\n" +
        "/mute - Mute a user permanently\n" +
        "/tmute [minutes] - Mute for a specific time (e.g., /tmute 10)\n" +
        "/unmute - Unmute a user\n\n" +
        "**Admin Commands:**\n" +
        "/antilink on - Turn on anti-link system\n" +
        "/antilink off - Turn off anti-link system\n" +
        "/unban [user_id] - Unban a user"
    );
});

// /antilink toggle command
bot.command('antilink', async (ctx) => {
    if (!await isAdmin(ctx)) {
        return ctx.reply("❌ You do not have permission to use this command!");
    }

    const args = ctx.match ? ctx.match.trim().toLowerCase() : '';
    if (args === 'on') {
        antilinkStatus = true;
        await ctx.reply("✅ Anti-link system enabled! Non-link messages will be deleted.");
    } else if (args === 'off') {
        antilinkStatus = false;
        await ctx.reply("🛑 Anti-link system disabled! All messages allowed.");
    } else {
        await ctx.reply("⚠️ Usage: `/antilink on` or `/antilink off`");
    }
});

// /ban command
bot.command('ban', async (ctx) => {
    if (!await isAdmin(ctx)) return ctx.reply("❌ You do not have permission to use this command!");
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Reply to the user's message you want to ban.");
    
    const userToBan = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(userToBan.id);
        await ctx.reply(`❌ User ${userToBan.first_name} has been banned.`);
    } catch (err) {
        await ctx.reply(`Failed to ban: ${err.message}`);
    }
});

// /unban command
bot.command('unban', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    const userId = parseInt(ctx.match);
    if (isNaN(userId)) return ctx.reply("⚠️ Usage: `/unban [user_id]`");

    try {
        await ctx.unbanChatMember(userId);
        await ctx.reply(`✓ User (ID: ${userId}) has been unbanned.`);
    } catch (err) {
        await ctx.reply(`Failed to unban: ${err.message}`);
    }
});

// /kick command
bot.command('kick', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Reply to the user's message you want to kick.");

    const userToKick = ctx.message.reply_to_message.from;
    try {
        await ctx.banChatMember(userToKick.id);
        await ctx.unbanChatMember(userToKick.id);
        await ctx.reply(`🏃 ${userToKick.first_name} has been kicked from the group.`);
    } catch (err) {
        await ctx.reply(`Failed to kick: ${err.message}`);
    }
});

// /mute command
bot.command('mute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Reply to the user's message you want to mute.");

    const userToMute = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(userToMute.id, { can_send_messages: false });
        await ctx.reply(`🔇 ${userToMute.first_name} has been muted.`);
    } catch (err) {
        await ctx.reply(`Failed to mute: ${err.message}`);
    }
});

// /tmute command
bot.command('tmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Reply to the user's message you want to mute.");
    
    const minutes = parseInt(ctx.match);
    if (isNaN(minutes)) return ctx.reply("⚠️ Please provide time in numbers (e.g., `/tmute 10`).");

    const userToMute = ctx.message.reply_to_message.from;
    const untilTime = Math.floor(Date.now() / 1000) + minutes * 60;

    try {
        await ctx.restrictChatMember(userToMute.id, { can_send_messages: false }, { until_date: untilTime });
        await ctx.reply(`⏳ ${userToMute.first_name} has been muted for ${minutes} minutes.`);
    } catch (err) {
        await ctx.reply(`Failed to mute: ${err.message}`);
    }
});

// /unmute command
bot.command('unmute', async (ctx) => {
    if (!await isAdmin(ctx)) return;
    if (!ctx.message.reply_to_message) return ctx.reply("⚠️ Reply to the user's message you want to unmute.");

    const userToUnmute = ctx.message.reply_to_message.from;
    try {
        await ctx.restrictChatMember(userToMute.id, {
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
        await ctx.reply(`🔊 ${userToUnmute.first_name} has been unmuted.`);
    } catch (err) {
        await ctx.reply(`Failed to unmute: ${err.message}`);
    }
});

// Welcome new members
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
            console.error("Welcome Error:", err);
        }
    }
});

// Handle normal text messages (Delete if not a link)
bot.on('message:text', async (ctx) => {
    if (!antilinkStatus) return;
    if (await isAdmin(ctx)) return;

    // If message contains a URL, keep it
    const entities = ctx.message.entities || [];
    const hasLink = entities.some(e => e.type === 'url' || e.type === 'text_link');
    if (hasLink) return;

    try {
        // 1. Delete the non-link message
        await ctx.deleteMessage();

        // 2. Delete previous warning
        if (lastWarningMessageId !== null) {
            try { await ctx.api.deleteMessage(ctx.chat.id, lastWarningMessageId); } catch (e) {}
        }

        // 3. Send new warning
        const warningText = `⚠️ <a href="tg://user?id=${ctx.from.id}">${ctx.from.first_name}</a>, please only send links in this group!`;
        const sentMessage = await ctx.reply(warningText, { parse_mode: "HTML" });
        lastWarningMessageId = sentMessage.message_id;
    } catch (err) {
        console.error("Message handling error:", err);
    }
});

// Error handling
bot.catch((err) => {
    const ctx = err.ctx;
    console.error(`Error while handling update ${ctx.update.update_id}:`);
    const e = err.error;
    if (e instanceof GrammyError) {
        console.error("Error in request:", e.description);
    } else if (e instanceof HttpError) {
        console.error("Could not contact Telegram:", e);
    } else {
        console.error("Unknown error:", e);
    }
});

console.log("Bot is starting...");
bot.start();