from telegram import Update
from telegram.ext import ContextTypes
from database.queries import get_player, create_player, get_setting
from utils.helpers import main_menu_keyboard, send_with_photo, update_survival_stats, format_number, rarity_badge

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Create or get player
    player = await get_player(user.id)
    if not player:
        player = await create_player(user.id, user.username or "", user.first_name)
        is_new = True
    else:
        await update_survival_stats(user.id)
        is_new = False
    
    welcome = await get_setting("welcome_message") or "Selamat datang di HuntGame!"
    
    if is_new:
        text = (
            f"🎉 <b>Selamat Datang, {user.first_name}!</b>\n\n"
            f"{welcome}\n\n"
            f"🎁 <b>Bonus Pemula:</b>\n"
            f"• 💰 500 Koin\n"
            f"• 🪃 Ketapel (gratis)\n"
            f"• 🍖 5x Daging Kelinci\n\n"
            f"Selamat berburu, Pemburu! 🦌"
        )
        # Give starter bonus
        from database.queries import add_coins, add_inventory
        from database.db import get_db
        await add_coins(user.id, 500)
        async with await get_db() as db:
            await db.execute(
                "INSERT OR IGNORE INTO player_weapons (user_id, weapon_id, weapon_name) VALUES (?,?,?)",
                (user.id, "slingshot", "Ketapel")
            )
            await db.commit()
        await add_inventory(user.id, "food", "grilled_meat", "Daging Panggang", 5)
    else:
        player = await get_player(user.id)
        text = (
            f"🦌 <b>Selamat Datang Kembali, {user.first_name}!</b>\n\n"
            f"💰 Koin: <b>{format_number(player['coins'])}</b>\n"
            f"⭐ Level: <b>{player['level']}</b>\n"
            f"🎯 Total Hunt: <b>{format_number(player['total_hunts'])}</b>\n\n"
            f"Pilih menu di bawah:"
        )
    
    await send_with_photo(
        context, update.effective_chat.id,
        "lobby_photo", text,
        reply_markup=main_menu_keyboard()
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    if not player:
        player = await create_player(user.id, user.username or "", user.first_name)
    
    await update_survival_stats(user.id)
    player = await get_player(user.id)
    
    text = (
        f"🦌 <b>HuntGame</b>\n\n"
        f"👤 <b>{user.first_name}</b>\n"
        f"💰 Koin: <b>{format_number(player['coins'])}</b>\n"
        f"⭐ Level: <b>{player['level']}</b>\n\n"
        f"Pilih menu:"
    )
    
    try:
        await query.edit_message_text(text=text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    except Exception:
        await query.message.reply_text(text=text, reply_markup=main_menu_keyboard(), parse_mode="HTML")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>Panduan HuntGame</b>\n\n"
        "🦌 <b>Hunt</b> - Berburu hewan di berbagai map\n"
        "🏪 <b>Market</b> - Jual hasil buruan & P2P Trading\n"
        "🏠 <b>Rumah</b> - Kelola kebutuhan hidup & masak\n"
        "🏛️ <b>Museum</b> - Koleksi trofi & achievement\n"
        "🔫 <b>Senjata</b> - Beli & equip senjata\n"
        "🎒 <b>Inventori</b> - Lihat semua item\n\n"
        "⚡ <b>Survival Stats:</b>\n"
        "• Hunger & Thirst berkurang setiap jam\n"
        "• Stamina diperlukan untuk berburu\n"
        "• Istirahat untuk pulihkan stamina\n\n"
        "💰 <b>Ekonomi:</b>\n"
        "• Jual daging & kulit hewan ke market\n"
        "• Trade dengan player lain via P2P\n"
        "• Top-up koin untuk item premium\n\n"
        "🎯 <b>Tips:</b>\n"
        "• Upgrade senjata untuk hewan langka\n"
        "• Kumpulkan trofi di museum\n"
        "• Lengkapi achievement untuk bonus\n"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=None)
