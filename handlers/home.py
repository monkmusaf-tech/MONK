from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_player, get_inventory, remove_inventory, add_coins, add_inventory,
    get_foods, get_setting
)
from database.db import get_db
from utils.helpers import (
    format_number, player_status_bar, get_survival_warning, update_survival_stats
)
import json

async def menu_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    await update_survival_stats(user.id)
    player = await get_player(user.id)
    
    # Home level info
    home_names = {1: "Gubuk Bambu 🏕️", 2: "Rumah Kayu 🏠", 3: "Rumah Bata 🏡", 4: "Rumah Mewah 🏰", 5: "Istana Pemburu 🏯"}
    home_name = home_names.get(player['home_level'], "Rumah")
    
    warning = get_survival_warning(player)
    
    text = (
        f"🏠 <b>{home_name}</b>\n\n"
        f"📊 <b>Status Survival:</b>\n"
        f"🍖 Lapar: {player_status_bar(player['hunger'])}\n"
        f"💧 Haus: {player_status_bar(player['thirst'])}\n"
        f"⚡ Stamina: {player_status_bar(player['stamina'])}\n"
        f"😴 Istirahat: {player_status_bar(player['rest'])}\n\n"
        f"{warning}\n\n"
        f"Pilih aksi:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍖 Makan", callback_data="home_eat"),
            InlineKeyboardButton("💧 Minum", callback_data="home_drink"),
        ],
        [
            InlineKeyboardButton("😴 Istirahat", callback_data="home_rest"),
            InlineKeyboardButton("🍳 Masak", callback_data="home_craft"),
        ],
        [InlineKeyboardButton("🏠 Upgrade Rumah", callback_data="upgrade_home")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def eat_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Check if specific food to eat
    if query.data.startswith("eat_"):
        food_id = query.data.replace("eat_", "")
        if food_id == "home":
            await show_food_menu(query, user.id, "food")
            return
        await _consume_food(query, user.id, food_id)
        return
    
    await show_food_menu(query, user.id, "food")

async def drink_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data.startswith("drink_") and len(query.data) > 6:
        drink_id = query.data.replace("drink_", "")
        if drink_id == "home":
            await show_food_menu(query, user.id, "drink")
            return
        await _consume_food(query, user.id, drink_id, is_drink=True)
        return
    
    await show_food_menu(query, user.id, "drink")

async def show_food_menu(query, user_id: int, food_type: str):
    foods = await get_foods()
    foods = [f for f in foods if f['type'] == food_type]
    
    # Get inventory food items
    inv_food = await get_inventory(user_id, 'food')
    inv_dict = {item['item_id']: item['quantity'] for item in inv_food}
    
    emoji = "🍖" if food_type == "food" else "💧"
    title = "Makan" if food_type == "food" else "Minum"
    
    text = f"{emoji} <b>{title}</b>\n\nPilih yang mau dikonsumsi:"
    buttons = []
    
    for food in foods:
        qty = inv_dict.get(food['id'], 0)
        if qty > 0:
            cb = f"eat_{food['id']}" if food_type == "food" else f"drink_{food['id']}"
            restore = food['hunger_restore'] if food_type == "food" else food['thirst_restore']
            buttons.append([InlineKeyboardButton(
                f"{food['emoji']} {food['name']} (x{qty}) +{int(restore)} {title.lower()}",
                callback_data=cb
            )])
    
    if not buttons:
        text += "\n\n❌ Tidak ada makanan/minuman di inventori!\nMasak dulu atau beli di market."
    
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="menu_home")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def _consume_food(query, user_id: int, food_id: str, is_drink: bool = False):
    foods = await get_foods()
    food = next((f for f in foods if f['id'] == food_id), None)
    
    if not food:
        await query.answer("❌ Item tidak ditemukan!", show_alert=True)
        return
    
    food_type = "drink" if is_drink else "food"
    success = await remove_inventory(user_id, food_type, food_id)
    
    if not success:
        await query.answer("❌ Item habis!", show_alert=True)
        return
    
    # Apply effects
    player = await get_player(user_id)
    new_hunger = min(100, player['hunger'] + food['hunger_restore'])
    new_thirst = min(100, player['thirst'] + food['thirst_restore'])
    new_stamina = min(100, player['stamina'] + food['stamina_restore'])
    
    async with await get_db() as db:
        await db.execute(
            "UPDATE players SET hunger=?, thirst=?, stamina=? WHERE user_id=?",
            (new_hunger, new_thirst, new_stamina, user_id)
        )
        await db.commit()
    
    msg = f"✅ Mengonsumsi {food['emoji']} {food['name']}\n\n"
    if food['hunger_restore'] > 0:
        msg += f"🍖 Kenyang: +{int(food['hunger_restore'])}\n"
    if food['thirst_restore'] > 0:
        msg += f"💧 Haus: +{int(food['thirst_restore'])}\n"
    if food['stamina_restore'] > 0:
        msg += f"⚡ Stamina: +{int(food['stamina_restore'])}\n"
    
    await query.answer(msg, show_alert=True)
    
    # Refresh home menu
    from telegram import Update
    class FakeUpdate:
        effective_user = query.from_user
        callback_query = query
    await menu_home(FakeUpdate(), None)

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "rest_":
        # Show rest options
        user = update.effective_user
        player = await get_player(user.id)
        
        text = (
            f"😴 <b>Istirahat</b>\n\n"
            f"Pilih cara istirahat:\n\n"
            f"• Gratis - istirahat singkat\n"
            f"• Premium - istirahat penuh + bonus\n"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("😴 Istirahat Sebentar (Gratis)", callback_data="rest_free")],
            [InlineKeyboardButton("🛏️ Tidur Nyenyak (500 koin)", callback_data="rest_paid")],
            [InlineKeyboardButton("💆 Istirahat Premium (2000 koin)", callback_data="rest_premium")],
            [InlineKeyboardButton("◀️ Kembali", callback_data="menu_home")],
        ])
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
        return
    
    user = update.effective_user
    player = await get_player(user.id)
    
    if data == "rest_free":
        stamina_gain = 20
        rest_gain = 15
        cost = 0
    elif data == "rest_paid":
        stamina_gain = 60
        rest_gain = 50
        cost = 500
    elif data == "rest_premium":
        stamina_gain = 100
        rest_gain = 100
        cost = 2000
    else:
        return
    
    if cost > 0 and player['coins'] < cost:
        await query.answer(f"❌ Butuh {format_number(cost)} koin!", show_alert=True)
        return
    
    new_stamina = min(100, player['stamina'] + stamina_gain)
    new_rest = min(100, player['rest'] + rest_gain)
    
    async with await get_db() as db:
        if cost > 0:
            await db.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (cost, user.id))
        await db.execute(
            "UPDATE players SET stamina=?, rest=? WHERE user_id=?",
            (new_stamina, new_rest, user.id)
        )
        await db.commit()
    
    msg = (
        f"✅ <b>Selesai Istirahat!</b>\n\n"
        f"⚡ Stamina: +{stamina_gain} ({int(new_stamina)}/100)\n"
        f"😴 Rest: +{rest_gain} ({int(new_rest)}/100)"
    )
    if cost > 0:
        msg += f"\n💰 Biaya: -{format_number(cost)} koin"
    
    await query.edit_message_text(
        msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🦌 Berburu!", callback_data="menu_hunt")],
            [InlineKeyboardButton("◀️ Rumah", callback_data="menu_home")],
        ])
    )

