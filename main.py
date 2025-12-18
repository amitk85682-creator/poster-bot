# -*- coding: utf-8 -*-
import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode, ChatMemberStatus
from database import ForceSubDB

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BOT_OWNER_ID = int(os.environ.get("BOT_OWNER_ID", "0"))  # Your Telegram ID
PORT = int(os.environ.get("PORT", 8080))

# ============ HEALTH SERVER ============
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Kavya Bot is Running!")
    def log_message(self, format, *args): pass

def run_health_server():
    HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever()

# ============ HELPER FUNCTIONS ============
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None) -> bool:
    """Check if user is admin in the chat"""
    try:
        if user_id is None:
            user_id = update.effective_user.id
        
        # Bot owner is always admin
        if user_id == BOT_OWNER_ID:
            return True
        
        chat_id = update.effective_chat.id
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except:
        return False

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int, channels: list) -> tuple:
    """Check if user is subscribed to all channels"""
    not_joined = []
    
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(
                chat_id=channel['target_chat_id'],
                user_id=user_id
            )
            if member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                not_joined.append(channel)
        except Exception as e:
            logger.warning(f"Cannot check {channel['target_chat_id']}: {e}")
            # If can't check, assume not joined
            not_joined.append(channel)
    
    return len(not_joined) == 0, not_joined

def create_join_buttons(not_joined: list, main_chat_id: int) -> InlineKeyboardMarkup:
    """Create join buttons for channels user hasn't joined"""
    buttons = []
    
    for idx, channel in enumerate(not_joined, 1):
        title = channel.get('target_chat_title', f'Channel {idx}')
        link = channel['target_link']
        buttons.append([InlineKeyboardButton(f"👉 Join {title}", url=link)])
    
    # Check button
    buttons.append([InlineKeyboardButton("✅ I've Joined - Verify", callback_data=f"checksub_{main_chat_id}")])
    
    return InlineKeyboardMarkup(buttons)

