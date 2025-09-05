import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_USER_ID", 0))
CHANNEL_ID = os.environ.get("CHANNEL_ID")
PORT = int(os.environ.get('PORT', 8080))
# Render.com आपको एक URL देता है, उसे यहाँ डालें या Environment Variable से लें
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL") 

# Configuration validation
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID environment variable is required")

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

# --- Bot and Flask Setup ---
async def main():
    """Sets up the bot application and webhook."""
    # PTB Application को बनाएं
    application = Application.builder().token(TOKEN).build()

    # Handlers जोड़ें
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("postvideo", post_video))
    
    # Webhook सेट करें
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
        print(f"Webhook set to {WEBHOOK_URL}/{TOKEN}")
    else:
        print("WEBHOOK_URL not found, running in polling mode for local testing.")
        # यह हिस्सा सिर्फ लोकल टेस्टिंग के लिए है, Render पर नहीं चलेगा
        await application.run_polling(allowed_updates=Update.ALL_TYPES)
        return

    # इस एप्लीकेशन को ग्लोबल करें ताकि Flask इसे इस्तेमाल कर सके
    # (यह एक आसान तरीका है, बड़े ऐप्स के लिए और बेहतर तरीके हो सकते हैं)
    flask_app.ptb_app = application
    
    # यह सुनिश्चित करें कि बॉट ठीक से शुरू हो गया है
    async with application:
        await application.start()
        # Flask ऐप को चलाएं (यह Gunicorn द्वारा किया जाएगा, इसलिए यह लाइन Render पर नहीं चलेगी)
        # flask_app.run(host='0.0.0.0', port=PORT, debug=False)
        # We need to keep the main async function running
        await asyncio.Event().wait()


# --- Flask App ---
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "Poster Bot is running with Webhooks!"

@flask_app.route(f'/{TOKEN}', methods=['POST'])
async def telegram_webhook():
    """यह फंक्शन टेलीग्राम से आने वाले सभी अपडेट्स को हैंडल करता है।"""
    update_data = request.get_json()
    update = Update.de_json(data=update_data, bot=flask_app.ptb_app.bot)
    await flask_app.ptb_app.process_update(update)
    return 'ok'

if __name__ == "__main__":
    # नया event loop बनाएं और main() फंक्शन चलाएं
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # अगर लूप पहले से चल रहा है (जैसे कुछ IDEs में), तो एक नया task बनाएं
        loop.create_task(main())
    else:
        # वरना, लूप को चलाएं
        loop.run_until_complete(main())
