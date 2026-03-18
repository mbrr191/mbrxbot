import os
import logging
import yt_dlp
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN environment variable is not set')

INTEL_SERVER = 'https://web-production-007d2.up.railway.app'

# Subscribers for breaking news alerts
alert_users: set = set()
sent_news_ids: set = set()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def priority_icon(p: str) -> str:
    return {'critical': '🔴', 'high': '🟠', 'medium': '🟡'}.get(p, '🟢')

def sentiment_label(score: int) -> str:
    if score >= 65: return '🟢 إيجابي'
    if score >= 40: return '🟡 محايد'
    return '🔴 سلبي'

async def fetch_news() -> list:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f'{INTEL_SERVER}/api/news')
        r.raise_for_status()
        return r.json().get('news', [])

def back_btn(dest='main_menu', label='🔙 القائمة الرئيسية'):
    return [[InlineKeyboardButton(label, callback_data=dest)]]


# ─── Main Menu ───────────────────────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📰 آخر الأخبار',      callback_data='news_latest'),
            InlineKeyboardButton('⚡ الأخبار العاجلة',  callback_data='news_critical'),
        ],
        [
            InlineKeyboardButton('📊 تحليل الأخبار',    callback_data='news_analysis'),
            InlineKeyboardButton('🎯 تحليل موقف إيران', callback_data='iran_analysis'),
        ],
        [
            InlineKeyboardButton('🌍 أخبار حسب المنطقة', callback_data='news_region'),
        ],
        [
            InlineKeyboardButton('⬇️ تحميل فيديو',    callback_data='menu_video'),
            InlineKeyboardButton('🎭 بحث عن ممثل',    callback_data='menu_actor'),
        ],
        [
            InlineKeyboardButton('🔔 تفعيل تنبيهات العاجل', callback_data='alerts_toggle'),
        ],
    ])

WELCOME = (
    "🛰 *MBRxBot — المركز الإعلامي الذكي*\n\n"
    "مرحباً! أنا بوتك الإعلامي المتكامل.\n"
    "📡 أخبار · 📊 تحليل · ⬇️ تحميل · 🎭 ممثلون\n\n"
    "اختر من القائمة:"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode='Markdown', reply_markup=main_keyboard())


# ─── Callback Router ─────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'main_menu':
        await query.message.edit_text(WELCOME, parse_mode='Markdown', reply_markup=main_keyboard())

    elif data == 'news_latest':
        await _news_latest(query)

    elif data == 'news_critical':
        await _news_critical(query)

    elif data == 'news_analysis':
        await _news_analysis(query)

    elif data == 'iran_analysis':
        await _iran_analysis(query)

    elif data == 'news_region':
        await _region_menu(query)

    elif data.startswith('region_'):
        await _region_news(query, data.replace('region_', ''))

    elif data == 'alerts_toggle':
        await _toggle_alerts(query)

    elif data == 'menu_video':
        context.user_data['mode'] = 'video'
        await query.message.reply_text(
            '📲 أرسل رابط الفيديو\n_يدعم: Twitter • TikTok • Instagram • YouTube_',
            parse_mode='Markdown'
        )

    elif data == 'menu_actor':
        context.user_data['mode'] = 'actor'
        await query.message.reply_text('📸 أرسل صورة الممثل وسأبحث عنه فوراً')


# ─── News: Latest ────────────────────────────────────────────────────────────

