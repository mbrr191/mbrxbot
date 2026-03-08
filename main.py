import os
import logging
import yt_dlp
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
INTEL_SERVER = 'https://web-production-007d2.up.railway.app'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('📰 آخر الأخبار', callback_data='menu_news')],
        [InlineKeyboardButton('⬇️ تحميل فيديو', callback_data='menu_video')],
        [InlineKeyboardButton('🎭 بحث عن ممثل', callback_data='menu_actor')],
    ]
    await update.message.reply_text('MBRxBot — اختر:', reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'menu_news':
        msg = await query.message.reply_text('⏳ جاري جلب الأخبار...')
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f'{INTEL_SERVER}/api/news')
                news = r.json().get('news', [])[:8]
            text = '📡 آخر الأخبار:\n\n'
            for i, n in enumerate(news, 1):
                p = n.get('priority', '')
                e = '🔴' if p=='critical' else '🟠' if p=='high' else '🟡' if p=='medium' else '🟢'
                text += f'{e} {i}. {n.get("title","")[:80]}\n📌 {n.get("source","")} • {n.get("time","")}\n\n'
            await msg.edit_text(text)
        except:
            await msg.edit_text('⚠️ تعذر جلب الأخبار')
    elif query.data == 'menu_video':
        await query.message.reply_text('أرسل رابط الفيديو من Twitter/TikTok/Instagram')
        context.user_data['mode'] = 'video'
    elif query.data == 'menu_actor':
        await query.message.reply_text('أرسل صورة الممثل')
        context.user_data['mode'] = 'actor'

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ''
    if any(d in text for d in ('twitter.com','x.com','tiktok.com','instagram.com')):
        msg = await update.message.reply_text('⏳ جاري التحميل...')
        try:
            with yt_dlp.YoutubeDL({'format':'best[filesize<50M]/best','outtmpl':'/tmp/%(id)s.%(ext)s','quiet':True}) as ydl:
                info = ydl.extract_info(text.strip(), download=True)
                path = ydl.prepare_filename(info)
            await msg.delete()
            await update.message.reply_video(video=open(path,'rb'), caption='✅ تم!')
            os.remove(path)
        except:
            await msg.edit_text('❌ فشل التحميل')
    elif any(k in text for k in ('أخبار','اخبار','news')):
        await button_handler.__wrapped__(update, context) if hasattr(button_handler,'__wrapped__') else await update.message.reply_text('اضغط /start')
    else:
        await update.message.reply_text('استخدم /start')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pending_photo'] = update.message.photo[-1].file_id
    keyboard = [[InlineKeyboardButton('🔍 ابحث عن الممثل', callback_data='do_lens')]]
    await update.message.reply_text('هل تريد البحث؟', reply_markup=InlineKeyboardMarkup(keyboard))

async def lens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = context.user_data.get('pending_photo')
    if not file_id:
        await query.message.reply_text('أرسل الصورة مرة أخرى')
        return
    file = await context.bot.get_file(file_id)
    lens_url = f'https://lens.google.com/uploadbyurl?url={file.file_path}'
    await query.message.reply_text('اضغط للبحث:', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔍 Google Lens', url=lens_url)]]))

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(lens_callback, pattern='^do_lens$'))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
