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
logger = logging.getLogger(**name**)

BOT_TOKEN = os.environ.get(“BOT_TOKEN”, “YOUR_BOT_TOKEN_HERE”)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
[InlineKeyboardButton(“🎬 تحميل فيديو”, callback_data=“menu_video”)],
[InlineKeyboardButton(“🔍 بحث عن ممثل بالصورة”, callback_data=“menu_actor”)],
[InlineKeyboardButton(“❓ مساعدة”, callback_data=“menu_help”)],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(
“👋 أهلاً! أنا *MBRxBot*\n\nاختر ما تريد من الأزرار أدناه:”,
parse_mode=“Markdown”,
reply_markup=reply_markup,
)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
if query.data == "menu_video":
    await query.message.reply_text(
        "🎬 *تحميل فيديو*\n\nأرسل رابط الفيديو من:\n• Twitter / X\n• TikTok\n• Instagram\n\nوسأحمله لك مباشرةً ✅",
        parse_mode="Markdown",
    )
    context.user_data["mode"] = "video"

elif query.data == "menu_actor":
    await query.message.reply_text(
        "🔍 *بحث عن ممثل بالصورة*\n\nأرسل صورة الممثل/الممثلة وسأفتح لك بحث Google Lens مباشرةً 🎭",
        parse_mode="Markdown",
    )
    context.user_data["mode"] = "actor"

elif query.data == "menu_help":
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]
    await query.message.reply_text(
        "❓ *كيفية الاستخدام:*\n\n1️⃣ اضغط *تحميل فيديو* ثم أرسل الرابط\n2️⃣ اضغط *بحث عن ممثل* ثم أرسل الصورة\n\n📌 المنصات المدعومة:\nTwitter/X • TikTok • Instagram",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

elif query.data == "menu_back":
    keyboard = [
        [InlineKeyboardButton("🎬 تحميل فيديو", callback_data="menu_video")],
        [InlineKeyboardButton("🔍 بحث عن ممثل بالصورة", callback_data="menu_actor")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="menu_help")],
    ]
    await query.message.reply_text(
        "اختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
```

SUPPORTED_DOMAINS = (“twitter.com”, “x.com”, “tiktok.com”, “instagram.com”)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text or “”
if any(domain in text for domain in SUPPORTED_DOMAINS):
await download_video(update, context, text.strip())
else:
await update.message.reply_text(“ℹ️ استخدم /start لاختيار الميزة التي تريدها.”)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
msg = await update.message.reply_text(“⏳ جاري التحميل…”)
ydl_opts = {
“format”: “best[filesize<50M]/best”,
“outtmpl”: “/tmp/%(id)s.%(ext)s”,
“quiet”: True,
“no_warnings”: True,
}
try:
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
info = ydl.extract_info(url, download=True)
file_path = ydl.prepare_filename(info)
await msg.delete()
await update.message.reply_video(
video=open(file_path, “rb”),
caption=“✅ تم التحميل بنجاح!”,
)
os.remove(file_path)
except Exception as e:
logger.error(f”Download error: {e}”)
await msg.edit_text(
“❌ فشل التحميل. تأكد من:\n• أن الرابط صحيح\n• أن الفيديو غير خاص\n• أن حجمه أقل من 50MB”
)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
mode = context.user_data.get(“mode”, “”)
if mode != “actor”:
keyboard = [[InlineKeyboardButton(“🔍 ابحث عن هذا الممثل”, callback_data=“do_lens”)]]
context.user_data[“pending_photo”] = update.message.photo[-1].file_id
await update.message.reply_text(
“📸 استلمت الصورة! هل تريد البحث عن الممثل؟”,
reply_markup=InlineKeyboardMarkup(keyboard),
)
return
await send_lens_link(update, context)

async def send_lens_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
photo = update.message.photo[-1] if update.message.photo else None
if not photo:
await update.message.reply_text(“❌ لم أتمكن من قراءة الصورة.”)
return
file = await context.bot.get_file(photo.file_id)
file_url = file.file_path
lens_url = f”https://lens.google.com/uploadbyurl?url={file_url}”
keyboard = [[InlineKeyboardButton(“🔍 افتح Google Lens”, url=lens_url)]]
await update.message.reply_text(
“✅ اضغط الزر أدناه للبحث عن الممثل في Google Lens:”,
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data[“mode”] = “”

async def lens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
file_id = context.user_data.get(“pending_photo”)
if not file_id:
await query.message.reply_text(“❌ لم أجد الصورة، أرسلها مرة أخرى.”)
return
file = await context.bot.get_file(file_id)
file_url = file.file_path
lens_url = f”https://lens.google.com/uploadbyurl?url={file_url}”
keyboard = [[InlineKeyboardButton(“🔍 افتح Google Lens”, url=lens_url)]]
await query.message.reply_text(
“✅ اضغط الزر أدناه للبحث عن الممثل في Google Lens:”,
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data[“pending_photo”] = None

def main():
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CallbackQueryHandler(lens_callback, pattern=”^do_lens$”))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
logger.info(“Bot is running…”)
app.run_polling()

if **name** == “**main**”:
main()