# ============ COMMAND HANDLERS ============
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - Kavya Persona"""
    user = update.effective_user
    
    if update.effective_chat.type == "private":
        text = (
            f"✨ **Namaste {user.first_name}!**\n\n"
            "Main hoon **Kavya**, aapki personal Group Assistant! 💖\n\n"
            "🌸 **Main kya kar sakti hoon?**\n"
            "• Main ensure karti hoon ki users channels join karein.\n"
            "• Groups ko spam se bachati hoon.\n"
            "• Multiple channels ko support karti hoon.\n\n"
            "📝 **Admin Commands:**\n"
            "• `/addforcesub` - Channel add karein\n"
            "• `/listforcesub` - List dekhein\n"
            "• `/removeforcesub` - Channel hatayein\n\n"
            "Mujhe apne group me add karein aur **Admin** banayein! 🚀"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("✨ Kavya is online! Help ke liye /help use karein.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = (
        "📚 **Kavya Help Menu** 🌸\n\n"
        "**Setup kaise karein?**\n"
        "1️⃣ Mujhe apne **Group** me Admin banayein.\n"
        "2️⃣ Mujhe apne **Channel** me Admin banayein.\n"
        "3️⃣ Group me ye command use karein:\n"
        "`/addforcesub <channel_link>`\n\n"
        "**Admin Commands:**\n"
        "• `/addforcesub` - Channel link ke sath use karein\n"
        "• `/removeforcesub` - Channel ID ke sath use karein\n"
        "• `/listforcesub` - Sabhi channels ki list\n"
        "• `/clearforcesub` - Sab kuch delete karein\n\n"
        "Agar koi issue ho to owner se contact karein! 💖"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def add_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a force subscribe channel"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Ye command group me use karein, dear!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Sorry! Sirf Admins ye kar sakte hain.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **Aise use karein:** `/addforcesub <channel_link>`\n\n"
            "**Example:**\n"
            "`/addforcesub https://t.me/yourchannel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_link = context.args[0]
    
    # Extract channel username or ID from link
    try:
        if "t.me/+" in channel_link or "t.me/joinchat/" in channel_link:
            await update.message.reply_text(
                "📝 Private channels ke liye ye use karein:\n"
                "`/addprivateforcesub <channel_id> <invite_link>`"
            )
            return
        
        # Public channel
        if "t.me/" in channel_link:
            username = channel_link.split("t.me/")[-1].split("/")[0].replace("@", "")
            channel = await context.bot.get_chat(f"@{username}")
            channel_id = channel.id
            channel_title = channel.title
            invite_link = channel_link
        else:
            await update.message.reply_text("❌ Link galat lag raha hai! Check karein.")
            return
            
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        await update.message.reply_text(
            "❌ Oops! Main channel access nahi kar pa rahi.\n\n"
            "Please check karein ki main wahan **Admin** hoon ya nahi! 🥺"
        )
        return
    
    # Check if bot is admin in target channel
    try:
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await update.message.reply_text(f"❌ Pehle mujhe **{channel_title}** me Admin banayein! 🥺", parse_mode=ParseMode.MARKDOWN)
            return
    except:
        await update.message.reply_text("❌ Main permissions check nahi kar pa rahi!")
        return
    
    # Save to database
    main_chat = update.effective_chat
    success = ForceSubDB.add_force_sub(
        main_chat_id=main_chat.id,
        main_chat_title=main_chat.title,
        target_chat_id=channel_id,
        target_chat_title=channel_title,
        target_link=invite_link,
        added_by=update.effective_user.id
    )
    
    if success:
        await update.message.reply_text(
            f"✅ **Done! Channel Add Ho Gaya!** ✨\n\n"
            f"📌 Group: `{main_chat.title}`\n"
            f"📢 Channel: `{channel_title}`\n"
            f"🔗 Link: {invite_link}\n\n"
            f"Ab sabko join karna padega! 😉",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Add nahi ho paya, shayad pehle se added hai.")

async def add_force_sub_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add private channel with ID"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Ye command group me use karein!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Sirf Admins allow hain!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/addprivateforcesub <channel_id> <invite_link>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        channel_id = int(context.args[0])
        invite_link = context.args[1]
    except ValueError:
        await update.message.reply_text("❌ Invalid Channel ID!")
        return
    
    try:
        channel = await context.bot.get_chat(channel_id)
        channel_title = channel.title
    except Exception as e:
        await update.message.reply_text("❌ Channel access denied! Make sure main Admin hoon.")
        return
    
    main_chat = update.effective_chat
    success = ForceSubDB.add_force_sub(
        main_chat_id=main_chat.id,
        main_chat_title=main_chat.title,
        target_chat_id=channel_id,
        target_chat_title=channel_title,
        target_link=invite_link,
        added_by=update.effective_user.id
    )
    
    if success:
        await update.message.reply_text(f"✅ **Private Channel Added!** ✨\n📢 `{channel_title}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Failed to add!")

async def remove_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a force subscribe channel"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Group me use karein!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Sirf Admins allow hain!")
        return
    
    if not context.args:
        channels = ForceSubDB.get_force_subs(update.effective_chat.id)
        if not channels:
            await update.message.reply_text("📭 Koi channel set nahi hai!")
            return
        
        text = "📝 **Remove karne ke liye ID use karein:**\n`/removeforcesub <channel_id>`\n\n**Current Channels:**\n"
        for ch in channels:
            text += f"• `{ch['target_chat_id']}` - {ch.get('target_chat_title', 'Unknown')}\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid ID!")
        return
    
    success = ForceSubDB.remove_force_sub(update.effective_chat.id, target_id)
    
    if success:
        await update.message.reply_text("✅ Channel remove kar diya gaya hai! 🗑️")
    else:
        await update.message.reply_text("❌ Failed to remove!")

async def list_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all force subscribe channels"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Group me use karein!")
        return
    
    channels = ForceSubDB.get_force_subs(update.effective_chat.id)
    
    if not channels:
        await update.message.reply_text("📭 **Filhal koi channel set nahi hai!**")
        return
    
    text = f"📋 **Subscription List** 🌸\n"
    text += f"👥 Group: `{update.effective_chat.title}`\n\n"
    
    for idx, ch in enumerate(channels, 1):
        text += f"**{idx}.** {ch.get('target_chat_title', 'Unknown')}\n"
        text += f"   🆔 `{ch['target_chat_id']}`\n"
        text += f"   🔗 {ch['target_link']}\n\n"
    
    text += f"📊 Total: {len(channels)} channel(s)"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def clear_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all force subscribe channels"""
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only Admins!")
        return
    
    success = ForceSubDB.remove_all_force_subs(update.effective_chat.id)
    if success:
        await update.message.reply_text("✅ Sabhi channels hata diye gaye hain! 🧹")
    else:
        await update.message.reply_text("❌ Failed!")

