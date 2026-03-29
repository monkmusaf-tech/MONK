from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_all_settings, get_setting, add_log
from database.db import get_db
from utils.helpers import is_admin, format_number

PHOTO_KEYS = {
    "lobby_photo": "🏠 Foto Lobby",
    "hunt_photo": "🦌 Foto Hunt",
    "market_photo": "🏪 Foto Market",
    "home_photo": "🏡 Foto Rumah",
    "museum_photo": "🏛️ Foto Museum",
    "boss_photo": "👹 Foto Boss",
}

TOGGLE_FEATURES = {
    "maintenance_mode": "🔧 Maintenance Mode",
    "double_exp": "⭐ Double EXP",
    "double_coin": "💰 Double COIN",
    "p2p_enabled": "🤝 P2P Market",
    "museum_enabled": "🏛️ Museum",
    "boss_enabled": "👹 Boss Spawn",
}

GAME_PARAMS = {
    "hunt_cooldown": ("⏱️ Cooldown Hunt (detik)", "300"),
    "max_inventory": ("🎒 Max Inventori", "100"),
    "spawn_rate": ("🦌 Spawn Rate", "1.0"),
    "stamina_regen": ("⚡ Regen Stamina/menit", "1"),
    "hunger_drain": ("🍖 Drain Lapar/jam", "2"),
    "thirst_drain": ("💧 Drain Haus/jam", "3"),
    "rest_drain": ("😴 Drain Istirahat/jam", "1"),
}

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    maintenance = await get_setting("maintenance_mode") == "1"

    text = (
        f"🤖 <b>Pengaturan Bot</b>\n\n"
        f"Status: {'🔴 MAINTENANCE' if maintenance else '🟢 ONLINE'}\n\n"
        f"Pilih pengaturan:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Pengaturan Foto", callback_data="setting_photos")],
        [InlineKeyboardButton("⚙️ Parameter Game", callback_data="setting_params")],
        [InlineKeyboardButton("🔧 Toggle Fitur", callback_data="setting_toggles")],
        [InlineKeyboardButton("💬 Welcome Message", callback_data="setting_welcome")],
        [InlineKeyboardButton("💳 Info Pembayaran", callback_data="eco_payment")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def set_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    data = query.data

    if data == "setting_photos":
        # Show photo menu
        settings = await get_all_settings()
        text = "📸 <b>Pengaturan Foto</b>\n\nPilih foto yang mau diubah:"
        buttons = []

        for key, label in PHOTO_KEYS.items():
            has_photo = "✅" if settings.get(key) else "❌"
            buttons.append([InlineKeyboardButton(f"{has_photo} {label}", callback_data=f"setting_photo_{key}")])

        buttons.append([InlineKeyboardButton("◀️ Pengaturan", callback_data="admin_settings")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # specific photo key
    photo_key = data.replace("setting_photo_", "")
    if photo_key not in PHOTO_KEYS:
        return

    label = PHOTO_KEYS[photo_key]
    current = await get_setting(photo_key)

    context.user_data['upload_photo_for'] = f"setting_{photo_key}"

    text = (
        f"📸 <b>Set {label}</b>\n\n"
        f"Status: {'✅ Ada foto' if current else '❌ Belum ada foto'}\n\n"
        f"Kirim foto baru untuk menggantinya.\n"
        f"Atau klik hapus untuk menghapus foto:"
    )

    buttons = []
    if current:
        buttons.append([InlineKeyboardButton("🗑️ Hapus Foto", callback_data=f"del_photo_{photo_key}")])
    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="setting_photos")])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def game_params(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    settings = await get_all_settings()
    text = "⚙️ <b>Parameter Game</b>\n\nKlik untuk edit:\n\n"
    buttons = []

    for key, (label, default) in GAME_PARAMS.items():
        val = settings.get(key, default)
        text += f"• {label}: <b>{val}</b>\n"
        buttons.append([InlineKeyboardButton(f"✏️ {label}", callback_data=f"edit_param_{key}")])

    buttons.append([InlineKeyboardButton("◀️ Pengaturan", callback_data="admin_settings")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def toggle_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    data = query.data

    if data == "setting_toggles":
        # Show toggle menu
        settings = await get_all_settings()
        text = "🔧 <b>Toggle Fitur</b>\n\nKlik untuk toggle on/off:"
        buttons = []

        for key, label in TOGGLE_FEATURES.items():
            is_on = settings.get(key, "0") == "1"
            status = "✅ ON" if is_on else "❌ OFF"
            buttons.append([InlineKeyboardButton(f"{label}: {status}", callback_data=f"setting_toggle_{key}")])

        buttons.append([InlineKeyboardButton("◀️ Pengaturan", callback_data="admin_settings")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    # Toggle specific feature
    feature_key = data.replace("setting_toggle_", "")
    if feature_key not in TOGGLE_FEATURES:
        return

    current = await get_setting(feature_key) == "1"
    new_val = "0" if current else "1"

    async with await get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?,?,datetime('now'))",
            (feature_key, new_val)
        )
        await db.commit()

    status = "ON ✅" if new_val == "1" else "OFF ❌"
    label = TOGGLE_FEATURES[feature_key]
    await add_log(query.from_user.id, "toggle_feature", f"{label} -> {status}", "info")
    await query.answer(f"✅ {label} sekarang {status}", show_alert=True)

    # Refresh toggle menu
    context.args = []
    query.data = "setting_toggles"
    await toggle_feature(update, context)
