#!/usr/bin/env python3
"""
MyVideoPoster
A simple admin-only bot that can:
  /start      – alive check
  /postvideo  – post video with custom thumbnail
"""

import os
import html
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

load_dotenv()

BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = int(os.getenv("ADMIN_ID"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("MyVideoPoster")

# ---------- helpers ----------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ---------- handlers ----------
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 MyVideoPoster is alive!\nUse /postvideo to upload.")

async def postvideo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌  Admin only.")
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "✅  Usage:\n"
            "<code>/postvideo Title video_file_id thumb_file_id [caption]</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    title   = html.escape(ctx.args[0])
    vid_fid = ctx.args[1]
    thm_fid = ctx.args[2]
    caption = html.escape(" ".join(ctx.args[3:])) if len(ctx.args) > 3 else title

    try:
        msg = await ctx.bot.send_video(
            chat_id=CHANNEL_ID,
            video=vid_fid,
            thumbnail=thm_fid,
            caption=caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
        )
        await update.message.reply_text("✅  Posted with custom thumbnail!")
        log.info("Posted video %s -> %s", title, msg.link)
    except Exception as exc:
        await update.message.reply_text(
            f"❌  Error:\n<code>{exc}</code>", parse_mode=ParseMode.HTML
        )
        log.exception("postvideo failed")

# ---------- main ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("postvideo", postvideo))
    log.info("Bot starting…")
    app.run_polling()

if __name__ == "__main__":
    main()
