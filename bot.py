#!/usr/bin/env python3
"""
MyVideoPoster
A simple admin-only bot that can:
  /start  – alive check
  /postvideo <title> <video_file_id> <thumb_file_id> [caption]
Video goes to CHANNEL_ID with custom thumbnail.
"""

import os, html, logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

load_dotenv()          # reads .env file
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID"))
CHANNEL_ID= os.getenv("CHANNEL_ID")

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
            parse_mode=ParseMode.HTML
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
        await update.message.reply_text(f"❌  Error:\n<code>{exc}</code>", parse_mode=ParseMode.HTML)
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
--------------------------------------------------

--------------------------------------------------
5. इंस्टॉल + रन (Linux / Windows PowerShell)
# 1. फोल्डर में जाएँ
cd myvideoposter

# 2. वर्चुअल एनवायरनमेंट (ऑप्शनल)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. डिपेंडेंसी
pip install -r requirements.txt

# 4. बॉट चलाएँ
python bot.py
--------------------------------------------------

--------------------------------------------------
6. इस्तेमाल (वही प्रोसेस)
1. मूवी और थंबनेल फोटो किसी प्राइवेट चैट/चैनल पर अपलोड करें।  
2. @JsonDumpBot से दोनों file_id निकालें।  
3. बॉट को प्राइवेट में:  
   `/postvideo Dobaaraa BQACAgQAAxkB…video… AgACAgQAAxkB…thumb… यहाँ कैप्शन`  
4. वीडियो आपके चैनल पर कस्टम थंबनेल के साथ पोस्ट हो जाएगा!

बस! कोई और फ़ाइल/कोड नहीं चाहिए। अगर कोई एरर आए तो लॉग टर्मिनल में दिखेगा – वही कॉपी-पेस्ट करके बताइए, मैं फिक्स कर दूँगा।
