import os
import logging
import yt_dlp
import httpx
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
INTEL_SERVER = “https://web-production-007d2.up.railway.app”

# ══ START ══

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
keyboard = [
[InlineKeyboardButton(“📰 آخر الأخبار”, callback_data=“menu_news”)],
[InlineKeyboardButton(“⬇️ تحميل فيديو”, callback_data=“menu_video”)],
[InlineKeyboardButton(“🎭 بحث عن ممثل بالصورة”, callback_data=“menu_actor”)],
[InlineKeyboardButton(“❓ مساعدة”, callback_data=“menu_help”)],
]
reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text(
“*MBRxBot* — اختر ما تريد:”,
parse_mode=“Markdown”,
reply_markup=reply_markup,
)

# ══ NEWS ══

async def fetch_news():
try:
async with httpx.AsyncClient(timeout=15) as client:
r = await client.get(f”{INTEL_SERVER}/api/news”)
data = r.json()
return data.get(“news”, [])
except Exception as e:
logger.error(f”News fetch error: {e}”)
return []

def priority_emoji(p):
return {“critical”: “🔴”, “high”: “🟠”, “medium”: “🟡”, “low”: “🟢”}.get(p, “⚪”)

async def show_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = await update.message.reply_text(“⏳ جاري جلب الأخبار…”)
news = await fetch_news()
if not news:
await msg.edit_text(“⚠️ تعذّر جلب الأخبار، حاول لاحقاً.”)
return
top = news[:8]
text = “📡 *آخر الأخبار الاستخباراتية:*\n\n”
for i, n in enumerate(top, 1):
emoji = priority_emoji(n.get(“priority”, “low”))
title = n.get(“title”, “”)[:80]
source = n.get(“source”, “”)
time = n.get(“time”, “”)
text += f”{emoji} *{i}.* {title}\n”
text += f”   📌 {source} • {time}\n\n”
await msg.edit_text(text, parse_mode=“Markdown”)

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
await show_news(update, context)

# ══ BUTTON HANDLER ══

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()

```
if query.data == "menu_news":
    msg = await query.message.reply_text("⏳ جاري جلب الأخبار...")
    news = await fetch_news()
    if not news:
        await msg.edit_text("⚠️ تعذّر جلب الأخبار، حاول لاحقاً.")
        return
    top = news[:8]
    text = "📡 *آخر الأخبار الاستخباراتية:*\n\n"
    for i, n in enumerate(top, 1):
        emoji = priority_emoji(n.get("priority", "low"))
        title = n.get("title", "")[:80]
        source = n.get("source", "")
        time = n.get("time", "")
        text += f"{emoji} *{i}.* {title}\n"
        text += f"   📌 {source} • {time}\n\n"
    await msg.edit_text(text, parse_mode="Markdown")

elif query.data == "menu_video":
    await query.message.reply_text(
        "*تحميل فيديو* 🎬\n\nأرسل رابط الفيديو من:\n• Twitter / X\n• TikTok\n• Instagram",
        parse_mode="Markdown",
    )
    context.user_data["mode"] = "video"

elif query.data == "menu_actor":
    await query.message.reply_text(
        "*بحث عن ممثل* 🎭\n\nأرسل صورة الممثل/الممثلة وسأفتح لك بحث Google Lens.",
        parse_mode="Markdown",
    )
    context.user_data["mode"] = "actor"

elif query.data == "menu_help":
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]
    await query.message.reply_text(
        "*كيفية الاستخدام:*\n\n"
        "📰 *أخبار:* اضغط آخر الأخبار\n"
        "🎬 *فيديو:* اضغط تحميل فيديو ثم أرسل الرابط\n"
        "🎭 *ممثل:* اضغط بحث عن ممثل ثم أرسل الصورة",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

elif query.data == "menu_back":
    keyboard = [
        [InlineKeyboardButton("📰 آخر الأخبار", callback_data="menu_news")],
        [InlineKeyboardButton("⬇️ تحميل فيديو", callback_data="menu_video")],
        [InlineKeyboardButton("🎭 بحث عن ممثل بالصورة", callback_data="menu_actor")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="menu_help")],
    ]
    await query.message.reply_text(
        "اختر ما تريد:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
```

# ══ MESSAGES ══

SUPPORTED_DOMAINS = (“twitter.com”, “x.com”, “tiktok.com”, “instagram.com”)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text or “”
lower = text.lower()

```
if any(domain in text for domain in SUPPORTED_DOMAINS):
    await download_video(update, context, text.strip())
elif any(kw in lower for kw in ["أخبار", "اخبار", "news", "خبر"]):
    await show_news(update, context)
else:
    await update.message.reply_text("استخدم /start لاختيار الميزة التي تريدها.")
```

# ══ VIDEO ══

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

# ══ PHOTO ══

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[“pending_photo”] = update.message.photo[-1].file_id
keyboard = [[InlineKeyboardButton(“🔍 ابحث عن هذا الممثل”, callback_data=“do_lens”)]]
await update.message.reply_text(
“استلمت الصورة! هل تريد البحث عن الممثل؟”,
reply_markup=InlineKeyboardMarkup(keyboard),
)

async def send_lens_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
photo = update.message.photo[-1] if update.message.photo else None
if not photo:
await update.message.reply_text(“لم أتمكن من قراءة الصورة.”)
return
file = await context.bot.get_file(photo.file_id)
lens_url = f”https://lens.google.com/uploadbyurl?url={file.file_path}”
keyboard = [[InlineKeyboardButton(“🔍 افتح Google Lens”, url=lens_url)]]
await update.message.reply_text(
“اضغط الزر أدناه للبحث عن الممثل في Google Lens:”,
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data[“mode”] = “”

async def lens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
file_id = context.user_data.get(“pending_photo”)
if not file_id:
await query.message.reply_text(“لم أجد الصورة، أرسلها مرة أخرى.”)
return
file = await context.bot.get_file(file_id)
lens_url = f”https://lens.google.com/uploadbyurl?url={file.file_path}”
keyboard = [[InlineKeyboardButton(“🔍 افتح Google Lens”, url=lens_url)]]
await query.message.reply_text(
“اضغط الزر أدناه للبحث عن الممثل في Google Lens:”,
reply_markup=InlineKeyboardMarkup(keyboard),
)
context.user_data[“pending_photo”] = None

# ══ MAIN ══

def main():
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CommandHandler(“news”, news_command))
app.add_handler(CallbackQueryHandler(lens_callback, pattern=”^do_lens$”))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
logger.info(“Bot is running…”)
app.run_polling()

if **name** == “**main**”:
main()
