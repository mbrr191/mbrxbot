import os
import re
import logging
import yt_dlp
import httpx
from datetime import datetime, timezone
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

def is_recent(time_str: str, max_minutes: int = 15) -> bool:
    """Returns True if the article was published within max_minutes."""
    if not time_str:
        return True
    m = re.match(r'منذ\s+(\d+)\s+(دقيقة|دقائق|ساعة|ساعات)', time_str)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        minutes_ago = amount * 60 if ('ساعة' in unit or 'ساعات' in unit) else amount
        return minutes_ago <= max_minutes
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            dt = datetime.strptime(time_str, fmt).replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds() / 60
            return age <= max_minutes
        except ValueError:
            continue
    return True

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
        await _iran_menu(query)

    elif data == 'iran_general':
        await _iran_general(query)

    elif data == 'iran_uae':
        await _iran_uae(query)

    elif data == 'iran_usa_war':
        await _iran_usa_war(query)

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


# ─── Iran Analysis Suite ─────────────────────────────────────────────────────

IRAN_KW   = ('إيران','ايران','Iran','طهران','خامنئي','الحرس الثوري','بالستي','صاروخ','نووي','فيلق القدس','خامنئي')
UAE_KW    = ('الإمارات','إمارات','UAE','أبوظبي','دبي','أبو ظبي')
USA_KW    = ('أمريكا','الولايات المتحدة','ترامب','بايدن','البنتاغون','واشنطن','أمريكي','US ','USA')
EXPERT_SRC = ('reuters','bbc','new york times','foreign policy','al monitor',
               'brookings','cnn','the guardian','economist','رويترز','بي بي سي')

def _calc_risk(news_list: list) -> tuple:
    """Return (risk 0-100, avg_sentiment, critical_cnt, high_cnt)."""
    if not news_list:
        return 0, 50, 0, 0
    sentiments   = [n.get('sentiment', 50) for n in news_list]
    avg_sent     = sum(sentiments) / len(sentiments)
    critical_cnt = sum(1 for n in news_list if n.get('priority') == 'critical')
    high_cnt     = sum(1 for n in news_list if n.get('priority') == 'high')
    risk = 0
    if avg_sent < 25:   risk += 35
    elif avg_sent < 40: risk += 20
    elif avg_sent < 55: risk += 10
    risk += min(critical_cnt * 15, 30)
    risk += min(high_cnt * 8, 20)
    risk += min(len(news_list) * 3, 15)
    return min(risk, 100), avg_sent, critical_cnt, high_cnt

def _risk_label(risk: int) -> tuple:
    if risk >= 70: return 'مرتفع جداً ⛔', '🔴'
    if risk >= 50: return 'مرتفع 🚨', '🟠'
    if risk >= 30: return 'متوسط ⚠️', '🟡'
    return 'منخفض ✅', '🟢'

def _bar(risk: int) -> str:
    f = round(risk / 10)
    return '█' * f + '░' * (10 - f)

def _match(n: dict, keywords) -> bool:
    hay = (n.get('title','') + n.get('summary','')).lower()
    return any(k.lower() in hay for k in keywords)

# Sub-menu
async def _iran_menu(query):
    kb = [
        [InlineKeyboardButton('🎯 هل تضرب إيران؟',        callback_data='iran_general')],
        [InlineKeyboardButton('🇦🇪 هل تستهدف الإمارات؟',  callback_data='iran_uae')],
        [InlineKeyboardButton('⚔️ تحليل حرب إيران-أمريكا', callback_data='iran_usa_war')],
        [InlineKeyboardButton('🔙 القائمة الرئيسية',       callback_data='main_menu')],
    ]
    await query.message.reply_text(
        '🎯 *تحليل الملف الإيراني*\n\nاختر نوع التحليل:',
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(kb)
    )

# 1. General Iran strike probability
async def _iran_general(query):
    msg = await query.message.reply_text('⏳ جاري تحليل الوضع الإيراني...')
    try:
        news      = await fetch_news()
        iran_news = [n for n in news if _match(n, IRAN_KW)]
        lines     = ['🎯 *هل تضرب إيران؟ — تحليل شامل*\n']

        if not iran_news:
            lines += ['📊 لا توجد مؤشرات تصعيد إيرانية حالياً', '✅ *مستوى الخطر:* 🟢 منخفض']
        else:
            risk, avg_s, crit, high = _calc_risk(iran_news)
            lv, col = _risk_label(risk)
            lines += [
                f'*📊 مستوى الخطر:* {col} {lv}',
                f'*📉 مؤشر التصعيد:* `{_bar(risk)}` {risk}%',
                f'*📰 أخبار مرصودة:* {len(iran_news)} خبر',
                f'*⚡ حرجة / عالية:* {crit} / {high}',
                f'*😟 المزاج العام:* {sentiment_label(int(avg_s))}',
                '',
                '*📋 آخر التطورات:*',
            ]
            for n in iran_news[:4]:
                e = priority_icon(n.get('priority',''))
                lines += [f'{e} {n.get("title","")[:70]}',
                          f'   📌 {n.get("source","")} • {n.get("time","")}', '']

        kb = [
            [InlineKeyboardButton('🔄 تحديث', callback_data='iran_general'),
             InlineKeyboardButton('🔙 رجوع',  callback_data='iran_analysis')],
        ]
        await msg.edit_text('\n'.join(lines), parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f'iran_general: {e}')
        await msg.edit_text(f'⚠️ خطأ: {e}')

