from telegram import Update
from telegram.ext import ContextTypes
from database.queries import (
    get_player, create_player, get_setting, 
    add_coins, add_inventory, give_weapon, add_log
)
from utils.helpers import (
    main_menu_keyboard, send_with_photo, 
    update_survival_stats, format_number, rarity_badge
)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Check if player exists
    player = await get_player(user.id)
    
    if not player:
        # 2. Register New Player
        player = await create_player(user.id, user.username or f"user_{user.id}", user.first_name)
        
        # 3. Give Starter Bonus (Menggunakan fungsi dari queries.py)
        await add_coins(user.id, 500)
        await give_weapon(user.id, "slingshot", "Ketapel")
        await add_inventory(user.id, "food", "grilled_meat", "Daging Panggang", 5)
        await add_log(user.id, "register", "Player baru bergabung")
        
        welcome_msg = await get_setting("welcome_message") or "Selamat datang di HuntGame!"
        text = (
            f"🎉 <b>Selamat Datang, {user.first_name}!</b>\n\n"
            f"{welcome_msg}\n\n"
            f"🎁 <b>Bonus Pemula:</b>\n"
            f"• 💰 500 Koin\n"
            f"• 🪃 Ketapel (gratis)\n"
            f"• 🍖 5x Daging Panggang\n\n"
            f"Selamat berburu, Pemburu! 🦌"
        )
    else:
        # 4. Existing Player
        await update_survival_stats(user.id)
        # Ambil data terbaru setelah update stats
        player = await get_player(user.id)
        
        text = (
            f"🦌 <b>Selamat Datang Kembali, {user.first_name}!</b>\n\n"
            f"💰 Koin: <b>{format_number(player['coins'])}</b>\n"
            f"⭐ Level: <b>{player['level']}</b>\n"
            f"🎯 Total Hunt: <b>{format_number(player.get('total_hunts', 0))}</b>\n\n"
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
        player = await create_player(user.id, user.username or f"user_{user.id}", user.first_name)
    
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
        # Jika pesan tidak bisa diedit (misal ada foto), kirim pesan baru
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
