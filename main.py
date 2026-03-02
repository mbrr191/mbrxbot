import os
import re
import subprocess
import tempfile
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8610242867:AAEQEifZxyjsWvaxCsapUyOVEx1LSmEhVhM"

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TWITTER_PATTERN = re.compile(r'https?://(www\.)?(twitter\.com|x\.com)/\S+/status/\d+')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً! أرسل رابط تويتر/X وأنا أنزل الفيديو لك!")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    match = TWITTER_PATTERN.search(message_text)
    if not match:
        await update.message.reply_text("❌ أرسل رابط تويتر/X صحيح!")
        return
    url = match.group(0)
    status_msg = await update.message.reply_text("⏳ جاري التنزيل...")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "video.%(ext)s")
            result = subprocess.run(
                ["yt-dlp", "-f", "best[ext=mp4]/best", "--merge-output-format", "mp4", "-o", output_path, "--no-playlist", url],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                raise Exception(result.stderr)
            video_file = None
            for f in os.listdir(tmpdir):
                if f.startswith("video"):
                    video_file = os.path.join(tmpdir, f)
                    break
            if not video_file:
                raise Exception("ما اتنزل")
            if os.path.getsize(video_file) > 50 * 1024 * 1024:
                await status_msg.edit_text("⚠️ الفيديو أكبر من 50MB")
                return
            await status_msg.edit_text("📤 جاري الإرسال...")
            with open(video_file, 'rb') as vf:
                await update.message.reply_video(video=vf, caption="✅ تم! | @MBRxBot", supports_streaming=True)
            await status_msg.delete()
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ ما قدرت أنزل الفيديو، تأكد أن التغريدة فيها فيديو")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    print("🤖 البوت شغال!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
