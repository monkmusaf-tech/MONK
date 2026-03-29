from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_logs, add_log
from database.db import get_db
from utils.helpers import is_admin, format_number
from datetime import datetime, timedelta

SEVERITY_EMOJI = {
    "info": "ℹ️",
    "warning": "⚠️",
    "critical": "🔴",
}

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    async with await get_db() as db:
        cur = await db.execute("SELECT COUNT(*) FROM activity_logs WHERE severity='critical' AND created_at > datetime('now', '-24 hours')")
        critical_count = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM activity_logs WHERE severity='warning' AND created_at > datetime('now', '-24 hours')")
        warning_count = (await cur.fetchone())[0]

    text = (
        f"📋 <b>Log & Monitoring</b>\n\n"
        f"🔴 Critical (24h): {critical_count}\n"
        f"⚠️ Warning (24h): {warning_count}\n\n"
        f"Pilih kategori log:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Log Realtime (50)", callback_data="log_realtime")],
        [InlineKeyboardButton("🔴 Log Critical", callback_data="log_critical")],
        [InlineKeyboardButton("⚠️ Log Warning", callback_data="log_warning")],
        [InlineKeyboardButton("🕵️ Deteksi Cheat", callback_data="log_cheat")],
        [InlineKeyboardButton("🧹 Bersihkan Log Lama", callback_data="log_clean")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def realtime_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    data = query.data
    severity = None
    if data == "log_critical":
        severity = "critical"
        title = "🔴 Log Critical"
    elif data == "log_warning":
        severity = "warning"
        title = "⚠️ Log Warning"
    else:
        title = "📋 Log Realtime"

    logs = await get_logs(limit=30, severity=severity)

    text = f"{title}\n\n"

    for log in logs:
        emoji = SEVERITY_EMOJI.get(log['severity'], 'ℹ️')
        time_str = log['created_at'][11:16] if log['created_at'] else "--:--"
        text += f"{emoji} [{time_str}] User:{log['user_id']} | {log['action']}\n"
        if log['details']:
            text += f"   └ {log['details'][:50]}\n"

    if not logs:
        text += "Tidak ada log."

    if len(text) > 4000:
        text = text[:4000] + "\n...(dipotong)"

    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data=data)],
            [InlineKeyboardButton("◀️ Log Menu", callback_data="admin_logs")],
        ])
    )

async def cheat_detection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    # Detect anomalies: players with too many hunts in short time
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))

        # Players with unusually high earnings in 24h
        cur = await db.execute("""
            SELECT user_id, SUM(amount) as total
            FROM transactions
            WHERE type='sell' AND created_at > datetime('now', '-24 hours')
            GROUP BY user_id
            HAVING total > 1000000
            ORDER BY total DESC
            LIMIT 10
        """)
        high_earners = await cur.fetchall()

        # Check activity logs for rapid hunting
        cur = await db.execute("""
            SELECT user_id, COUNT(*) as count
            FROM activity_logs
            WHERE action='hunt_success' AND created_at > datetime('now', '-1 hours')
            GROUP BY user_id
            HAVING count > 20
            ORDER BY count DESC
        """)
        rapid_hunters = await cur.fetchall()

    text = "🕵️ <b>Deteksi Cheat & Anomali</b>\n\n"

    text += "💰 <b>Penghasilan Tinggi 24h (>1M):</b>\n"
    if high_earners:
        for e in high_earners:
            text += f"• User {e['user_id']}: {format_number(e['total'])} koin\n"
    else:
        text += "Tidak ada anomali\n"

    text += "\n🎯 <b>Hunt Cepat (>20 dalam 1 jam):</b>\n"
    if rapid_hunters:
        for h in rapid_hunters:
            text += f"• User {h['user_id']}: {h['count']} hunt\n"
    else:
        text += "Tidak ada anomali\n"

    buttons = []
    for e in high_earners[:3]:
        buttons.append([InlineKeyboardButton(
            f"🔍 Investigasi User {e['user_id']}",
            callback_data=f"investigate_{e['user_id']}"
        )])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="log_cheat")])
    buttons.append([InlineKeyboardButton("◀️ Log", callback_data="admin_logs")])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
