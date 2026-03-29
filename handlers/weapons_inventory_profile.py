from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_player, get_weapons, get_weapon, get_player_weapons,
    player_has_weapon, give_weapon, add_coins, get_inventory,
    get_leaderboard, get_museum_trophies
)
from database.db import get_db
from utils.helpers import format_number, rarity_badge

# ===================== WEAPONS =====================

async def menu_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    owned = await get_player_weapons(user.id)
    owned_ids = {w['weapon_id'] for w in owned}
    
    weapons = await get_weapons()
    
    text = (
        f"🔫 <b>Arsenal Senjata</b>\n\n"
        f"💰 Koinmu: <b>{format_number(player['coins'])}</b>\n"
        f"🔫 Senjata dimiliki: <b>{len(owned)}</b>\n\n"
        f"Grade senjata menentukan hewan yang bisa diburu.\nPilih senjata:"
    )
    
    buttons = []
    for w in weapons:
        status = "✅" if w['id'] in owned_ids else f"💰 {format_number(w['price'])}"
        equipped = " 🎯" if w['id'] == player.get('weapon_equipped') else ""
        buttons.append([InlineKeyboardButton(
            f"{w['emoji']} {w['name']} G{w['grade']}{equipped} [{status}]",
            callback_data=f"buy_weapon_{w['id']}" if w['id'] not in owned_ids else f"equip_weapon_{w['id']}"
        )])
    
    buttons.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass

async def buy_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    weapon_id = query.data.replace("buy_weapon_", "")
    user = update.effective_user
    player = await get_player(user.id)
    weapon = await get_weapon(weapon_id)
    
    if not weapon:
        await query.answer("❌ Senjata tidak ditemukan!", show_alert=True)
        return
    
    if await player_has_weapon(user.id, weapon_id):
        await query.answer("✅ Sudah punya senjata ini!", show_alert=True)
        return
    
    if player['coins'] < weapon['price']:
        await query.answer(f"❌ Koin kurang! Butuh {format_number(weapon['price'])} koin.", show_alert=True)
        return
    
    # Buy weapon
    await add_coins(user.id, -weapon['price'])
    await give_weapon(user.id, weapon_id, weapon['name'])
    
    await query.edit_message_text(
        f"✅ <b>Senjata Dibeli!</b>\n\n"
        f"{weapon['emoji']} <b>{weapon['name']}</b>\n"
        f"Grade: {weapon['grade']} | Damage: {weapon['damage']} | Akurasi: {int(weapon['accuracy']*100)}%\n\n"
        f"💰 -{format_number(weapon['price'])} koin\n\n"
        f"Tap 'Equip' untuk memakai senjata ini!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎯 Equip {weapon['name']}", callback_data=f"equip_weapon_{weapon_id}")],
            [InlineKeyboardButton("◀️ Senjata", callback_data="menu_weapons")],
        ])
    )

async def equip_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    weapon_id = query.data.replace("equip_weapon_", "")
    user = update.effective_user
    
    if not await player_has_weapon(user.id, weapon_id):
        await query.answer("❌ Kamu tidak punya senjata ini!", show_alert=True)
        return
    
    weapon = await get_weapon(weapon_id)
    
    async with await get_db() as db:
        await db.execute("UPDATE players SET weapon_equipped=? WHERE user_id=?", (weapon_id, user.id))
        await db.commit()
    
    await query.answer(f"✅ {weapon['name']} equipped!", show_alert=True)
    await menu_weapons(update, context)

# ===================== INVENTORY =====================