# ============ MESSAGE HANDLER ============
async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is subscribed to all required channels"""
    if update.effective_chat.type == "private" or not update.message:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    if user.is_bot:
        return
    
    if await is_admin(update, context, user.id):
        return
    
    channels = ForceSubDB.get_force_subs(chat.id)
    if not channels:
        return
    
    is_subscribed, not_joined = await check_subscription(context, user.id, channels)
    
    if is_subscribed:
        return
    
    # User not subscribed - DELETE MESSAGE FIRST
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Cannot delete message: {e}")
    
    # Create warning message with Mention
    # Using user.mention_markdown() allows clicking the name
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    
    warning_text = (
        f"🚫 **Oops {user_mention}!**\n\n"
        f"Maine apka message **delete** kar diya hai kyunki aapne channels join nahi kiye! 🥺\n\n"
        f"👇 **Chat karne ke liye please niche diye gaye channels join karein:**\n"
    )
    
    keyboard = create_join_buttons(not_joined, chat.id)
    
    try:
        warning_msg = await context.bot.send_message(
            chat_id=chat.id,
            text=warning_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Auto-delete warning after 60 seconds
        context.job_queue.run_once(
            delete_message,
            60,
            data={"chat_id": chat.id, "message_id": warning_msg.message_id}
        )
    except Exception as e:
        logger.error(f"Error sending warning: {e}")

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    """Delete a message (used by job queue)"""
    try:
        await context.bot.delete_message(
            chat_id=context.job.data["chat_id"],
            message_id=context.job.data["message_id"]
        )
    except:
        pass

# ============ CALLBACK HANDLER ============
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    data = query.data
    
    if data.startswith("checksub_"):
        chat_id = int(data.split("_")[1])
        user = query.from_user
        
        channels = ForceSubDB.get_force_subs(chat_id)
        
        if not channels:
            await query.answer("✅ Koi restrictions nahi hain!", show_alert=True)
            try: await query.message.delete()
            except: pass
            return
        
        is_subscribed, not_joined = await check_subscription(context, user.id, channels)
        
        if is_subscribed:
            await query.answer("✅ Verification Successful! Welcome back! ✨", show_alert=True)
            try: await query.message.delete()
            except: pass
        else:
            await query.answer(
                f"❌ Aapne abhi bhi channels join nahi kiye! 🥺",
                show_alert=True
            )

# ============ MAIN ============
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found!")
        return
    
    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Build application with Increased Timeouts for Render
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .build()
    )
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addforcesub", add_force_sub))
    application.add_handler(CommandHandler("addprivateforcesub", add_force_sub_private))
    application.add_handler(CommandHandler("removeforcesub", remove_force_sub))
    application.add_handler(CommandHandler("listforcesub", list_force_sub))
    application.add_handler(CommandHandler("clearforcesub", clear_force_sub))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Message handler (must be last)
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
        check_force_sub
    ))
    
    print("🚀 Kavya Bot Started!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
