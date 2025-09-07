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
        r"/d/([-\w]{25,})", r"id=([-\w]{25,})", r"folders/([-\w]{25,})"
    ]
    file_id = None
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1); break
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
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ यह कमांड केवल एडमिन के लिए है।"); return
    if len(ctx.args) < 3:
        await update.message.reply_text(
            "✅ <b>Usage:</b>\n<code>/postdrive \"Title\" GDriveLink ThumbLink</code>\n(Note: Only for videos < 50MB).",
            parse_mode=ParseMode.HTML); return
    try:
        title = ctx.args[0]
        caption = f"🎬 <b>{html.escape(title)}</b>"
        await update.message.reply_text("⏳ गूगल ड्राइव से वीडियो पोस्ट किया जा रहा है...")
        await ctx.bot.send_video(
            chat_id=CHANNEL_ID, video=gdrive_direct(ctx.args[1]), thumbnail=gdrive_direct(ctx.args[2]),
            caption=caption, parse_mode=ParseMode.HTML, supports_streaming=True,
            read_timeout=300, write_timeout=300, connect_timeout=60,
        )
        await update.message.reply_text(f"✅ G-Drive वीडियो '{title}' सफलतापूर्वक पोस्ट हो गया!")
    except Exception as exc:
        await update.message.reply_text(f"❌ त्रुटि:\n<code>{html.escape(str(exc))}</code>", parse_mode=ParseMode.HTML)

async def post_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ यह कमांड केवल एडमिन के लिए है।"); return
    if len(ctx.args) != 3:
        await update.message.reply_text(
            "✅ <b>Usage:</b>\n<code>/postvideo Movie_Name video_file_id thumb_file_id</code>\n(Note: For large files on Telegram).",
            parse_mode=ParseMode.HTML); return
    try:
        movie_name = ctx.args[0].replace("_", " ")
        caption = f"🎬 <b>{html.escape(movie_name)}</b>"
        await update.message.reply_text("⏳ File ID से वीडियो पोस्ट किया जा रहा है...")
        await ctx.bot.send_video(
            chat_id=CHANNEL_ID, video=ctx.args[1], thumb=ctx.args[2],
            caption=caption, parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(f"✅ File ID वीडियो '{movie_name}' सफलतापूर्वक पोस्ट हो गया!")
    except Exception as e:
        await update.message.reply_text(f"❌ त्रुटि:\n<code>{html.escape(str(e))}</code>", parse_mode=ParseMode.HTML)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error(f"Exception while handling an update:", exc_info=context.error)

# --- Main Bot Logic (Using Polling - Perfect for Background Worker) ---
def main() -> None:
    """Starts the bot using polling."""
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("postdrive", postdrive))
        app.add_handler(CommandHandler("postvideo", post_video))
        app.add_error_handler(error_handler)
        
        log.info("बॉट Polling मोड में शुरू हो रहा है…")
        app.run_polling()
        
    except Exception as e:
        log.critical(f"बॉट शुरू करने में विफल: {e}")
        raise

if __name__ == "__main__":
    main()
