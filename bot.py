#!/usr/bin/env python3
import os, re, html, logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Validate environment variables
if not all([BOT_TOKEN, ADMIN_ID, CHANNEL_ID]):
    raise ValueError("Missing required environment variables. Please check your .env file")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID must be an integer")

# Setup logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", 
    level=logging.INFO
)
log = logging.getLogger("GDrivePoster")

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    """Converts ANY g-drive share-link to direct-download link"""
    # Check if it's already a direct link
    if "uc?id=" in url or "uc?export=download" in url:
        return url
        
    # Extract file ID from various Google Drive URL formats
    patterns = [
        r"/d/([-\w]{25,})",
        r"id=([-\w]{25,})",
        r"folders/([-\w]{25,})",
        r"([-\w]{25,})"  # standalone ID
    ]
    
    file_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            break
            
    if not file_id:
        raise ValueError("Invalid G-Drive link: Could not extract file ID")
        
    return f"https://drive.google.com/uc?id={file_id}&export=download"

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🤖 Hello {user.first_name}!\n\n"
        "I'm a bot for posting Google Drive videos to channels.\n\n"
        "Use /postdrive to post content (admin only)."
    )

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Admin only.")
        log.warning(f"Unauthorized access attempt by user {user.id}")
        return
        
    if len(ctx.args) < 3:
        await update.message.reply_text(
            "✅ Usage:\n"
            "<code>/postdrive Title MovieDriveLink ThumbDriveLink [caption]</code>\n\n"
            "Example:\n"
            "<code>/postdrive \"My Video\" https://drive.google.com/... https://drive.google.com/... \"Check out this video!\"</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        title = html.escape(ctx.args[0])
        movie = gdrive_direct(ctx.args[1])
        thumb = gdrive_direct(ctx.args[2])
        caption = html.escape(" ".join(ctx.args[3:])) if len(ctx.args) > 3 else title
        
        log.info(f"Attempting to post: {title}")
        log.info(f"Movie URL: {movie}")
        log.info(f"Thumb URL: {thumb}")
        
        # Validate URLs
        for url in [movie, thumb]:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL: {url}")

        msg = await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=movie,
            thumbnail=thumb,
            caption=caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            read_timeout=300,
            write_timeout=300,
            connect_timeout=60,
        )
        
        await update.message.reply_text("✅ Drive video posted successfully!")
        log.info(f"Posted {title} -> {msg.link}")
        
    except Exception as exc:
        error_msg = f"❌ Error:\n<code>{html.escape(str(exc))}</code>"
        await update.message.reply_text(error_msg, parse_mode=ParseMode.HTML)
        log.exception("postdrive failed")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error(f"Exception while handling an update: {context.error}")

def main():
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("postdrive", postdrive))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        log.info("Bot starting…")
        app.run_polling()
        
    except Exception as e:
        log.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
