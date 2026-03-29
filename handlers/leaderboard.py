from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_leaderboard
from utils.helpers import format_number

async def menu_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🏆 <b>Leaderboard</b>\n\nPilih kategori:"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Terkaya", callback_data="lb_coins")],
        [InlineKeyboardButton("⭐ Level Tertinggi", callback_data="lb_level")],
        [InlineKeyboardButton("☠️ Kill Terbanyak", callback_data="lb_kills")],
        [InlineKeyboardButton("💵 Penghasilan Terbesar", callback_data="lb_earnings")],
        [InlineKeyboardButton("🏛️ Museum", callback_data="museum_lb")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, lb_type: str):
    query = update.callback_query
    data = await get_leaderboard(lb_type)
    
    titles = {
        "coins": "💰 Leaderboard Terkaya",
        "level": "⭐ Leaderboard Level",
        "kills": "☠️ Leaderboard Kill",
        "earnings": "💵 Leaderboard Penghasilan",
    }
    
    text = f"🏆 <b>{titles.get(lb_type, 'Leaderboard')}</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, entry in enumerate(data):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = entry.get('username') or entry.get('full_name') or f"Player#{entry['user_id']}"
        
        if lb_type == "coins":
            value = f"{format_number(entry['coins'])} 💰"
        elif lb_type == "level":
            value = f"Level {entry['level']}"
        elif lb_type == "kills":
            value = f"{format_number(entry['total_kills'])} kill"
        elif lb_type == "earnings":
            value = f"{format_number(entry['total_earnings'])} 💰"
        else:
            value = ""
        
        text += f"{medal} {name} — {value}\n"
    
    try:
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Kembali", callback_data="menu_leaderboard")]
            ])
        )
    except Exception:
        pass
