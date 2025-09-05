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

# --- Flask App for Keep-Alive ---
flask_app = Flask('')
@flask_app.route('/')
def home():
    return "Poster Bot is running!"

def run_flask():
    from waitress import serve
    serve(flask_app, host='0.0.0.0', port=PORT)

# --- Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "नमस्ते! मैं आपका Video Poster Bot हूँ।\n"
        "मुझे मूवी का नाम, वीडियो का file_id, और थंबनेल का file_id दें, और मैं इसे आपके चैनल पर पोस्ट कर दूँगा।\n\n"
        "इस्तेमाल करें: /postvideo <मूवी का नाम> <वीडियो_id> <थंबनेल_id>"
    )

async def post_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Posts a video with a custom thumbnail to the specified channel."""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("माफ़ कीजियेगा, यह कमांड सिर्फ एडमिन के लिए है।")
        return

    args = context.args
    if not args or len(args) < 3:
        await update.message.reply_text(
            "गलत फॉर्मेट! ऐसे इस्तेमाल करें:\n"
            "/postvideo \"मूवी का नाम\" <वीडियो_file_id> <थंबनेल_file_id>\n\n"
            "ध्यान दें: अगर मूवी के नाम में स्पेस है, तो उसे \" \" के अंदर लिखें।"
        )
        return

    # The last two arguments are file IDs, everything before is the movie name
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
        await update.message.reply_text(f"कुछ एरर आ गया! वीडियो पोस्ट नहीं हो पाया। 😢\n\nएरर: {e}")

# --- Main Execution Block ---
async def main():
    """Starts the bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("postvideo", post_video))

    print("Poster Bot is starting polling...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(main())
