import os
import threading
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_USER_ID", 0))
CHANNEL_ID = os.environ.get("CHANNEL_ID")
PORT = int(os.environ.get('PORT', 8080))

# Configuration validation
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")

# --- Flask App ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Poster Bot is running!"

# --- Telegram Bot Logic ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "नमस्ते! मैं आपका Video Poster Bot हूँ।\n"
        "इस्तेमाल करें: /postvideo <मूवी का नाम> <वीडियो_id> <थंबनेल_id>"
    )

async def post_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Posts a video with a custom thumbnail."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("माफ़ कीजियेगा, यह कमांड सिर्फ एडमिन के लिए है।")
        return

    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "गलत फॉर्मेट! /postvideo \"मूवी का नाम\" <वीडियो_id> <थंबनेल_id>"
        )
        return
    
    thumbnail_file_id = args[-1]
    video_file_id = args[-2]
    movie_name = " ".join(args[:-2])

    try:
        await context.bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_file_id,
            thumb=thumbnail_file_id,
            caption=f"🎬 **{movie_name}**\n\n*Join for more updates!*",
            parse_mode='Markdown'
        )
        await update.message.reply_text(f"बढ़िया! '{movie_name}' आपके चैनल पर सफलतापूर्वक पोस्ट हो गया है। ✅")
    except Exception as e:
        print(f"Error posting video: {e}")
        await update.message.reply_text(f"कुछ एरर आ गया! 😢\nएरर: {e}")

# --- Bot Runner Function ---
def run_bot_polling():
    """Sets up and runs the bot's polling loop."""
    print("Bot polling thread started.")
    
    # नया event loop बनाएं और सेट करें
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("postvideo", post_video))
        
        print("Poster Bot is starting polling...")
        loop.run_until_complete(application.run_polling(allowed_updates=Update.ALL_TYPES))
    except Exception as e:
        print(f"Bot polling error: {e}")
    finally:
        loop.close()

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting bot in a background thread...")
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    
    # Flask ऐप चलाएं
    flask_app.run(host='0.0.0.0', port=PORT, debug=False)
