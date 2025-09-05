import os
import asyncio
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_USER_ID", 0))
CHANNEL_ID = os.environ.get("CHANNEL_ID")
PORT = int(os.environ.get('PORT', 8080))

if not TOKEN or not CHANNEL_ID:
    raise ValueError("Missing TOKEN or CHANNEL_ID")

flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Poster Bot is running!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "नमस्ते! मैं आपका Video Poster Bot हूँ।\n"
        "इस्तेमाल करें: /postvideo <मूवी का नाम> <वीडियो_id> <थंबनेल_id>"
    )

async def post_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("postvideo", post_video))
    
    # Run bot and Flask concurrently
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_polling())
    
    flask_app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    asyncio.run(main())
