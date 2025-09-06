import os
import logging
from typing import Final
from dotenv import load_dotenv
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Load environment variables
load_dotenv()

# Configuration from environment variables
BOT_TOKEN: Final = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id_str) for id_str in os.getenv('ADMIN_IDS', '').split(',') if id_str]
TARGET_CHANNEL: Final = os.getenv('TARGET_CHANNEL', '')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text('नमस्ते! मैं MyVideoPoster बॉट हूँ। /postvideo कमांड का उपयोग करें।')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
    Available Commands:
    /start - बॉट शुरू करें
    /help - सहायता देखें
    /postvideo <movie_name> <video_file_id> <thumbnail_file_id> - कस्टम थंबनेल के साथ वीडियो पोस्ट करें
    """
    await update.message.reply_text(help_text)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS

async def postvideo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /postvideo command"""
    user_id = update.effective_user.id
    
    # Admin check
    if not is_admin(user_id):
        await update.message.reply_text("⚠️ अनुमति denied. केवल administrators इस कमांड का उपयोग कर सकते हैं।")
        return
    
    # Validate arguments
    if len(context.args) < 3:
        await update.message.reply_text("❌ Invalid format. Use: /postvideo <movie_name> <video_file_id> <thumbnail_file_id>")
        return
    
    movie_name = context.args[0]
    video_file_id = context.args[1]
    thumbnail_file_id = context.args[2]
    
    try:
        # Send video with custom thumbnail
        await context.bot.send_video(
            chat_id=TARGET_CHANNEL,
            video=video_file_id,
            thumb=thumbnail_file_id,
            caption=movie_name,
            supports_streaming=True
        )
        
        await update.message.reply_text("✅ वीडियो सफलतापूर्वक पोस्ट किया गया!")
        
    except Exception as e:
        error_message = f"❌ Error posting video: {str(e)}"
        logger.error(error_message)
        await update.message.reply_text(error_message)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text("❌ An error occurred while processing your request.")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")
    
    if not ADMIN_IDS:
        logger.warning("No ADMIN_IDS set - anyone will be able to use admin commands")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("postvideo", postvideo_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