async def craft_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data.startswith("craft_") and len(query.data) > 6:
        food_id = query.data.replace("craft_", "")
        await _do_craft(query, user.id, food_id)
        return
    
    # Show craftable foods
    foods = await get_foods()
    
    text = "🍳 <b>Masak Makanan</b>\n\nPilih resep:"
    buttons = []
    
    inv = await get_inventory(user.id)
    inv_dict = {}
    for item in inv:
        inv_dict[item['item_id']] = item['quantity']
    
    for food in foods:
        recipe = json.loads(food['craft_recipe']) if food['craft_recipe'] else {}
        
        can_craft = True
        recipe_text = ""
        for ingredient, qty in recipe.items():
            have = inv_dict.get(f"meat_{ingredient}", 0)
            if have < qty:
                can_craft = False
            recipe_text += f"🍖Daging {ingredient} x{qty}"
        
        if not recipe_text:
            recipe_text = "Tidak perlu bahan"
        
        status = "✅" if can_craft else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {food['emoji']} {food['name']}",
            callback_data=f"craft_{food['id']}" if can_craft else "noop"
        )])
    
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="menu_home")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def _do_craft(query, user_id: int, food_id: str):
    foods = await get_foods()
    food = next((f for f in foods if f['id'] == food_id), None)
    
    if not food:
        await query.answer("❌ Resep tidak ditemukan!", show_alert=True)
        return
    
    recipe = json.loads(food['craft_recipe']) if food['craft_recipe'] else {}
    
    # Check and consume ingredients
    for ingredient, qty in recipe.items():
        success = await remove_inventory(user_id, 'animal_meat', f"meat_{ingredient}", qty)
        if not success:
            await query.answer(f"❌ Bahan kurang! Butuh Daging {ingredient} x{qty}", show_alert=True)
            return
    
    # Add crafted food
    food_type = "food" if food['type'] == "food" else "drink"
    await add_inventory(user_id, food_type, food['id'], food['name'])
    
    await query.answer(
        f"✅ Berhasil masak {food['emoji']} {food['name']}!",
        show_alert=True
    )

