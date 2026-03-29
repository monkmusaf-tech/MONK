from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_player, get_museum_trophies, add_trophy, get_museum_leaderboard,
    get_achievements, get_inventory, get_animal
)
from database.db import get_db
from utils.helpers import format_number, rarity_badge, RARITY_COLORS

async def menu_museum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    
    trophies = await get_museum_trophies(user.id)
    
    text = (
        f"🏛️ <b>Museum Pemburu</b>\n\n"
        f"🏆 Trofi Koleksimu: <b>{len(trophies)}</b>\n"
        f"⭐ Level: <b>{player['level']}</b>\n\n"
        f"Pilih menu:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🏆 Trofi ({len(trophies)})", callback_data="museum_trophies")],
        [InlineKeyboardButton("➕ Tambah Trofi", callback_data="add_trophy_menu")],
        [InlineKeyboardButton("🥇 Leaderboard", callback_data="museum_lb")],
        [InlineKeyboardButton("🎯 Achievement", callback_data="achievements")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def view_trophies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    trophies = await get_museum_trophies(user.id)
    
    if not trophies:
        await query.edit_message_text(
            "🏛️ <b>Museum Kosong!</b>\n\nKamu belum punya trofi.\nBerburu hewan langka dan tambahkan ke museum!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🦌 Berburu", callback_data="menu_hunt")],
                [InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")],
            ])
        )
        return
    
    text = f"🏆 <b>Koleksi Trofi ({len(trophies)})</b>\n\n"
    
    # Group by rarity
    rarity_order = ["boss", "mythic", "legendary", "epic", "rare", "uncommon", "common"]
    grouped = {}
    for trophy in trophies:
        r = trophy['rarity']
        if r not in grouped:
            grouped[r] = []
        grouped[r].append(trophy)
    
    for rarity in rarity_order:
        if rarity in grouped:
            text += f"{RARITY_COLORS[rarity]} <b>{rarity.title()}</b>\n"
            for t in grouped[rarity]:
                text += f"• {t['animal_name']}\n"
            text += "\n"
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Tambah Trofi", callback_data="add_trophy_menu")],
            [InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")],
        ])
    )

async def add_trophy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    if data == "add_trophy_menu":
        # Show animals in inventory that can be added as trophy
        inv = await get_inventory(user.id)
        existing_trophies = await get_museum_trophies(user.id)
        existing_ids = {t['animal_id'] for t in existing_trophies}
        
        # Find unique animals
        animal_items = set()
        for item in inv:
            if item['item_type'] in ['animal_meat', 'animal_skin']:
                if item['item_type'] == 'animal_meat':
                    animal_id = item['item_id'].replace("meat_", "")
                else:
                    animal_id = item['item_id'].replace("skin_", "")
                animal_items.add(animal_id)
        
        if not animal_items:
            await query.edit_message_text(
                "❌ <b>Tidak Ada Hewan!</b>\n\nKamu belum punya hasil buruan untuk dijadikan trofi.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🦌 Berburu", callback_data="menu_hunt")],
                    [InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")],
                ])
            )
            return
        
        text = "🏆 <b>Tambah Trofi</b>\n\nPilih hewan untuk dijadikan trofi:\n(Trofi mengurangi 1 daging dari inventori)"
        buttons = []
        
        for animal_id in animal_items:
            animal = await get_animal(animal_id)
            if animal:
                already = "✅" if animal_id in existing_ids else "➕"
                buttons.append([InlineKeyboardButton(
                    f"{already} {animal['emoji']} {animal['name']} ({rarity_badge(animal['rarity'])})",
                    callback_data=f"add_trophy_{animal_id}" if animal_id not in existing_ids else "noop"
                )])
        
        buttons.append([InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Process adding trophy
    animal_id = data.replace("add_trophy_", "")
    animal = await get_animal(animal_id)
    
    if not animal:
        await query.answer("❌ Hewan tidak ditemukan!", show_alert=True)
        return
    
    # Get trophy reward from museum slots
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute(
            "SELECT trophy_reward FROM museum_slots WHERE required_rarity=? LIMIT 1",
            (animal['rarity'],)
        )
        slot = await cursor.fetchone()
    
    trophy_reward = slot['trophy_reward'] if slot else 100
    
    # Remove one meat from inventory
    success = await add_trophy(user.id, animal_id, animal['name'], animal['rarity'], trophy_reward)
    
    if not success:
        await query.answer("✅ Trofi sudah ada di museum!", show_alert=True)
        return
    
    # Remove meat from inventory (optional, trophy costs nothing actually)
    
    await query.edit_message_text(
        f"🎊 <b>Trofi Ditambahkan!</b>\n\n"
        f"{animal['emoji']} <b>{animal['name']}</b>\n"
        f"{rarity_badge(animal['rarity'])}\n\n"
        f"🎁 Bonus: +{format_number(trophy_reward)} koin!\n\n"
        f"Museum kamu semakin kaya koleksi!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏛️ Lihat Museum", callback_data="museum_trophies")],
            [InlineKeyboardButton("🦌 Berburu Lagi", callback_data="menu_hunt")],
        ])
    )

async def museum_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lb = await get_museum_leaderboard()
    
    text = "🏛️ <b>Leaderboard Museum</b>\n🏆 Kolektor Terhebat!\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    for i, entry in enumerate(lb[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = entry['username'] or entry['full_name'] or f"Player#{entry['user_id']}"
        text += f"{medal} {name} - {entry['trophy_count']} trofi\n"
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")]
        ])
    )

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    trophies = await get_museum_trophies(user.id)
    
    all_achievements = await get_achievements()
    
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute(
            "SELECT achievement_id FROM player_achievements WHERE user_id=?",
            (user.id,)
        )
        unlocked_rows = await cursor.fetchall()
    
    unlocked_ids = {r['achievement_id'] for r in unlocked_rows}
    
    text = f"🎯 <b>Achievement</b>\n\n✅ {len(unlocked_ids)}/{len(all_achievements)} Selesai\n\n"
    
    for ach in all_achievements:
        status = "✅" if ach['id'] in unlocked_ids else "🔒"
        
        # Progress
        if ach['type'] == 'hunts':
            current = player['total_hunts']
        elif ach['type'] == 'level':
            current = player['level']
        elif ach['type'] == 'trophies':
            current = len(trophies)
        elif ach['type'] == 'coins':
            current = player['coins']
        else:
            current = 0
        
        progress = min(current, ach['req'])
        text += (
            f"{status} <b>{ach['name']}</b>\n"
            f"   {ach['desc']}\n"
            f"   Progress: {format_number(progress)}/{format_number(ach['req'])}\n"
            f"   💰 Reward: {format_number(ach['reward'])} koin\n\n"
        )
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Museum", callback_data="menu_museum")]
        ])
    )
