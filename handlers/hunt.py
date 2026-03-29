import random
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_player, create_player, get_animals, get_animal, get_maps,
    add_inventory, add_coins, add_exp, get_player_weapons, get_weapon,
    add_log, check_achievements, get_setting, update_player
)
from database.db import get_db
from utils.helpers import (
    rarity_badge, format_coins, format_number, send_with_photo,
    main_menu_keyboard, RARITY_COLORS, update_survival_stats, player_status_bar
)

RARITY_SPAWN_CHANCE = {
    "common": 40,
    "uncommon": 25,
    "rare": 15,
    "epic": 8,
    "legendary": 5,
    "mythic": 2,
    "boss": 0  # Boss only via event
}

async def menu_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    if not player:
        player = await create_player(user.id, user.username or "", user.first_name)
    
    await update_survival_stats(user.id)
    player = await get_player(user.id)
    
    # Check survival
    if player['stamina'] < 10:
        await query.edit_message_text(
            "😴 <b>Stamina Habis!</b>\n\n"
            "Kamu terlalu lelah untuk berburu.\n"
            "Pergi ke 🏠 Rumah untuk istirahat dulu!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Ke Rumah", callback_data="menu_home")],
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
            ])
        )
        return
    
    if player['hunger'] < 5:
        await query.edit_message_text(
            "😫 <b>Sangat Lapar!</b>\n\n"
            "Kamu terlalu lapar untuk berburu.\n"
            "Makan dulu di 🏠 Rumah!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Ke Rumah", callback_data="menu_home")],
                [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
            ])
        )
        return
    
    # Get available maps
    maps = await get_maps(active_only=True)
    
    text = (
        f"🦌 <b>Menu Hunt</b>\n\n"
        f"⚡ Stamina: {player_status_bar(player['stamina'])}\n"
        f"🍖 Lapar: {player_status_bar(player['hunger'])}\n"
        f"💧 Haus: {player_status_bar(player['thirst'])}\n\n"
        f"📍 Pilih lokasi berburu:"
    )
    
    buttons = []
    for m in maps:
        if player['level'] >= m['min_level']:
            buttons.append([InlineKeyboardButton(
                f"{m['emoji']} {m['name']} (Lv.{m['min_level']}+)",
                callback_data=f"map_{m['id']}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                f"🔒 {m['name']} (Butuh Lv.{m['min_level']})",
                callback_data="noop"
            )])
    
    buttons.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def select_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    map_id = query.data.replace("map_", "")
    context.user_data['selected_map'] = map_id
    context.user_data['filter_rarity'] = 'all'
    context.user_data['hunt_page'] = 0
    
    await show_animal_list(query, context, map_id)

async def show_animal_list(query, context, map_id: str, rarity_filter: str = 'all', page: int = 0):
    maps = await get_maps()
    map_data = next((m for m in maps if m['id'] == map_id), None)
    
    if rarity_filter == 'all':
        animals = await get_animals(map_id=map_id)
    else:
        animals = await get_animals(map_id=map_id, rarity=rarity_filter)
    
    per_page = 6
    total = len(animals)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    page_animals = animals[page * per_page:(page + 1) * per_page]
    
    map_name = map_data['name'] if map_data else map_id
    map_emoji = map_data['emoji'] if map_data else '🗺️'
    
    text = (
        f"{map_emoji} <b>{map_name}</b>\n"
        f"📋 {total} hewan tersedia\n\n"
        f"Pilih hewan untuk diburu:"
    )
    
    buttons = []
    for animal in page_animals:
        badge = RARITY_COLORS.get(animal['rarity'], '⬜')
        buttons.append([InlineKeyboardButton(
            f"{badge} {animal['emoji']} {animal['name']}",
            callback_data=f"hunt_animal_{animal['id']}"
        )])
    
    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"map_{map_id}_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"map_{map_id}_page_{page+1}"))
    if nav:
        buttons.append(nav)
    
    # Filter buttons
    rarity_row = [
        InlineKeyboardButton("🔍 Cari", callback_data="search_animal"),
        InlineKeyboardButton("🎯 Filter", callback_data=f"filter_rarity_{map_id}"),
    ]
    buttons.append(rarity_row)
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="menu_hunt")])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        pass

