import os
import logging
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application,
CommandHandler,
MessageHandler,
CallbackQueryHandler,
filters,
ContextTypes,
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
[InlineKeyboardButton(" ﺗﺤﻤﯿﻞ ﻓﯿﺪﯾﻮ", callback_data="menu_video")],
[InlineKeyboardButton(" ﺑﺤﺚ ﻋﻦ ﻣﻤﺜﻞ ﺑﺎﻟﺼﻮرة", callback_data="menu_actor")],
[InlineKeyboardButton(" ﻣﺴﺎﻋﺪة", callback_data="menu_help")],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(
,":اﺧﺘﺮ ﻣﺎ ﺗﺮﯾﺪ ﻣﻦ اﻷزرار أدﻧﺎهMBRxBot*\n\n* أھﻼ ً! أﻧﺎ "
parse_mode="Markdown",
reply_markup=reply_markup,
)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if query.data == "menu_video":
await query.message.reply_text(
\n• Twitter / X\n• TikTok\n• Instagram\:أرﺳﻞ راﺑﻂ اﻟﻔﯿﺪﯾﻮ ﻣﻦn\n\*ﺗﺤﻤﯿﻞ ﻓﯿﺪﯾﻮ* "
parse_mode="Markdown",
)
context.user_data["mode"] = "video"
elif query.data == "menu_actor":
await query.message.reply_text(
ً Google Lens أرﺳﻞ ﺻﻮرة اﻟﻤﻤﺜﻞ/اﻟﻤﻤﺜﻠﺔ وﺳﺄﻓﺘﺢ ﻟﻚ ﺑﺤﺚn\n\*ﺑﺤﺚ ﻋﻦ ﻣﻤﺜﻞ ﺑﺎﻟﺼmode="Markdown",
ة
)
context.user_data["mode"] = "actor"
elif query.data == "menu_help":
keyboard = [[InlineKeyboardButton(" رﺟﻮع", callback_data="menu_back")]]
await query.message.reply_text(
ﺛﻢ أرﺳﻞ اﻟﺼﻮرة n\اﺿﻐﻂ *ﺗﺤﻤﯿﻞ ﻓﯿﺪﯾﻮ* ﺛﻢ أرﺳﻞ اﻟﺮاﺑﻂ n\n\*:ﻛﯿﻔﯿﺔ اﻻﺳﺘﺨﺪام* "
parse_mode="Markdown",
reply_markup=InlineKeyboardMarkup(keyboard),
)
elif query.data == "menu_back":
keyboard = [
[InlineKeyboardButton(" ﺗﺤﻤﯿﻞ ﻓﯿﺪﯾﻮ", callback_data="menu_video")],
[InlineKeyboardButton(" ﺑﺤﺚ ﻋﻦ ﻣﻤﺜﻞ ﺑﺎﻟﺼﻮرة", callback_data="menu_actor")],
[InlineKeyboardButton(" ﻣﺴﺎﻋﺪة", callback_data="menu_help")],
]
await query.message.reply_text(
,":اﺧﺘﺮ ﻣﺎ ﺗﺮﯾﺪ"
reply_markup=InlineKeyboardMarkup(keyboard),
)
SUPPORTED_DOMAINS = ("twitter.com", "x.com", "tiktok.com", "instagram.com")
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text or ""
if any(domain in text for domain in SUPPORTED_DOMAINS):
await download_video(update, context, text.strip())
else:
)".ﻻﺧﺘﯿﺎر اﻟﻤﯿﺰة اﻟﺘﻲ ﺗﺮﯾﺪھﺎ start/ اﺳﺘﺨﺪم "(await update.message.reply_text
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
)"...ﺟﺎري اﻟﺘﺤﻤﯿﻞ "(msg = await update.message.reply_text
ydl_opts = {
"format": "best[filesize<50M]/best",
"outtmpl": "/tmp/%(id)s.%(ext)s",
"quiet": True,
"no_warnings": True,
}
try:
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(url, download=True)
file_path = ydl.prepare_filename(info)
await msg.delete()
await update.message.reply_video(
video=open(file_path, "rb"),
,"!ﺗﻢ اﻟﺘﺤﻤﯿﻞ ﺑﻨﺠﺎح "=caption
)
os.remove(file_path)
except Exception as e:
logger.error(f"Download error: {e}")
await msg.edit_text(
ﻤﮫ أﻞ ﻣﻦ 50 •n\أن اﻟﻔﯿﺪﯾﻮ ﻏﯿﺮ ﺧﺎص •n\أن اﻟﺮاﺑﻂ ﺻﺤﯿﺢ •n\:ﻓﺸﻞ اﻟﺘﺤﻤﯿﻞ. ﺗﺄﻛﻣﻦ "
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
mode = context.user_data.get("mode", "")
if mode != "actor":
keyboard = [[InlineKeyboardButton(" اﺑﺤﺚ ﻋﻦ ھﺬا اﻟﻤﻤﺜﻞ", callback_data="do_lens")]]
context.user_data["pending_photo"] = update.message.photo[-1].file_id
await update.message.reply_text(
,"اﺳﺘﻠﻤﺖ اﻟﺼﻮرة! ھﻞ ﺗﺮﯾﺪ اﻟﺒﺤﺚ ﻋﻦ اﻟﻤﻤﺜﻞ؟ "
reply_markup=InlineKeyboardMarkup(keyboard),
)
return
await send_lens_link(update, context)
async def send_lens_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
photo = update.message.photo[-1] if update.message.photo else None
if not photo:
)".ﻟﻢ أﺗﻤﻜﻦ ﻣﻦ ﻗﺮاءة اﻟﺼﻮرة "(await update.message.reply_text
return
file = await context.bot.get_file(photo.file_id)
file_url = file.file_path
lens_url = f"https://lens.google.com/uploadbyurl?url={file_url}"
keyboard = [[InlineKeyboardButton(" اﻓﺘﺢ Google Lens", url=lens_url)]]
await update.message.reply_text(
,":Google Lens اﺿﻐﻂ اﻟﺰر أدﻧﺎه ﻟﻠﺒﺤﺚ ﻋﻦ اﻟﻤﻤﺜﻞ ﻓﻲ "
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data["mode"] = ""
async def lens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
file_id = context.user_data.get("pending_photo")
if not file_id:
)".ﻟﻢ أﺟﺪ اﻟﺼﻮرة، أرﺳﻠﮭﺎ ﻣﺮة أﺧﺮى "(await query.message.reply_text
return
file = await context.bot.get_file(file_id)
file_url = file.file_path
lens_url = f"https://lens.google.com/uploadbyurl?url={file_url}"
keyboard = [[InlineKeyboardButton(" اﻓﺘﺢ Google Lens", url=lens_url)]]
await query.message.reply_text(
,":Google Lens اﺿﻐﻂ اﻟﺰر أدﻧﺎه ﻟﻠﺒﺤﺚ ﻋﻦ اﻟﻤﻤﺜﻞ ﻓﻲ "
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data["pending_photo"] = None
def main():
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(lens_callback, pattern="^do_lens$"))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
logger.info("Bot is running...")
app.run_polling()
if __name__ == "__main__":
main()