async def _news_latest(query):
    msg = await query.message.reply_text('⏳ جاري جلب الأخبار...')
    try:
        news = (await fetch_news())[:8]
        lines = ['📰 *آخر الأخبار*\n']
        for i, n in enumerate(news, 1):
            e = priority_icon(n.get('priority', ''))
            lines.append(f'{e} *{i}. {n.get("title","")[:75]}*')
            lines.append(f'   📌 {n.get("source","")} • {n.get("time","")}')
            lines.append('')
        await msg.edit_text(
            '\n'.join(lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(back_btn())
        )
    except Exception as e:
        logger.error(f'news_latest: {e}')
        await msg.edit_text(f'⚠️ تعذر جلب الأخبار: {e}')


# ─── News: Critical / Breaking ───────────────────────────────────────────────

async def _news_critical(query):
    msg = await query.message.reply_text('⏳ جاري جلب الأخبار العاجلة...')
    try:
        news = await fetch_news()
        critical = [n for n in news if n.get('priority') in ('critical', 'high')][:6]
        if not critical:
            await msg.edit_text(
                '✅ لا توجد أخبار عاجلة حالياً',
                reply_markup=InlineKeyboardMarkup(back_btn())
            )
            return
        lines = ['⚡ *الأخبار العاجلة*\n']
        for n in critical:
            e = priority_icon(n.get('priority', ''))
            lines.append(f'{e} *{n.get("title","")[:75]}*')
            lines.append(f'   📌 {n.get("source","")} • {n.get("time","")}')
            summary = n.get('summary', '')
            if summary:
                lines.append(f'   📝 _{summary[:120]}..._')
            lines.append('')
        await msg.edit_text(
            '\n'.join(lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(back_btn())
        )
    except Exception as e:
        logger.error(f'news_critical: {e}')
        await msg.edit_text(f'⚠️ تعذر جلب الأخبار: {e}')


# ─── News: Analysis ──────────────────────────────────────────────────────────

async def _news_analysis(query):
    msg = await query.message.reply_text('⏳ جاري تحليل الأخبار...')
    try:
        news = await fetch_news()
        top = [n for n in news if n.get('analysis') and 'Error' not in n.get('analysis', '')][:5]
        if not top:
            top = news[:5]
        lines = ['📊 *تحليل الأخبار*\n']
        for n in top:
            e = priority_icon(n.get('priority', ''))
            lines.append(f'{e} *{n.get("title","")[:70]}*')
            analysis = n.get('analysis', '')
            if analysis and 'Error' not in analysis:
                lines.append(f'🧠 _{analysis[:130]}..._')
            else:
                lines.append(f'📝 _{n.get("summary","")[:130]}_')
            lines.append(f'📈 {sentiment_label(n.get("sentiment", 50))}')
            lines.append(f'📌 {n.get("source","")} • {n.get("time","")}')
            lines.append('')
        await msg.edit_text(
            '\n'.join(lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(back_btn())
        )
    except Exception as e:
        logger.error(f'news_analysis: {e}')
        await msg.edit_text(f'⚠️ خطأ في التحليل: {e}')


# ─── Iran Strike Analysis ────────────────────────────────────────────────────

IRAN_KEYWORDS = ('إيران', 'ايران', 'Iran', 'طهران', 'خامنئي', 'الحرس الثوري',
                 'بالستي', 'صاروخ', 'نووي', 'فيلق القدس')

async def _iran_analysis(query):
    msg = await query.message.reply_text('⏳ جاري تحليل الوضع الإيراني...')
    try:
        news = await fetch_news()
        iran_news = [
            n for n in news
            if any(k in (n.get('title', '') + n.get('summary', '')) for k in IRAN_KEYWORDS)
        ]

        lines = ['🎯 *تحليل: هل تضرب إيران؟*\n']

        if not iran_news:
            lines.append('📊 لا توجد مؤشرات تصعيد إيرانية حالياً')
            lines.append('✅ *مستوى الخطر:* 🟢 منخفض')
        else:
            sentiments   = [n.get('sentiment', 50) for n in iran_news]
            avg_sent     = sum(sentiments) / len(sentiments)
            critical_cnt = sum(1 for n in iran_news if n.get('priority') == 'critical')
            high_cnt     = sum(1 for n in iran_news if n.get('priority') == 'high')

            # Risk score (0-100)
            risk = 0
            if avg_sent < 25:   risk += 35
            elif avg_sent < 40: risk += 20
            elif avg_sent < 55: risk += 10
            risk += min(critical_cnt * 15, 30)
            risk += min(high_cnt * 8, 20)
            risk += min(len(iran_news) * 3, 15)
            risk = min(risk, 100)

            if risk >= 70:   level, color = 'مرتفع جداً ⛔', '🔴'
            elif risk >= 50: level, color = 'مرتفع 🚨', '🟠'
            elif risk >= 30: level, color = 'متوسط ⚠️', '🟡'
            else:            level, color = 'منخفض ✅', '🟢'

            # Risk bar
            filled = round(risk / 10)
            bar = '█' * filled + '░' * (10 - filled)

            lines.append(f'*📊 مستوى الخطر:* {color} {level}')
            lines.append(f'*📉 مؤشر التصعيد:* `{bar}` {risk}%')
            lines.append(f'*📰 أخبار مرصودة:* {len(iran_news)} خبر')
            lines.append(f'*⚡ حرجة / عالية:* {critical_cnt} / {high_cnt}')
            lines.append(f'*😟 المزاج العام:* {sentiment_label(int(avg_sent))}')
            lines.append('')
            lines.append('*📋 آخر التطورات:*')
            for n in iran_news[:4]:
                e = priority_icon(n.get('priority', ''))
                lines.append(f'{e} {n.get("title","")[:70]}')
                lines.append(f'   • {n.get("source","")} • {n.get("time","")}')
                lines.append('')

        kb = [
            [InlineKeyboardButton('🔄 تحديث', callback_data='iran_analysis')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')],
        ]
        await msg.edit_text(
            '\n'.join(lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb)
        )
    except Exception as e:
        logger.error(f'iran_analysis: {e}')
        await msg.edit_text(f'⚠️ خطأ في التحليل: {e}')


# ─── News by Region ──────────────────────────────────────────────────────────

REGIONS = {
    'gulf':   ('🛢 الخليج العربي',   ('gulf', 'خليج', 'سعودي', 'إمارات', 'كويت', 'قطر', 'بحرين', 'عُمان')),
    'levant': ('🕌 المشرق العربي',   ('levant', 'سوريا', 'لبنان', 'الأردن', 'فلسطين', 'العراق')),
    'egypt':  ('🏛 مصر وشمال أفريقيا', ('egypt', 'مصر', 'ليبيا', 'تونس', 'المغرب')),
    'global': ('🌐 أخبار دولية',     ('global', 'america', 'europe', 'أمريكا', 'أوروبا')),
}

async def _region_menu(query):
    kb = [
        [InlineKeyboardButton('🛢 الخليج',      callback_data='region_gulf'),
         InlineKeyboardButton('🕌 المشرق',      callback_data='region_levant')],
        [InlineKeyboardButton('🏛 مصر / شمال أفريقيا', callback_data='region_egypt'),
         InlineKeyboardButton('🌐 دولي',        callback_data='region_global')],
        [InlineKeyboardButton('📋 الكل',        callback_data='region_all')],
        [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')],
    ]
    await query.message.reply_text('🌍 اختر المنطقة:', reply_markup=InlineKeyboardMarkup(kb))

async def _region_news(query, region: str):
    msg = await query.message.reply_text('⏳ جاري الجلب...')
    try:
        news = await fetch_news()
        label = '📋 الكل'
        if region == 'all':
            filtered = news[:8]
        else:
            info = REGIONS.get(region)
            label, keywords = info if info else (region, (region,))
            filtered = [
                n for n in news
                if any(k.lower() in (n.get('region','') + n.get('title','') + n.get('summary','')).lower()
                       for k in keywords)
            ][:8]
            if not filtered:
                filtered = news[:8]

        lines = [f'🌍 *أخبار {label}*\n']
        for i, n in enumerate(filtered, 1):
            e = priority_icon(n.get('priority', ''))
            lines.append(f'{e} *{i}. {n.get("title","")[:75]}*')
            lines.append(f'   📌 {n.get("source","")} • {n.get("time","")}')
            lines.append('')

        await msg.edit_text(
            '\n'.join(lines),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(back_btn('news_region', '🔙 تغيير المنطقة'))
        )
    except Exception as e:
        logger.error(f'region_news: {e}')
        await msg.edit_text(f'⚠️ خطأ: {e}')


# ─── Alerts ──────────────────────────────────────────────────────────────────

async def _toggle_alerts(query):
    uid = query.from_user.id
    if uid in alert_users:
        alert_users.discard(uid)
        await query.message.reply_text('🔕 تم إيقاف تنبيهات الأخبار العاجلة')
    else:
        alert_users.add(uid)
        await query.message.reply_text(
            '🔔 *تم تفعيل التنبيهات!*\n\n'
            'ستصلك الأخبار العاجلة فور نشرها تلقائياً.',
            parse_mode='Markdown'
        )

async def job_send_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Runs every 5 min — sends new critical news to subscribers."""
    if not alert_users:
        return
    try:
        news = await fetch_news()
        new_critical = [
            n for n in news
            if n.get('priority') == 'critical' and n.get('id') not in sent_news_ids
        ]
        for n in new_critical[:3]:
            sent_news_ids.add(n.get('id'))
            text = (
                f'⚡ *خبر عاجل*\n\n'
                f'🔴 *{n.get("title","")}*\n\n'
                f'📌 {n.get("source","")} • {n.get("time","")}'
            )
            summary = n.get('summary', '')
            if summary:
                text += f'\n\n📝 _{summary[:200]}_'
            for uid in list(alert_users):
                try:
                    await context.bot.send_message(uid, text, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f'alert to {uid}: {e}')
    except Exception as e:
        logger.error(f'job_send_alerts: {e}')


# ─── Message / Photo Handlers ────────────────────────────────────────────────

VIDEO_DOMAINS = ('twitter.com', 'x.com', 'tiktok.com', 'instagram.com', 'youtube.com', 'youtu.be')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ''
    if any(d in text for d in VIDEO_DOMAINS):
        msg = await update.message.reply_text('⏳ جاري التحميل...')
        try:
            with yt_dlp.YoutubeDL({
                'format': 'best[filesize<50M]/best',
                'outtmpl': '/tmp/%(id)s.%(ext)s',
                'quiet': True,
            }) as ydl:
                info = ydl.extract_info(text.strip(), download=True)
                path = ydl.prepare_filename(info)
            await msg.delete()
            await update.message.reply_video(video=open(path, 'rb'), caption='✅ تم التحميل!')
            os.remove(path)
        except Exception as e:
            logger.error(f'video download: {e}')
            await msg.edit_text(f'❌ فشل التحميل: {e}')
    else:
        await update.message.reply_text('استخدم /start للقائمة الرئيسية')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pending_photo'] = update.message.photo[-1].file_id
    kb = [[InlineKeyboardButton('🔍 ابحث عن هذا الشخص', callback_data='do_lens')]]
    await update.message.reply_text(
        '📸 تم استلام الصورة — هل تريد البحث؟',
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def lens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = context.user_data.get('pending_photo')
    if not file_id:
        await query.message.reply_text('أرسل الصورة مرة أخرى')
        return
    file = await context.bot.get_file(file_id)
    lens_url = f'https://lens.google.com/uploadbyurl?url={file.file_path}'
    await query.message.reply_text(
        '🔍 اضغط للبحث عبر Google Lens:',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔍 Google Lens', url=lens_url)]])
    )


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(lens_callback, pattern='^do_lens$'))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Breaking news alert job — every 5 minutes
    app.job_queue.run_repeating(job_send_alerts, interval=300, first=15)
    app.run_polling()

if __name__ == '__main__':
    main()
