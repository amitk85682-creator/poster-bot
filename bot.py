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
# Load environment variables from .env file
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Validate that all required environment variables are present
if not all([BOT_TOKEN, ADMIN_ID, CHANNEL_ID]):
    raise ValueError("Missing required environment variables. Please create a .env file with BOT_TOKEN, ADMIN_ID, and CHANNEL_ID.")

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
    """Checks if a user ID belongs to the admin."""
    return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    """Converts various Google Drive share-links to a direct download link."""
    # Regular expressions to find the file ID in different G-Drive URL formats
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
    """Handles the /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 नमस्ते {user.first_name}!\n\n"
        "मैं एक हाइब्रिड वीडियो पोस्टर बॉट हूँ।\n\n"
        "🔹 /postdrive: छोटी वीडियो (<50MB) को G-Drive लिंक से पोस्ट करें।\n"
        "🔹 /postvideo: बड़ी वीडियो को file_id से पोस्ट करें।\n\n"
        "ये कमांड केवल एडमिन के लिए हैं।"
    )

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Posts a video from a Google Drive URL. Best for files < 50MB."""
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
        # Use optional caption or default to the title
        caption_text = " ".join(ctx.args[3:]) if len(ctx.args) > 3 else title
        
        # Sanitize for HTML
        caption = f"🎬 <b>{html.escape(title)}</b>\n\n{html.escape(caption_text)}"

        log.info(f"Attempting to post from G-Drive: {title}")
        await update.message.reply_text("⏳ गूगल ड्राइव से वीडियो पोस्ट किया जा रहा है... इसमें कुछ समय लग सकता है।")

        await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=movie_url,
            thumbnail=thumb_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            read_timeout=300,  # Increased timeouts for downloading
            write_timeout=300,
            connect_timeout=60,
        )
        
        await update.message.reply_text(f"✅ G-Drive वीडियो '{title}' सफलतापूर्वक पोस्ट हो गया!")
        log.info(f"Successfully posted {title} from G-Drive.")
        
    except Exception as exc:
        error_msg = f"❌ त्रुटि:\n<code>{html.escape(str(exc))}</code>\n\nयह अक्सर तब होता है जब फ़ाइल 50 MB से बड़ी हो या G-Drive लिंक गलत हो।"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)
        log.exception("postdrive failed")

async def post_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Posts a large video using file_id. Best for movies."""
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
        # Replace underscores with spaces for the title
        movie_name = ctx.args[0].replace("_", " ")
        video_file_id = ctx.args[1]
        thumb_file_id = ctx.args[2]

        caption = f"🎬 <b>{html.escape(movie_name)}</b>\n\n<i>Posted via FileID</i>"

        log.info(f"Attempting to post via file_id: {movie_name}")
        await update.message.reply_text("⏳ File ID से वीडियो पोस्ट किया जा रहा है...")

        await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=video_file_id,
            thumb=thumb_file_id,
            caption=caption,
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ File ID वीडियो '{movie_name}' सफलतापूर्वक पोस्ट हो गया!")
        log.info(f"Successfully posted {movie_name} using file_id.")

    except Exception as e:
        error_msg = f"❌ त्रुटि:\n<code>{html.escape(str(e))}</code>\n\nकृपया सुनिश्चित करें कि file_id और चैनल का नाम सही है।"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)
        log.exception("post_video failed")


# --- Main Bot Logic ---
def main():
    """Starts the bot."""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("postdrive", postdrive))
        app.add_handler(CommandHandler("postvideo", post_video)) # New handler
        
        log.info("बॉट शुरू हो रहा है…")
        app.run_polling()
        
    except Exception as e:
        log.critical(f"बॉट शुरू करने में विफल: {e}")
        raise

if __name__ == "__main__":
    main()
