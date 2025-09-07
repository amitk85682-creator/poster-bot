#!/usr/bin/env python3
import os
import re
import html
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from urllib.parse import urlparse

# --- Environment Variable Setup ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not all([BOT_TOKEN, ADMIN_ID, CHANNEL_ID]):
    raise ValueError("Missing required environment variables. Please check your .env file.")
try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID in your .env file must be a valid integer.")

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("HybridVideoPoster")

# --- Helper Functions ---
def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    patterns = [
        r"/d/([-\w]{25,})",
        r"id=([-\w]{25,})",
        r"folders/([-\w]{25,})"
    ]
    file_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            break
    if not file_id:
        raise ValueError("Invalid G-Drive link: Could not extract file ID.")
    return f"https://drive.google.com/uc?id={file_id}&export=download"

# --- Command Handlers ---
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 नमस्ते {user.first_name}!\n\n"
        "मैं एक हाइब्रिड वीडियो पोस्टर बॉट हूँ।\n\n"
        "🔹 /postdrive: छोटी वीडियो (<50MB) को G-Drive लिंक से पोस्ट करें।\n"
        "🔹 /postvideo: बड़ी वीडियो को file_id से पोस्ट करें।\n\n"
        "ये कमांड केवल एडमिन के लिए हैं।"
    )

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        log.warning(f"Unauthorized /postdrive attempt by user {user.id}")
        await update.message.reply_text("❌ यह कमांड केवल एडमिन के लिए है।")
        return
        
    if len(ctx.args) < 3:
        await update.message.reply_text(
            "✅ **Usage for G-Drive Post:**\n"
            "<code>/postdrive \"Title\" MovieDriveLink ThumbDriveLink [Optional Caption]</code>\n\n"
            "<b>Note:</b> This method only works for videos under 50MB.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        title = ctx.args[0]
        movie_url = gdrive_direct(ctx.args[1])
        thumb_url = gdrive_direct(ctx.args[2])
        caption_text = " ".join(ctx.args[3:]) if len(ctx.args) > 3 else title
        caption = f"🎬 <b>{html.escape(title)}</b>\n\n{html.escape(caption_text)}"
        log.info(f"Attempting to post from G-Drive: {title}")
        await update.message.reply_text("⏳ गूगल ड्राइव से वीडियो पोस्ट किया जा रहा है...")

        await ctx.bot.send_video(
            chat_id=CHANNEL_ID, video=movie_url, thumbnail=thumb_url,
            caption=caption, parse_mode=ParseMode.HTML, supports_streaming=True,
            read_timeout=300, write_timeout=300, connect_timeout=60,
        )
        await update.message.reply_text(f"✅ G-Drive वीडियो '{title}' सफलतापूर्वक पोस्ट हो गया!")
        log.info(f"Successfully posted {title} from G-Drive.")
    except Exception as exc:
        error_msg = f"❌ त्रुटि:\n<code>{html.escape(str(exc))}</code>\n\nयह अक्सर तब होता है जब फ़ाइल 50 MB से बड़ी हो या G-Drive लिंक गलत हो।"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)
        log.exception("postdrive failed")

async def post_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        log.warning(f"Unauthorized /postvideo attempt by user {user.id}")
        await update.message.reply_text("❌ यह कमांड केवल एडमिन के लिए है।")
        return

    if len(ctx.args) != 3:
        await update.message.reply_text(
            "✅ **Usage for File ID Post:**\n"
            "<code>/postvideo Movie_Name video_file_id thumb_file_id</code>\n\n"
            "<b>Note:</b> Use this for large files already on Telegram.",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        movie_name = ctx.args[0].replace("_", " ")
        video_file_id = ctx.args[1]
        thumb_file_id = ctx.args[2]
        caption = f"🎬 <b>{html.escape(movie_name)}</b>\n\n<i>Posted via FileID</i>"
        log.info(f"Attempting to post via file_id: {movie_name}")
        await update.message.reply_text("⏳ File ID से वीडियो पोस्ट किया जा रहा है...")
        await ctx.bot.send_video(
            chat_id=CHANNEL_ID, video=video_file_id, thumb=thumb_file_id,
            caption=caption, parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ File ID वीडियो '{movie_name}' सफलतापूर्वक पोस्ट हो गया!")
        log.info(f"Successfully posted {movie_name} using file_id.")
    except Exception as e:
        error_msg = f"❌ त्रुटि:\n<code>{html.escape(str(e))}</code>\n\nकृपया सुनिश्चित करें कि file_id और चैनल का नाम सही है।"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)
        log.exception("post_video failed")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Logs the error."""
    log.error(f"Exception while handling an update:", exc_info=context.error)

# --- Main Bot Logic (Updated for Webhooks) ---
def main() -> None:
    """Starts the bot using webhooks for deployment on a server like Render."""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("postdrive", postdrive))
        app.add_handler(CommandHandler("postvideo", post_video))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # --- Webhook Setup for Render ---
        # Render provides the PORT environment variable.
        # It throws a KeyError if it's not set, which is fine as this script is for deployment.
        PORT = int(os.environ.get("PORT"))

        # RENDER_EXTERNAL_URL is the public URL of your service (e.g., your-app.onrender.com)
        # It is automatically set by Render.
        WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_URL')}/{BOT_TOKEN}"
        
        log.info(f"Starting bot, listening on port {PORT}")
        
        # This command sets the webhook with Telegram and starts the bot's internal web server.
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=WEBHOOK_URL
        )
        
    except KeyError:
        log.critical("ERROR: PORT environment variable not set. This script is intended for webhook deployment on a platform like Render.")
    except Exception as e:
        log.critical(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()

