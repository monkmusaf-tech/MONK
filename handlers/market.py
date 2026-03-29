from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_player, get_inventory, get_animals, get_animal,
    get_p2p_listings, buy_p2p, add_inventory, add_coins,
    create_transaction, get_topup_packages, get_setting
)
from database.db import get_db
from utils.helpers import format_number, format_coins, rarity_badge, update_survival_stats

async def menu_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    player = await get_player(user.id)
    
    text = (
        f"🏪 <b>Market</b>\n\n"
        f"💰 Koinmu: <b>{format_number(player['coins'])}</b>\n\n"
        f"Pilih menu market:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Jual Inventori", callback_data="market_sell")],
        [InlineKeyboardButton("📈 Cek Harga Pasar", callback_data="market_prices")],
        [InlineKeyboardButton("🤝 P2P Trading", callback_data="market_p2p")],
        [InlineKeyboardButton("💎 Top-Up Koin", callback_data="market_topup")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
    ])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        pass

async def sell_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Get sellable items
    meats = await get_inventory(user.id, 'animal_meat')
    skins = await get_inventory(user.id, 'animal_skin')
    special = await get_inventory(user.id, 'special_item')
    
    all_items = meats + skins + special
    
    if not all_items:
        await query.edit_message_text(
            "🎒 <b>Inventori Kosong!</b>\n\nKamu belum punya hasil buruan untuk dijual.\nPergi berburu dulu!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🦌 Hunt", callback_data="menu_hunt")],
                [InlineKeyboardButton("◀️ Market", callback_data="menu_market")],
            ])
        )
        return
    
    # Calculate total value
    total_value = 0
    item_list = ""
    sell_buttons = []
    
    for item in all_items[:10]:  # Show max 10
        # Get price from animal data if meat/skin
        price = 0
        if item['item_type'] == 'animal_meat':
            animal_id = item['item_id'].replace("meat_", "")
            animal = await get_animal(animal_id)
            price = animal['meat_price'] * item['quantity'] if animal else 0
        elif item['item_type'] == 'animal_skin':
            animal_id = item['item_id'].replace("skin_", "")
            animal = await get_animal(animal_id)
            price = animal['skin_price'] * item['quantity'] if animal else 0
        
        total_value += price
        emoji = "🍖" if item['item_type'] == 'animal_meat' else "🧥" if item['item_type'] == 'animal_skin' else "🎁"
        item_list += f"• {emoji} {item['item_name']} x{item['quantity']} = {format_number(price)} koin\n"
        sell_buttons.append([InlineKeyboardButton(
            f"💰 Jual {item['item_name']} x{item['quantity']}",
            callback_data=f"sell_item_{item['item_type']}_{item['item_id']}"
        )])
    
    text = (
        f"💰 <b>Jual Inventori</b>\n\n"
        f"📦 Item yang bisa dijual:\n{item_list}\n"
        f"💎 Total estimasi: <b>{format_number(total_value)} koin</b>"
    )
    
    sell_buttons.append([InlineKeyboardButton(
        f"✅ Jual Semua ({format_number(total_value)} koin)",
        callback_data="sell_all"
    )])
    sell_buttons.append([InlineKeyboardButton("◀️ Market", callback_data="menu_market")])
    
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(sell_buttons))
    except Exception:
        pass

