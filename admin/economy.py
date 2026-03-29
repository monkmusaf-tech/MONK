from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_topup_packages, get_animals, get_setting, add_log
from database.db import get_db
from utils.helpers import is_admin, format_number

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    double_exp = await get_setting("double_exp") == "1"
    double_coin = await get_setting("double_coin") == "1"

    text = (
        f"💰 <b>Harga & Ekonomi</b>\n\n"
        f"Event Aktif:\n"
        f"{'⭐ Double EXP: ON' if double_exp else '⭐ Double EXP: OFF'}\n"
        f"{'💰 Double COIN: ON' if double_coin else '💰 Double COIN: OFF'}\n\n"
        f"Pilih pengaturan:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Set Harga Hewan", callback_data="eco_prices")],
        [InlineKeyboardButton("💎 Paket Top-Up", callback_data="eco_topup")],
        [InlineKeyboardButton("🎯 Multiplier Rarity", callback_data="eco_rarity")],
        [
            InlineKeyboardButton(
                "⭐ Double EXP OFF" if double_exp else "⭐ Double EXP ON",
                callback_data="eco_event_exp"
            ),
            InlineKeyboardButton(
                "💰 Double COIN OFF" if double_coin else "💰 Double COIN ON",
                callback_data="eco_event_coin"
            ),
        ],
        [InlineKeyboardButton("💳 Info Pembayaran", callback_data="eco_payment")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def set_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    animals = await get_animals()
    page = context.user_data.get('eco_price_page', 0)
    per_page = 6
    total_pages = max(1, (len(animals) + per_page - 1) // per_page)
    page_animals = animals[page*per_page:(page+1)*per_page]

    text = "💰 <b>Set Harga Hewan</b>\n\nPilih hewan untuk edit harga:\n\n"
    buttons = []

    for a in page_animals:
        text += f"• {a['emoji']} {a['name']}: 🍖{format_number(a['meat_price'])} | 🧥{format_number(a['skin_price'])}\n"
        buttons.append([InlineKeyboardButton(
            f"✏️ {a['name']}",
            callback_data=f"eco_edit_price_{a['id']}"
        )])

    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️", callback_data=f"eco_price_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages-1: nav.append(InlineKeyboardButton("▶️", callback_data=f"eco_price_page_{page+1}"))
    if nav: buttons.append(nav)

    buttons.append([InlineKeyboardButton("◀️ Ekonomi", callback_data="admin_economy")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def topup_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    packages = await get_topup_packages()
    text = "💎 <b>Paket Top-Up</b>\n\n"
    buttons = []

    for pkg in packages:
        bonus = f" +{pkg['bonus_percent']}%" if pkg['bonus_percent'] > 0 else ""
        actual = int(pkg['coins'] * (1 + pkg['bonus_percent']/100))
        text += f"• {pkg['name']}: {format_number(actual)} koin = Rp {format_number(pkg['price'])}{bonus}\n"
        buttons.append([InlineKeyboardButton(
            f"✏️ {pkg['name']}",
            callback_data=f"edit_pkg_{pkg['id']}"
        )])

    buttons.append([InlineKeyboardButton("➕ Tambah Paket", callback_data="add_topup_pkg")])
    buttons.append([InlineKeyboardButton("◀️ Ekonomi", callback_data="admin_economy")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def rarity_multiplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    rarities = ["common", "uncommon", "rare", "epic", "legendary", "mythic", "boss"]
    text = "🎯 <b>Multiplier Reward per Rarity</b>\n\n"
    buttons = []

    for r in rarities:
        key = f"multiplier_{r}"
        val = await get_setting(key) or "1.0"
        text += f"• {r.title()}: {val}x\n"
        buttons.append([InlineKeyboardButton(
            f"✏️ {r.title()} ({val}x)",
            callback_data=f"edit_multiplier_{r}"
        )])

    buttons.append([InlineKeyboardButton("◀️ Ekonomi", callback_data="admin_economy")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def toggle_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    event_type = query.data.replace("eco_event_", "")

    if event_type == "exp":
        key = "double_exp"
        label = "Double EXP"
    elif event_type == "coin":
        key = "double_coin"
        label = "Double COIN"
    else:
        return

    current = await get_setting(key) == "1"
    new_val = "0" if current else "1"

    async with await get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?,?)",
            (key, new_val)
        )
        await db.commit()

    status = "ON ✅" if new_val == "1" else "OFF ❌"
    await add_log(query.from_user.id, "toggle_event", f"{label} diset {status}", "info")
    await query.answer(f"✅ {label} sekarang {status}", show_alert=True)
    await menu(update, context)

async def set_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    current = await get_setting("payment_info") or "-"
    context.user_data['admin_action'] = 'set_payment_info'

    await query.edit_message_text(
        f"💳 <b>Edit Info Pembayaran</b>\n\nSaat ini:\n{current}\n\n"
        f"Kirim teks baru untuk mengganti info pembayaran:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_economy")]])
    )
