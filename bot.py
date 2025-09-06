import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import os
from dotenv import load_dotenv

# लॉगिंग सेटअप
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# पर्यावरण चर लोड करें (.env फाइल से)
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# एडमिन चेक करने के लिए डेकोरेटर
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("यह कमांड केवल एडमिन्स के लिए है!")
            return
        return await func(update, context)
    return wrapper

# /start कमांड
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("हाय! मैं MyVideoPoster बॉट हूँ। /postvideo कमांड का उपयोग करके वीडियो और थंबनेल पोस्ट करें।")

# /postvideo कमांड
@admin_only
async def post_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text(
            "उपयोग: /postvideo <मूवी_का_नाम> <वीडियो_file_id> <थंबनेल_file_id>"
        )
        return

    movie_name, video_file_id, thumbnail_file_id = context.args

    try:
        # वीडियो को चैनल पर कस्टम थंबनेल के साथ भेजें
        await context.bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_file_id,
            thumb=thumbnail_file_id,
            caption=f"🎬 {movie_name}",
            supports_streaming=True
        )
        await update.message.reply_text(f"वीडियो '{movie_name}' सफलतापूर्वक {CHANNEL_ID} पर पोस्ट हो गया!")
    except TelegramError as e:
        await update.message.reply_text(f"एरर: {e.message}")
        logger.error(f"वीडियो पोस्ट करने में त्रुटि: {e}")

# एरर हैंडलर
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"अपडेट {update} के कारण त्रुटि: {context.error}")
    if update:
        await update.message.reply_text("कुछ गलत हुआ। कृपया बाद में पुनः प्रयास करें।")

def main():
    # बॉट शुरू करें
    application = Application.builder().token(BOT_TOKEN).build()

    # कमांड्स रजिस्टर करें
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("postvideo", post_video))

    # एरर हैंडलर जोड़ें
    application.add_error_handler(error_handler)

    # बॉट शुरू करें
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