async def sell_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    parts = query.data.replace("sell_item_", "").split("_", 1)
    
    if query.data == "sell_all":
        await _sell_all_items(query, user.id)
        return
    
    item_type = parts[0]
    item_id = parts[1] if len(parts) > 1 else ""
    
    # Get item from inventory
    inv = await get_inventory(user.id)
    item = next((i for i in inv if i['item_type'] == item_type and i['item_id'] == item_id), None)
    
    if not item:
        await query.answer("❌ Item tidak ditemukan!", show_alert=True)
        return
    
    # Calculate price
    price = 0
    if item_type == 'animal_meat':
        animal_id = item_id.replace("meat_", "")
        animal = await get_animal(animal_id)
        price = animal['meat_price'] * item['quantity'] if animal else 0
    elif item_type == 'animal_skin':
        animal_id = item_id.replace("skin_", "")
        animal = await get_animal(animal_id)
        price = animal['skin_price'] * item['quantity'] if animal else 0
    
    if price <= 0:
        await query.answer("❌ Item tidak bisa dijual!", show_alert=True)
        return
    
    # Remove from inventory and add coins
    from database.queries import remove_inventory
    success = await remove_inventory(user.id, item_type, item_id, item['quantity'])
    if success:
        await add_coins(user.id, price)
        await query.answer(f"✅ Terjual +{format_number(price)} koin!", show_alert=True)
        await sell_inventory(update, context)
    else:
        await query.answer("❌ Gagal menjual!", show_alert=True)

async def _sell_all_items(query, user_id: int):
    meats = await get_inventory(user_id, 'animal_meat')
    skins = await get_inventory(user_id, 'animal_skin')
    
    total = 0
    from database.queries import remove_inventory
    
    for item in meats:
        animal_id = item['item_id'].replace("meat_", "")
        animal = await get_animal(animal_id)
        if animal:
            price = animal['meat_price'] * item['quantity']
            total += price
            await remove_inventory(user_id, item['item_type'], item['item_id'], item['quantity'])
    
    for item in skins:
        animal_id = item['item_id'].replace("skin_", "")
        animal = await get_animal(animal_id)
        if animal:
            price = animal['skin_price'] * item['quantity']
            total += price
            await remove_inventory(user_id, item['item_type'], item['item_id'], item['quantity'])
    
    if total > 0:
        await add_coins(user_id, total)
    
    text = (
        f"✅ <b>Semua Item Terjual!</b>\n\n"
        f"💰 Total pendapatan: <b>{format_number(total)} koin</b>\n\n"
        f"Inventori hasil buruan sudah dikosongkan."
    )
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🦌 Berburu Lagi", callback_data="menu_hunt")],
            [InlineKeyboardButton("◀️ Market", callback_data="menu_market")],
        ])
    )

async def check_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    import random
    
    # Sample prices with fluctuation display
    animals = await get_animals()
    
    text = "📈 <b>Harga Pasar Hari Ini</b>\n\n"
    text += "<i>Harga naik-turun setiap jam</i>\n\n"
    
    rarities = ["common", "uncommon", "rare", "epic", "legendary"]
    for rarity in rarities:
        rarity_animals = [a for a in animals if a['rarity'] == rarity][:3]
        if rarity_animals:
            from utils.helpers import RARITY_COLORS
            text += f"{RARITY_COLORS[rarity]} <b>{rarity.title()}</b>\n"
            for a in rarity_animals:
                fluc_meat = random.uniform(-0.1, 0.15)
                fluc_skin = random.uniform(-0.1, 0.15)
                meat = int(a['meat_price'] * (1 + fluc_meat))
                skin = int(a['skin_price'] * (1 + fluc_skin))
                trend_meat = "📈" if fluc_meat > 0 else "📉"
                trend_skin = "📈" if fluc_skin > 0 else "📉"
                text += f"• {a['emoji']} {a['name']}: 🍖{format_number(meat)}{trend_meat} 🧥{format_number(skin)}{trend_skin}\n"
            text += "\n"
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="market_prices")],
            [InlineKeyboardButton("◀️ Market", callback_data="menu_market")],
        ])
    )