# 2. UAE threat from Iran
async def _iran_uae(query):
    msg = await query.message.reply_text('⏳ جاري تقييم التهديد للإمارات...')
    try:
        news     = await fetch_news()
        iran_all = [n for n in news if _match(n, IRAN_KW)]
        uae_iran = [n for n in iran_all if _match(n, UAE_KW)]
        uae_all  = [n for n in news    if _match(n, UAE_KW)]

        lines = ['🇦🇪 *هل تستهدف إيران الإمارات؟*\n']

        if not uae_iran:
            risk_g, avg_s, crit, high = _calc_risk(iran_all)
            # Indirect risk from general Iran tension
            indirect = round(risk_g * 0.4)
            lv, col  = _risk_label(indirect)
            lines += [
                '📊 *لا توجد أخبار تستهدف الإمارات مباشرة*',
                '',
                '*🔍 تقييم التهديد غير المباشر:*',
                f'  {col} *مستوى الخطر الجانبي:* {lv}',
                f'  📉 المؤشر: `{_bar(indirect)}` {indirect}%',
                '',
                '_يعتمد على مستوى التصعيد الإيراني العام_',
                '',
                f'*📰 أخبار إيران العامة:* {len(iran_all)} خبر',
                f'*📰 أخبار الإمارات:* {len(uae_all)} خبر',
            ]
        else:
            risk, avg_s, crit, high = _calc_risk(uae_iran)
            lv, col = _risk_label(risk)
            lines += [
                f'*🎯 مستوى التهديد المباشر:* {col} {lv}',
                f'*📉 مؤشر الخطر:* `{_bar(risk)}` {risk}%',
                f'*📰 أخبار إيران-الإمارات:* {len(uae_iran)} خبر',
                f'*⚡ حرجة / عالية:* {crit} / {high}',
                f'*😟 مزاج الأخبار:* {sentiment_label(int(avg_s))}',
                '',
                '*📋 الأخبار المرتبطة:*',
            ]
            for n in uae_iran[:4]:
                e = priority_icon(n.get('priority',''))
                lines += [f'{e} {n.get("title","")[:70]}',
                          f'   📌 {n.get("source","")} • {n.get("time","")}', '']

        kb = [
            [InlineKeyboardButton('🔄 تحديث', callback_data='iran_uae'),
             InlineKeyboardButton('🔙 رجوع',  callback_data='iran_analysis')],
        ]
        await msg.edit_text('\n'.join(lines), parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f'iran_uae: {e}')
        await msg.edit_text(f'⚠️ خطأ: {e}')

