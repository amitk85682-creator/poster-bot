#!/usr/bin/env python3
import os
import re
import html
import logging
import threading
import asyncio
from flask import Flask
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from urllib.parse import urlparse

# --- Flask Web Server (to keep Render's Free Web Service alive) ---
app = Flask(__name__)

@app.route('/')
def hello_world():
    # This is the endpoint Render will check to see if the service is live.
    return 'Bot is alive and running!'

def run_web_server():
    # Render provides the PORT environment variable.
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- Telegram Bot ---
# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Validate environment variables
if not all([BOT_TOKEN, ADMIN_ID, CHANNEL_ID]):
    raise ValueError("Missing required environment variables. Please check your .env file.")
try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID in your .env file must be a valid integer.")

# Setup logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("HybridVideoPoster")

# Helper Functions
def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    patterns = [r"/d/([-\w]{25,})", r"id=([-\w]{25,})", r"folders/([-\w]{25,})"]
    file_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1); break
    if not file_id:
        raise ValueError("Invalid G-Drive link: Could not extract file ID.")
    return f"https://drive.google.com/uc?id={file_id}&export=download"

# Command Handlers
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is running! Use /postdrive or /postvideo.")

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only."); return
    # For postdrive, the correct argument name is 'thumbnail'
    if len(ctx.args) < 3:
        await update.message.reply_text("✅ <b>Usage:</b>\n<code>/postdrive \"Title\" GDriveLink ThumbLink</code>", parse_mode=ParseMode.HTML); return
    try:
        title = ctx.args[0]
        await update.message.reply_text(f"⏳ Posting '{title}' from G-Drive...")
        await ctx.bot.send_video(
            chat_id=CHANNEL_ID, video=gdrive_direct(ctx.args[1]), thumbnail=gdrive_direct(ctx.args[2]),
            caption=f"🎬 <b>{html.escape(title)}</b>", parse_mode=ParseMode.HTML, supports_streaming=True,
            read_timeout=300, write_timeout=300, connect_timeout=60
        )
        await update.message.reply_text(f"✅ Posted '{title}' successfully!")
    except Exception as exc:
        await update.message.reply_text(f"❌ Error:\n<code>{html.escape(str(exc))}</code>", parse_mode=ParseMode.HTML)

async def post_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only."); return
    if len(ctx.args) != 3:
        await update.message.reply_text("✅ <b>Usage:</b>\n<code>/postvideo Name video_id thumb_id</code>", parse_mode=ParseMode.HTML); return
    try:
        movie_name = ctx.args[0].replace("_", " ")
        await update.message.reply_text(f"⏳ Posting '{movie_name}' from File ID...")
        # ==========================================================
        # THE FIX IS HERE: changed 'thumb' to 'thumbnail'
        # ==========================================================
        await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=ctx.args[1],
            thumbnail=ctx.args[2], # <-- Corrected from 'thumb'
            caption=f"🎬 <b>{html.escape(movie_name)}</b>",
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ Posted '{movie_name}' successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n<code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error(f"Exception while handling an update:", exc_info=context.error)

def run_bot():
    """Starts the bot in the main thread."""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("postdrive", postdrive))
        app.add_handler(CommandHandler("postvideo", post_video))
        app.add_error_handler(error_handler)
        log.info("Bot starting in polling mode...")
        app.run_polling()
    except Exception as e:
        log.critical(f"Failed to start bot: {e}")
        raise

# --- Main Execution ---
if __name__ == "__main__":
    log.info("Starting application...")
    
    # Run the web server in a separate, secondary thread
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True  # Allows the main bot to exit gracefully
    web_thread.start()
    
    # Run the bot in the main thread, as required by the library
    run_bot()