async def menu_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    text = "🎒 <b>Inventori</b>\n\nPilih kategori:"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🍖 Hasil Buruan", callback_data="inv_animals")],
        [InlineKeyboardButton("🎁 Item & Perlengkapan", callback_data="inv_items")],
        [InlineKeyboardButton("🔫 Senjata", callback_data="menu_weapons")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def view_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    items = await get_inventory(user.id, 'item')
    
    if not items:
        await query.edit_message_text(
            "🎒 <b>Item Kosong!</b>\n\nKamu belum punya item.\nBeli di market!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏪 Market", callback_data="menu_market")],
                [InlineKeyboardButton("◀️ Inventori", callback_data="menu_inventory")],
            ])
        )
        return
    
    text = "🎁 <b>Item & Perlengkapan</b>\n\n"
    buttons = []
    
    for item in items:
        text += f"• {item['item_name']} x{item['quantity']}\n"
        buttons.append([InlineKeyboardButton(
            f"⚡ Pakai {item['item_name']}",
            callback_data=f"use_item_{item['item_id']}"
        )])
    
    buttons.append([InlineKeyboardButton("◀️ Inventori", callback_data="menu_inventory")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def view_animals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    meats = await get_inventory(user.id, 'animal_meat')
    skins = await get_inventory(user.id, 'animal_skin')
    special = await get_inventory(user.id, 'special_item')
    
    all_items = meats + skins + special
    
    if not all_items:
        await query.edit_message_text(
            "🦌 <b>Hasil Buruan Kosong!</b>\n\nBelum ada hasil buruan.\nPergi berburu dulu!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🦌 Hunt", callback_data="menu_hunt")],
                [InlineKeyboardButton("◀️ Inventori", callback_data="menu_inventory")],
            ])
        )
        return
    
    text = "🍖 <b>Hasil Buruan</b>\n\n"
    total_items = sum(i['quantity'] for i in all_items)
    text += f"Total: {total_items} item\n\n"
    
    for item in all_items[:20]:
        emoji = "🍖" if item['item_type'] == 'animal_meat' else "🧥" if item['item_type'] == 'animal_skin' else "🎁"
        text += f"{emoji} {item['item_name']} x{item['quantity']}\n"
    
    if len(all_items) > 20:
        text += f"\n...dan {len(all_items) - 20} item lainnya"
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Jual", callback_data="market_sell")],
            [InlineKeyboardButton("◀️ Inventori", callback_data="menu_inventory")],
        ])
    )

async def use_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    item_id = query.data.replace("use_item_", "")
    user = update.effective_user
    
    # Get item from DB
    from database.queries import get_items, remove_inventory
    items = await get_items()
    item = next((i for i in items if i['id'] == item_id), None)
    
    if not item:
        await query.answer("❌ Item tidak ditemukan!", show_alert=True)
        return
    
    success = await remove_inventory(user.id, 'item', item_id)
    if not success:
        await query.answer("❌ Item habis!", show_alert=True)
        return
    
    # Apply effect
    effect_text = f"✅ {item['emoji']} {item['name']} digunakan!"
    
    if item['effect'] == 'stamina':
        player = await get_player(user.id)
        new_stamina = min(100, player['stamina'] + item['effect_value'])
        async with await get_db() as db:
            await db.execute("UPDATE players SET stamina=? WHERE user_id=?", (new_stamina, user.id))
            await db.commit()
        effect_text += f"\n⚡ Stamina +{int(item['effect_value'])}"
    
    await query.answer(effect_text, show_alert=True)

# ===================== PROFILE =====================

async def menu_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    from utils.helpers import update_survival_stats
    await update_survival_stats(user.id)
    player = await get_player(user.id)
    
    if not player:
        await query.answer("❌ Error!", show_alert=True)
        return
    
    owned_weapons = await get_player_weapons(user.id)
    trophies = await get_museum_trophies(user.id)
    equipped_weapon = await get_weapon(player.get('weapon_equipped', 'slingshot'))
    
    # EXP progress
    exp_needed = player['level'] * 100
    exp_progress = int((player['exp'] / exp_needed) * 10)
    exp_bar = "█" * exp_progress + "░" * (10 - exp_progress)
    
    text = (
        f"👤 <b>Profil {user.first_name}</b>\n"
        f"@{user.username or 'no_username'}\n\n"
        f"⭐ Level: <b>{player['level']}</b>\n"
        f"📊 EXP: [{exp_bar}] {player['exp']}/{exp_needed}\n\n"
        f"💰 Koin: <b>{format_number(player['coins'])}</b>\n"
        f"🎯 Total Hunt: <b>{format_number(player['total_hunts'])}</b>\n"
        f"☠️ Total Kill: <b>{format_number(player['total_kills'])}</b>\n"
        f"💵 Total Earn: <b>{format_number(player['total_earnings'])}</b>\n\n"
        f"🔫 Senjata: <b>{equipped_weapon['name'] if equipped_weapon else 'Ketapel'}</b>\n"
        f"🏠 Rumah: <b>Level {player['home_level']}</b>\n"
        f"🏆 Trofi: <b>{len(trophies)}</b>\n"
        f"🔫 Arsenal: <b>{len(owned_weapons)} senjata</b>\n\n"
        f"📅 Bergabung: {player['joined_at'][:10] if player['joined_at'] else '-'}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

# ===================== LEADERBOARD =====================

async def menu_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🏆 <b>Leaderboard</b>\n\nPilih kategori:"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Terkaya", callback_data="lb_coins")],
        [InlineKeyboardButton("⭐ Level Tertinggi", callback_data="lb_level")],
        [InlineKeyboardButton("☠️ Kill Terbanyak", callback_data="lb_kills")],
        [InlineKeyboardButton("💵 Penghasilan Terbesar", callback_data="lb_earnings")],
        [InlineKeyboardButton("🏛️ Museum Terlengkap", callback_data="museum_lb")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass
