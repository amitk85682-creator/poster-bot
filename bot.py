#!/usr/bin/env python3
import os, html, re, logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import gdown

load_dotenv()
BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("GDrivePoster")

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

def gdrive_direct(url: str) -> str:
    """convert any G-Drive share-link to direct-download HTTPS URL"""
    file_id = re.findall(r"[-\w]{25,}", url)[0]
    return f"https://drive.google.com/uc?id={file_id}&export=download"

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 GDrivePoster ready!\nUse /postdrive")

async def postdrive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌  Admin only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "✅  Usage:\n"
            "<code>/postdrive Title https://drive.google.com/... [caption]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    title   = html.escape(ctx.args[0])
    g_link  = ctx.args[1]
    caption = html.escape(" ".join(ctx.args[2:])) if len(ctx.args) > 2 else title

    try:
        direct_url = gdrive_direct(g_link)
        log.info("Streaming: %s", direct_url)

        msg = await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=direct_url,          # Telegram itself fetches from Drive
            caption=caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            read_timeout=300,          # 5 min enough for multi-GB
            write_timeout=300,
            connect_timeout=60,
        )
        await update.message.reply_text("✅  Drive video posted!")
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
