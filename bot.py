#!/usr/bin/env python3
import os, re, html, logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

load_dotenv()
BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")   # @YourChannel या -100...

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
log = logging.getLogger("GDrivePoster")

def is_admin(uid: int) -> bool: return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    """converts ANY g-drive share-link to direct-download link"""
    match = re.search(r"[-\w]{25,}", url)
    if not match: raise ValueError("Invalid G-Drive link")
    return f"https://drive.google.com/uc?id={match.group(0)}&export=download"

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Ready!\nUse /postdrive")

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌  Admin only.")
        return
    if len(ctx.args) < 3:                      # title + movie_link + thumb_link
        await update.message.reply_text(
            "✅  Usage:\n"
            "<code>/postdrive Title MovieDriveLink ThumbDriveLink [caption]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    title  = html.escape(ctx.args[0])
    movie  = gdrive_direct(ctx.args[1])
    thumb  = gdrive_direct(ctx.args[2])
    caption= html.escape(" ".join(ctx.args[3:])) if len(ctx.args) > 3 else title

    try:
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
        await update.message.reply_text("✅  Drive video posted with thumbnail!")
        log.info("Posted %s -> %s", title, msg.link)
    except Exception as exc:
        await update.message.reply_text(f"❌  Error:\n<code>{exc}</code>", parse_mode=ParseMode.HTML)
        log.exception("postdrive failed")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("postdrive", postdrive))
    log.info("Bot starting…")
    app.run_polling()

if __name__ == "__main__":
    main()