async def upgrade_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    
    current_level = player['home_level']
    
    if current_level >= 5:
        await query.edit_message_text(
            "🏯 <b>Rumah Sudah Maksimal!</b>\n\nRumahmu sudah di level tertinggi - Istana Pemburu!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Rumah", callback_data="menu_home")
            ]])
        )
        return
    
    upgrade_costs = {1: 5000, 2: 20000, 3: 100000, 4: 500000}
    next_names = {2: "Rumah Kayu 🏠", 3: "Rumah Bata 🏡", 4: "Rumah Mewah 🏰", 5: "Istana Pemburu 🏯"}
    
    cost = upgrade_costs.get(current_level, 0)
    next_name = next_names.get(current_level + 1, "???")
    
    if query.data == "upgrade_home_confirm":
        if player['coins'] < cost:
            await query.answer(f"❌ Butuh {format_number(cost)} koin!", show_alert=True)
            return
        
        async with await get_db() as db:
            await db.execute(
                "UPDATE players SET home_level=home_level+1, coins=coins-? WHERE user_id=?",
                (cost, user.id)
            )
            await db.commit()
        
        await query.edit_message_text(
            f"🎊 <b>Rumah Diupgrade!</b>\n\nSelamat! Rumahmu sekarang: <b>{next_name}</b>\n"
            f"Bonus survival regen meningkat!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Rumah", callback_data="menu_home")
            ]])
        )
        return
    
    text = (
        f"🏠 <b>Upgrade Rumah</b>\n\n"
        f"Level sekarang: {current_level}\n"
        f"Upgrade ke: <b>{next_name}</b>\n\n"
        f"💰 Biaya: <b>{format_number(cost)} koin</b>\n"
        f"💳 Koinmu: <b>{format_number(player['coins'])}</b>\n\n"
        f"Manfaat upgrade:\n"
        f"• Regen hunger/thirst/rest lebih cepat\n"
        f"• Storage slot lebih banyak\n"
        f"• Bonus buff saat istirahat"
    )
    
    can_upgrade = player['coins'] >= cost
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"✅ Upgrade ({format_number(cost)} koin)" if can_upgrade else f"❌ Koin Kurang",
            callback_data="upgrade_home_confirm" if can_upgrade else "noop"
        )],
        [InlineKeyboardButton("◀️ Kembali", callback_data="menu_home")],
    ])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
