from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import ADMIN_IDS
from database.queries import get_stats, get_setting, get_active_bosses, add_log
from database.db import get_db
from utils.helpers import is_admin, format_number

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("❌ Akses ditolak!")
        return
    await update.message.reply_text(
        "🔐 <b>Admin Panel</b>\n\nSelamat datang, Admin!",
        parse_mode="HTML",
        reply_markup=_admin_main_keyboard()
    )

async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.answer("❌ Akses ditolak!", show_alert=True)
        return
    
    stats = await get_stats()
    maintenance = await get_setting("maintenance_mode") == "1"
    double_exp = await get_setting("double_exp") == "1"
    double_coin = await get_setting("double_coin") == "1"
    active_bosses = await get_active_bosses()
    
    text = (
        f"📊 <b>Dashboard Admin</b>\n\n"
        f"👥 Total Player: <b>{format_number(stats['total_players'])}</b>\n"
        f"🟢 Online (1 jam): <b>{stats['online_players']}</b>\n"
        f"💰 Revenue Hari Ini: <b>Rp {format_number(stats['revenue_today'])}</b>\n"
        f"🎯 Total Hunt: <b>{format_number(stats['total_hunts'])}</b>\n"
        f"⏳ Topup Pending: <b>{stats['pending_topups']}</b>\n"
        f"👹 Boss Aktif: <b>{stats['active_bosses']}</b>\n\n"
        f"⚙️ <b>Status Bot:</b>\n"
        f"{'🔴 MAINTENANCE MODE' if maintenance else '🟢 Bot Aktif'}\n"
        f"{'⭐ Double EXP ON' if double_exp else '⭐ Double EXP OFF'}\n"
        f"{'💰 Double COIN ON' if double_coin else '💰 Double COIN OFF'}\n"
    )
    
    if stats['pending_topups'] > 0:
        text += f"\n⚠️ Ada {stats['pending_topups']} top-up menunggu verifikasi!"
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=_admin_main_keyboard())
    except Exception:
        pass

def _admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [
            InlineKeyboardButton("🗂️ Konten", callback_data="admin_content"),
            InlineKeyboardButton("💰 Ekonomi", callback_data="admin_economy"),
        ],
        [
            InlineKeyboardButton("👤 Player", callback_data="admin_players"),
            InlineKeyboardButton("🎉 Event/Boss", callback_data="admin_events"),
        ],
        [
            InlineKeyboardButton("💳 Transaksi", callback_data="admin_transactions"),
            InlineKeyboardButton("🤖 Pengaturan", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton("📋 Log", callback_data="admin_logs"),
            InlineKeyboardButton("🛡️ Admin/Role", callback_data="admin_roles"),
        ],
        [InlineKeyboardButton("🏠 Menu User", callback_data="main_menu")],
    ])
