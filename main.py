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
        self.wfile.write(b"Force Subscribe Bot Running!")
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
    """Start command"""
    user = update.effective_user
    
    if update.effective_chat.type == "private":
        text = (
            f"👋 Hello {user.first_name}!\n\n"
            "🤖 **I'm a Force Subscribe Bot**\n\n"
            "📌 **My Features:**\n"
            "• Force users to join channels before chatting\n"
            "• Support multiple channels per group\n"
            "• Easy admin management\n\n"
            "📝 **Admin Commands:**\n"
            "`/addforcesub` - Add force sub channel\n"
            "`/removeforcesub` - Remove force sub channel\n"
            "`/listforcesub` - List all channels\n"
            "`/clearforcesub` - Remove all channels\n\n"
            "➕ Add me to your group and make me admin!"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("✅ I'm active! Use /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = (
        "📚 **Force Subscribe Bot Help**\n\n"
        "**Setup Steps:**\n"
        "1️⃣ Add bot to your GROUP as Admin\n"
        "2️⃣ Add bot to your CHANNEL as Admin\n"
        "3️⃣ Use `/addforcesub` in group\n\n"
        "**Commands (Admin Only):**\n"
        "• `/addforcesub <channel_link>` - Add channel\n"
        "• `/removeforcesub <channel_id>` - Remove channel\n"
        "• `/listforcesub` - Show all channels\n"
        "• `/clearforcesub` - Remove all\n\n"
        "**Example:**\n"
        "`/addforcesub https://t.me/yourchannel`"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def add_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a force subscribe channel"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Use this command in a group!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📝 **Usage:** `/addforcesub <channel_link>`\n\n"
            "**Example:**\n"
            "`/addforcesub https://t.me/yourchannel`\n"
            "`/addforcesub https://t.me/+ABC123xyz`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    channel_link = context.args[0]
    
    # Extract channel username or ID from link
    try:
        if "t.me/+" in channel_link or "t.me/joinchat/" in channel_link:
            # Private channel - user needs to provide channel ID separately
            await update.message.reply_text(
                "📝 For private channels, use:\n"
                "`/addforcesub <channel_id> <invite_link>`\n\n"
                "Example:\n"
                "`/addforcesub -1001234567890 https://t.me/+ABC123`\n\n"
                "💡 Get channel ID by forwarding a message from channel to @userinfobot",
                parse_mode=ParseMode.MARKDOWN
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
            await update.message.reply_text("❌ Invalid link format!")
            return
            
    except Exception as e:
        logger.error(f"Error getting channel: {e}")
        await update.message.reply_text(
            "❌ Cannot access channel!\n\n"
            "Make sure:\n"
            "1. Bot is admin in the channel\n"
            "2. Link is correct\n"
            "3. Channel exists"
        )
        return
    
    # Check if bot is admin in target channel
    try:
        bot_member = await context.bot.get_chat_member(channel_id, context.bot.id)
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await update.message.reply_text(f"❌ Make me admin in **{channel_title}** first!", parse_mode=ParseMode.MARKDOWN)
            return
    except:
        await update.message.reply_text("❌ Cannot check bot permissions in channel!")
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
            f"✅ **Force Subscribe Added!**\n\n"
            f"📌 Group: `{main_chat.title}`\n"
            f"📢 Channel: `{channel_title}`\n"
            f"🔗 Link: {invite_link}\n\n"
            f"Now users must join this channel to chat!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Failed to add! Maybe already exists.")

async def add_force_sub_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add private channel with ID"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Use this command in a group!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/addprivateforcesub <channel_id> <invite_link>`\n\n"
            "**Example:**\n"
            "`/addprivateforcesub -1001234567890 https://t.me/+ABC123`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        channel_id = int(context.args[0])
        invite_link = context.args[1]
    except ValueError:
        await update.message.reply_text("❌ Invalid channel ID! Must be a number.")
        return
    
    # Get channel info
    try:
        channel = await context.bot.get_chat(channel_id)
        channel_title = channel.title
    except Exception as e:
        await update.message.reply_text(
            "❌ Cannot access channel!\n"
            "Make sure bot is admin in the channel."
        )
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
            f"✅ **Private Channel Added!**\n\n"
            f"📢 Channel: `{channel_title}`\n"
            f"🆔 ID: `{channel_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Failed to add!")

async def remove_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a force subscribe channel"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Use this command in a group!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not context.args:
        # Show list with IDs
        channels = ForceSubDB.get_force_subs(update.effective_chat.id)
        if not channels:
            await update.message.reply_text("📭 No force subscribe channels set!")
            return
        
        text = "📝 **To remove, use:**\n`/removeforcesub <channel_id>`\n\n**Current Channels:**\n"
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
        await update.message.reply_text("✅ Channel removed from force subscribe!")
    else:
        await update.message.reply_text("❌ Failed to remove!")

async def list_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all force subscribe channels"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Use this command in a group!")
        return
    
    channels = ForceSubDB.get_force_subs(update.effective_chat.id)
    
    if not channels:
        await update.message.reply_text(
            "📭 **No Force Subscribe Channels**\n\n"
            "Use `/addforcesub` to add channels!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = f"📋 **Force Subscribe Channels**\n"
    text += f"👥 Group: `{update.effective_chat.title}`\n\n"
    
    for idx, ch in enumerate(channels, 1):
        text += f"**{idx}.** {ch.get('target_chat_title', 'Unknown')}\n"
        text += f"   🆔 `{ch['target_chat_id']}`\n"
        text += f"   🔗 {ch['target_link']}\n\n"
    
    text += f"📊 Total: {len(channels)} channel(s)"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def clear_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all force subscribe channels"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("⚠️ Use this command in a group!")
        return
    
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    success = ForceSubDB.remove_all_force_subs(update.effective_chat.id)
    
    if success:
        await update.message.reply_text("✅ All force subscribe channels removed!")
    else:
        await update.message.reply_text("❌ Failed to clear!")

# ============ MESSAGE HANDLER ============
async def check_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user is subscribed to all required channels"""
    # Ignore private chats
    if update.effective_chat.type == "private":
        return
    
    # Ignore if no message
    if not update.message:
        return
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Ignore bots
    if user.is_bot:
        return
    
    # Skip admins
    if await is_admin(update, context, user.id):
        return
    
    # Get force sub channels for this group
    channels = ForceSubDB.get_force_subs(chat.id)
    
    # No force sub set
    if not channels:
        return
    
    # Check subscription
    is_subscribed, not_joined = await check_subscription(context, user.id, channels)
    
    if is_subscribed:
        return  # User is subscribed, allow message
    
    # User not subscribed - delete message and warn
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Cannot delete message: {e}")
    
    # Create warning message
    warning_text = (
        f"⚠️ **Hey {user.first_name}!**\n\n"
        f"You must join the following channel(s) to send messages here:\n\n"
    )
    
    for idx, ch in enumerate(not_joined, 1):
        warning_text += f"{idx}. **{ch.get('target_chat_title', 'Channel')}**\n"
    
    warning_text += "\n👇 Click buttons below to join, then click verify!"
    
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
        
        # Get force sub channels
        channels = ForceSubDB.get_force_subs(chat_id)
        
        if not channels:
            await query.answer("✅ No restrictions!", show_alert=True)
            await query.message.delete()
            return
        
        # Check subscription
        is_subscribed, not_joined = await check_subscription(context, user.id, channels)
        
        if is_subscribed:
            await query.answer("✅ Verified! You can now chat.", show_alert=True)
            try:
                await query.message.delete()
            except:
                pass
        else:
            channels_names = ", ".join([ch.get('target_chat_title', 'Channel') for ch in not_joined])
            await query.answer(
                f"❌ Please join: {channels_names}",
                show_alert=True
            )

# ============ MAIN ============
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found!")
        return
    
    # Start health server
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Build application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
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
    
    print("🚀 Force Subscribe Bot Started!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