# 3. Iran-USA War full expert analysis
async def _iran_usa_war(query):
    msg = await query.message.reply_text('⏳ جاري تجميع تحليلات الخبراء...')
    try:
        news      = await fetch_news()
        iran_news = [n for n in news if _match(n, IRAN_KW)]
        usa_iran  = [n for n in iran_news if _match(n, USA_KW)]
        all_rel   = iran_news  # broader context

        # Expert sources
        expert_items = [
            n for n in all_rel
            if any(s in n.get('source','').lower() for s in EXPERT_SRC)
        ]

        risk_all, avg_s_all, crit_all, high_all = _calc_risk(all_rel)
        risk_us,  avg_s_us,  crit_us,  high_us  = _calc_risk(usa_iran)

        # Scenario probability model
        #  - Diplomatic: high sentiment + low risk
        #  - Limited strike: mid risk
        #  - Full war: high risk + many critical
        p_diplo  = max(5,  min(60, 100 - risk_us - (crit_us * 5)))
        p_strike = max(10, min(55, risk_us // 2 + high_us * 5))
        p_war    = max(3,  min(40, risk_us // 3 + crit_us * 8))
        total    = p_diplo + p_strike + p_war
        p_diplo  = round(p_diplo  / total * 100)
        p_strike = round(p_strike / total * 100)
        p_war    = 100 - p_diplo - p_strike

        # Trend
        if risk_us >= 60:   trend = '📈 تصاعدي — التوتر في ارتفاع'
        elif risk_us >= 35: trend = '📊 مستقر — وضع مراقبة'
        else:               trend = '📉 هادئ — دبلوماسية نشطة'

        lv_all, col_all = _risk_label(risk_all)
        lv_us,  col_us  = _risk_label(risk_us)

        lines = [
            '⚔️ *تحليل حرب إيران-أمريكا*',
            '_مدعوم بتحليل ذكاء اصطناعي + مصادر خبراء_\n',
            '━━━━━━━━━━━━━━━━━━',
            '*📡 الوضع الراهن:*',
            f'  {col_us}  مستوى التوتر الإيراني-الأمريكي: *{lv_us}*',
            f'  📉 المؤشر: `{_bar(risk_us)}` {risk_us}%',
            f'  📈 الاتجاه: {trend}',
            f'  📰 أخبار مرصودة: {len(usa_iran)} خبر إيران-أمريكا',
            f'  📚 مصادر خبراء: {len(expert_items)} مصدر موثوق',
            '',
            '━━━━━━━━━━━━━━━━━━',
            '*🔭 توقعات السيناريوهات:*',
            '',
            f'🕊 *التسوية الدبلوماسية*',
            f'   الاحتمالية: `{"█" * round(p_diplo/10)}{"░" * (10-round(p_diplo/10))}` {p_diplo}%',
            f'   _مفاوضات، وساطة، ضغط دبلوماسي_',
            '',
            f'💥 *ضربة محدودة / عملية نوعية*',
            f'   الاحتمالية: `{"█" * round(p_strike/10)}{"░" * (10-round(p_strike/10))}` {p_strike}%',
            f'   _استهداف مواقع بعيداً عن حرب شاملة_',
            '',
            f'🔥 *حرب مفتوحة*',
            f'   الاحتمالية: `{"█" * round(p_war/10)}{"░" * (10-round(p_war/10))}` {p_war}%',
            f'   _تصعيد كامل، مشاركة أطراف إقليمية_',
        ]

        # Expert opinions
        if expert_items:
            lines += ['', '━━━━━━━━━━━━━━━━━━',
                      '*🎓 ما يقوله الخبراء والمصادر الموثوقة:*', '']
            for n in expert_items[:3]:
                e = priority_icon(n.get('priority',''))
                lines.append(f'{e} *{n.get("source","")}*')
                analysis = n.get('analysis','')
                summary  = n.get('summary','')
                excerpt  = analysis if (analysis and 'Error' not in analysis) else summary
                if excerpt:
                    lines.append(f'   _{excerpt[:150]}..._')
                lines.append(f'   📌 {n.get("title","")[:65]}')
                lines.append('')

        # AI conclusion
        lines += [
            '━━━━━━━━━━━━━━━━━━',
            '*🧠 الاستنتاج التحليلي:*',
        ]
        if risk_us >= 65:
            lines.append(
                '_المؤشرات الحالية تشير إلى توتر حاد. '
                'الضغط العسكري والدبلوماسي في أعلى مستوياته، '
                'واحتمال عملية محدودة قائم. '
                'النافذة الدبلوماسية ضيقة لكنها لم تُغلق بعد._'
            )
        elif risk_us >= 40:
            lines.append(
                '_الوضع في مرحلة التصعيد التدريجي. '
                'الأطراف تتبادل الضغوط دون تجاوز خط الاشتباك المباشر. '
                'المفاوضات غير المعلنة محتملة في الخلفية._'
            )
        else:
            lines.append(
                '_المؤشرات الحالية تصب في مصلحة الاحتواء الدبلوماسي. '
                'لا توجد مؤشرات على ضربة وشيكة. '
                'متابعة مستمرة ضرورية لرصد أي تحول مفاجئ._'
            )

        kb = [
            [InlineKeyboardButton('🔄 تحديث', callback_data='iran_usa_war'),
             InlineKeyboardButton('🔙 رجوع',  callback_data='iran_analysis')],
        ]
        await msg.edit_text('\n'.join(lines), parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        logger.error(f'iran_usa_war: {e}')
        await msg.edit_text(f'⚠️ خطأ في التحليل: {e}')


# ─── News by Region ──────────────────────────────────────────────────────────

REGIONS = {
    'gulf':   ('🛢 الخليج العربي',
               ('سعودي','السعودية','الرياض','كويت','قطر','بحرين','عُمان','مسقط',
                'الدوحة','المنامة','gulf')),
    'uae':    ('🇦🇪 الإمارات العربية',
               ('الإمارات','إمارات','UAE','أبوظبي','دبي','أبو ظبي',
                'الشارقة','عجمان','الفجيرة','رأس الخيمة')),
    'global': ('🌐 أخبار عالمية',
               ('أمريكا','الولايات المتحدة','أوروبا','الصين','روسيا',
                'global','america','europe','china','russia','بريطانيا')),
    'houthi': ('🎖 اليمن والحوثيون',
               ('اليمن','الحوثي','حوثي','صنعاء','عدن','أنصار الله',
                'هجوم صاروخي','مسيّرة','بحر أحمر','باب المندب')),
}

async def _region_menu(query):
    kb = [
        [InlineKeyboardButton('🛢 الخليج',           callback_data='region_gulf'),
         InlineKeyboardButton('🇦🇪 الإمارات',         callback_data='region_uae')],
        [InlineKeyboardButton('🌐 عالمي',            callback_data='region_global'),
         InlineKeyboardButton('🎖 اليمن / الحوثيون', callback_data='region_houthi')],
        [InlineKeyboardButton('📋 الكل',             callback_data='region_all')],
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
            if n.get('priority') == 'critical'
            and n.get('id') not in sent_news_ids
            and is_recent(n.get('time', ''))
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