async def select_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    animal_id = query.data.replace("hunt_animal_", "")
    animal = await get_animal(animal_id)
    
    if not animal:
        await query.answer("❌ Hewan tidak ditemukan!", show_alert=True)
        return
    
    user = update.effective_user
    player = await get_player(user.id)
    
    # Check weapon grade
    owned_weapons = await get_player_weapons(user.id)
    max_grade = max([w['grade'] for w in owned_weapons], default=1) if owned_weapons else 1
    
    # Build animal info
    behavior_text = {
        "flee": "🏃 Kabur",
        "aggressive": "⚔️ Agresif",
        "neutral": "😐 Netral",
        "boss": "👹 Boss"
    }.get(animal['behavior'], animal['behavior'])
    
    text = (
        f"{animal['emoji']} <b>{animal['name']}</b>\n"
        f"{rarity_badge(animal['rarity'])}\n\n"
        f"📊 <b>Info:</b>\n"
        f"• Sifat: {behavior_text}\n"
        f"• Spawn: {animal['spawn_time']}\n"
        f"• HP: {format_number(animal['hp'])}\n\n"
        f"💰 <b>Reward:</b>\n"
        f"• 🍖 Daging: {format_number(animal['meat_price'])} koin\n"
        f"• 🧥 Kulit: {format_number(animal['skin_price'])} koin\n"
        f"• 🎁 {animal['main_reward']} x{animal['main_reward_amount']}\n"
        f"• ⭐ EXP: +{animal['exp_reward']}\n\n"
    )
    
    if animal['description']:
        text += f"📝 {animal['description']}\n\n"
    
    # Weapon requirement check
    if max_grade < animal['min_weapon_grade']:
        text += f"⚠️ <b>Perlu senjata Grade {animal['min_weapon_grade']}+!</b>\n"
        text += f"Senjatamu saat ini max Grade {max_grade}"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔫 Beli Senjata", callback_data="menu_weapons")],
            [InlineKeyboardButton("◀️ Kembali", callback_data=f"map_{animal['map_id']}")],
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎯 Mulai Berburu!", callback_data=f"do_hunt_{animal_id}")],
            [InlineKeyboardButton("◀️ Kembali", callback_data=f"map_{animal['map_id']}")],
        ])
    
    if animal.get('photo_file_id'):
        try:
            await query.message.reply_photo(
                photo=animal['photo_file_id'],
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await query.message.delete()
            return
        except Exception:
            pass
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def do_hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🎯 Berburu...")
    
    user = update.effective_user
    animal_id = query.data.replace("do_hunt_", "")
    
    animal = await get_animal(animal_id)
    player = await get_player(user.id)
    
    if not animal or not player:
        await query.answer("❌ Error!", show_alert=True)
        return
    
    # Check cooldown
    if player['last_hunt']:
        from datetime import datetime, timezone
        try:
            last = datetime.fromisoformat(player['last_hunt'].replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            cooldown = int(await get_setting("hunt_cooldown") or 300)
            elapsed = (now - last).total_seconds()
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                mins = remaining // 60
                secs = remaining % 60
                await query.answer(
                    f"⏳ Cooldown {mins}m {secs}s lagi!",
                    show_alert=True
                )
                return
        except Exception:
            pass
    
    # Update survival stats
    await update_survival_stats(user.id)
    player = await get_player(user.id)
    
    # Check stamina
    if player['stamina'] < 10:
        await query.answer("😴 Stamina habis! Istirahat dulu!", show_alert=True)
        return
    
    # Get equipped weapon
    owned_weapons = await get_player_weapons(user.id)
    equipped_id = player.get('weapon_equipped', 'slingshot')
    equipped = next((w for w in owned_weapons if w['weapon_id'] == equipped_id), None)
    if not equipped and owned_weapons:
        equipped = owned_weapons[0]
    
    weapon_data = await get_weapon(equipped['weapon_id']) if equipped else None
    accuracy = weapon_data['accuracy'] if weapon_data else 0.5
    damage = weapon_data['damage'] if weapon_data else 5
    
    # Check active events for multipliers
    double_exp = await get_setting("double_exp") == "1"
    double_coin = await get_setting("double_coin") == "1"
    
    # Hunt calculation
    hunt_success = random.random() < accuracy
    
    # Behavior modifier
    if animal['behavior'] == 'flee':
        flee_chance = 0.3
        if random.random() < flee_chance:
            hunt_success = False
            fled = True
        else:
            fled = False
    elif animal['behavior'] == 'aggressive':
        # Take damage if failed
        fled = False
    else:
        fled = False
    
    # Drain stamina
    stamina_cost = 10 + (animal['min_weapon_grade'] * 2)
    new_stamina = max(0, player['stamina'] - stamina_cost)
    new_hunger = max(0, player['hunger'] - 5)
    new_thirst = max(0, player['thirst'] - 8)
    
    async with await get_db() as db:
        await db.execute(
            """UPDATE players SET stamina=?, hunger=?, thirst=?, 
            last_hunt=datetime('now'), last_active=datetime('now'),
            total_hunts=total_hunts+1
            WHERE user_id=?""",
            (new_stamina, new_hunger, new_thirst, user.id)
        )
        await db.commit()
    
    if hunt_success:
        # Calculate rewards
        meat_price = await _get_current_price(f"meat_{animal_id}", animal['meat_price'])
        skin_price = await _get_current_price(f"skin_{animal_id}", animal['skin_price'])
        
        # Apply double coin event
        total_coins = meat_price + skin_price
        if double_coin:
            total_coins *= 2
        
        exp_gain = animal['exp_reward']
        if double_exp:
            exp_gain *= 2
        
        # Add to inventory
        await add_inventory(user.id, 'animal_meat', f"meat_{animal_id}", f"Daging {animal['name']}")
        await add_inventory(user.id, 'animal_skin', f"skin_{animal_id}", f"Kulit {animal['name']}")
        
        # Add main reward
        if animal['main_reward']:
            await add_inventory(
                user.id, 'special_item',
                f"reward_{animal_id}",
                animal['main_reward'],
                animal['main_reward_amount']
            )
        
        # Update stats
        await add_coins(user.id, total_coins)
        new_level, leveled_up = await add_exp(user.id, exp_gain)
        
        async with await get_db() as db:
            await db.execute(
                "UPDATE players SET total_kills=total_kills+1 WHERE user_id=?",
                (user.id,)
            )
            await db.commit()
        
        # Check achievements
        new_achievements = await check_achievements(user.id)
        
        result_text = (
            f"🎯 <b>BERHASIL DIBURU!</b>\n\n"
            f"{animal['emoji']} <b>{animal['name']}</b> {rarity_badge(animal['rarity'])}\n\n"
            f"💰 <b>Reward:</b>\n"
            f"• 🍖 Daging {animal['name']}: +{format_number(meat_price)} koin\n"
            f"• 🧥 Kulit {animal['name']}: +{format_number(skin_price)} koin\n"
            f"• 🎁 {animal['main_reward']} x{animal['main_reward_amount']}\n"
            f"• ⭐ EXP: +{exp_gain}"
        )
        
        if double_coin:
            result_text += " 🎉2x Event!"
        if double_exp:
            result_text += " ⭐2x EXP!"
        
        result_text += f"\n\n💰 Total: +{format_number(total_coins)} koin"
        
        if leveled_up:
            result_text += f"\n\n🎊 <b>LEVEL UP! Sekarang Level {new_level}!</b>"
        
        if new_achievements:
            result_text += "\n\n🏆 <b>Achievement Baru:</b>"
            for ach in new_achievements:
                result_text += f"\n• {ach['name']} (+{format_number(ach['reward'])} koin)"
        
        result_text += f"\n\n⚡ Stamina: {int(new_stamina)}/100"
        
        await add_log(user.id, "hunt_success", f"Berhasil memburu {animal['name']}")
    
    elif fled:
        result_text = (
            f"💨 <b>HEWAN KABUR!</b>\n\n"
            f"{animal['emoji']} {animal['name']} berhasil melarikan diri!\n\n"
            f"💡 Tip: Gunakan 🪤 Jebakan untuk mengurangi peluang kabur.\n\n"
            f"⚡ Stamina: {int(new_stamina)}/100"
        )
    else:
        damage_taken = 0
        if animal['behavior'] == 'aggressive':
            damage_taken = random.randint(5, 20)
            new_stamina = max(0, new_stamina - damage_taken)
            async with await get_db() as db:
                await db.execute(
                    "UPDATE players SET stamina=? WHERE user_id=?",
                    (new_stamina, user.id)
                )
                await db.commit()
        
        result_text = (
            f"❌ <b>GAGAL BERBURU!</b>\n\n"
            f"{animal['emoji']} {animal['name']} berhasil menghindar!\n"
        )
        if damage_taken > 0:
            result_text += f"⚔️ Kamu diserang! -{damage_taken} stamina\n"
        result_text += (
            f"\n💡 Tip: Upgrade senjata untuk akurasi lebih tinggi!\n\n"
            f"⚡ Stamina: {int(new_stamina)}/100"
        )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Berburu Lagi", callback_data=f"map_{animal['map_id']}"),
            InlineKeyboardButton("🏪 Jual", callback_data="market_sell"),
        ],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]
    ])
    
    try:
        await query.edit_message_text(result_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await query.message.reply_text(result_text, parse_mode="HTML", reply_markup=keyboard)

async def _get_current_price(item_id: str, base_price: int) -> int:
    import random
    fluc = random.uniform(-0.1, 0.15)
    return max(int(base_price * 0.7), int(base_price * (1 + fluc)))

async def filter_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    map_id = parts[2]
    
    rarities = ["all", "common", "uncommon", "rare", "epic", "legendary", "mythic", "boss"]
    rarity_labels = {
        "all": "🌐 Semua",
        "common": "⬜ Common",
        "uncommon": "🟩 Uncommon",
        "rare": "🟦 Rare",
        "epic": "🟪 Epic",
        "legendary": "🟨 Legendary",
        "mythic": "🟥 Mythic",
        "boss": "💀 Boss",
    }
    
    buttons = []
    for r in rarities:
        buttons.append([InlineKeyboardButton(
            rarity_labels[r],
            callback_data=f"filter_rarity_{map_id}_{r}"
        )])
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data=f"map_{map_id}")])
    
    await query.edit_message_text(
        "🎯 <b>Filter Rarity</b>\n\nPilih rarity hewan:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def search_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'search_animal'
    await query.edit_message_text(
        "🔍 <b>Cari Hewan</b>\n\nKetik nama hewan yang ingin dicari:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data="menu_hunt")
        ]])
    )