async def p2p_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "🤝 <b>P2P Market</b>\n\n"
        "Beli & jual item langsung dengan player lain!\n\n"
        "Pilih aksi:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Lihat Listing", callback_data="p2p_list")],
        [InlineKeyboardButton("➕ Buat Listing", callback_data="p2p_create")],
        [InlineKeyboardButton("◀️ Market", callback_data="menu_market")],
    ])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def p2p_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    listings = await get_p2p_listings(active_only=True)
    
    if not listings:
        await query.edit_message_text(
            "🤝 <b>P2P Market</b>\n\nBelum ada listing aktif.\nJadi yang pertama buat listing!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Buat Listing", callback_data="p2p_create")],
                [InlineKeyboardButton("◀️ Kembali", callback_data="market_p2p")],
            ])
        )
        return
    
    text = "🤝 <b>P2P Listings Aktif</b>\n\n"
    buttons = []
    
    user = update.effective_user
    
    for listing in listings[:10]:
        item_emoji = "🍖" if "meat" in listing['item_type'] else "🧥" if "skin" in listing['item_type'] else "🎁"
        seller = listing['seller_name'] or f"Player#{listing['seller_id']}"
        text += (
            f"{item_emoji} <b>{listing['item_name']}</b> x{listing['quantity']}\n"
            f"💰 {format_number(listing['price_per_unit'])}/unit | 👤 {seller}\n\n"
        )
        if listing['seller_id'] != user.id:
            buttons.append([InlineKeyboardButton(
                f"🛒 Beli {listing['item_name']} ({format_number(listing['price_per_unit'])}/unit)",
                callback_data=f"p2p_buy_{listing['id']}"
            )])
    
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="market_p2p")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def p2p_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    listing_id = int(query.data.replace("p2p_buy_", ""))
    user = update.effective_user
    player = await get_player(user.id)
    
    # Get listing details first
    listings = await get_p2p_listings()
    listing = next((l for l in listings if l['id'] == listing_id), None)
    
    if not listing:
        await query.answer("❌ Listing sudah tidak tersedia!", show_alert=True)
        return
    
    total_cost = listing['price_per_unit'] * listing['quantity']
    
    if player['coins'] < total_cost:
        await query.answer(
            f"❌ Koin tidak cukup! Butuh {format_number(total_cost)} koin.",
            show_alert=True
        )
        return
    
    result = await buy_p2p(listing_id, user.id, listing['quantity'])
    
    if result:
        await add_inventory(user.id, result['item_type'], result['item_id'], result['item_name'], result['quantity'])
        await query.answer(
            f"✅ Berhasil membeli {result['item_name']} x{result['quantity']}!",
            show_alert=True
        )
        await p2p_list(update, context)
    else:
        await query.answer("❌ Gagal membeli! Cek lagi koin kamu.", show_alert=True)

async def p2p_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for'] = 'p2p_create'
    
    await query.edit_message_text(
        "➕ <b>Buat P2P Listing</b>\n\n"
        "Ketik pesan dengan format:\n"
        "<code>nama_item | jumlah | harga_per_unit</code>\n\n"
        "Contoh:\n"
        "<code>Daging Rusa | 5 | 200</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Batal", callback_data="market_p2p")
        ]])
    )

async def menu_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    packages = await get_topup_packages()
    payment_info = await get_setting("payment_info") or "Hubungi admin untuk info pembayaran"
    
    text = "💎 <b>Top-Up Koin</b>\n\n"
    text += "📦 <b>Paket Tersedia:</b>\n\n"
    
    buttons = []
    for pkg in packages:
        bonus = f" (+{pkg['bonus_percent']}% bonus)" if pkg['bonus_percent'] > 0 else ""
        actual_coins = int(pkg['coins'] * (1 + pkg['bonus_percent'] / 100))
        text += f"• {pkg['name']}: {format_number(actual_coins)} koin = Rp {format_number(pkg['price'])}{bonus}\n"
        buttons.append([InlineKeyboardButton(
            f"💎 {pkg['name']} - Rp {format_number(pkg['price'])}",
            callback_data=f"topup_select_{pkg['id']}"
        )])
    
    text += f"\n💳 <b>Cara Bayar:</b>\n{payment_info}"
    
    buttons.append([InlineKeyboardButton("◀️ Market", callback_data="menu_market")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
