from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_animals, get_weapons, get_items, get_maps, get_foods, add_log
from database.db import get_db
from utils.helpers import is_admin, has_permission, format_number, rarity_badge
import json

# ── MAIN CONTENT MENU ──────────────────────────────────────────
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id):
        await query.answer("❌ Akses ditolak!", show_alert=True); return
    
    await query.edit_message_text(
        "🗂️ <b>Kelola Konten</b>\n\nPilih kategori:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🦌 Hewan", callback_data="content_animals")],
            [InlineKeyboardButton("🔫 Senjata", callback_data="content_weapons")],
            [InlineKeyboardButton("🎒 Item", callback_data="content_items")],
            [InlineKeyboardButton("🗺️ Map", callback_data="content_maps")],
            [InlineKeyboardButton("🏠 Rumah & Makanan", callback_data="content_homes")],
            [InlineKeyboardButton("🏛️ Museum", callback_data="content_museum")],
            [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
        ])
    )

# ── ANIMALS ────────────────────────────────────────────────────
async def manage_animals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    animals = await get_animals(active_only=False)
    page = context.user_data.get('animal_page', 0)
    per_page = 8
    total_pages = max(1, (len(animals) + per_page - 1) // per_page)
    page_animals = animals[page*per_page:(page+1)*per_page]
    
    text = f"🦌 <b>Kelola Hewan</b>\nTotal: {len(animals)} hewan\n\n"
    buttons = []
    
    for a in page_animals:
        status = "✅" if a['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {a['emoji']} {a['name']} [{a['rarity'].title()}]",
            callback_data=f"edit_animal_{a['id']}"
        )])
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("◀️", callback_data=f"animal_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages-1: nav.append(InlineKeyboardButton("▶️", callback_data=f"animal_page_{page+1}"))
    if nav: buttons.append(nav)
    
    buttons.append([InlineKeyboardButton("➕ Tambah Hewan Baru", callback_data="add_animal")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def edit_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    animal_id = query.data.replace("edit_animal_", "")
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM animals WHERE id=?", (animal_id,))
        a = await cur.fetchone()
    
    if not a:
        await query.answer("❌ Hewan tidak ditemukan!", show_alert=True); return
    
    text = (
        f"✏️ <b>Edit Hewan: {a['name']}</b>\n\n"
        f"ID: <code>{a['id']}</code>\n"
        f"Emoji: {a['emoji']}\n"
        f"Rarity: {rarity_badge(a['rarity'])}\n"
        f"Map: {a['map_id']}\n"
        f"Harga Daging: {format_number(a['meat_price'])}\n"
        f"Harga Kulit: {format_number(a['skin_price'])}\n"
        f"Reward Utama: {a['main_reward']} x{a['main_reward_amount']}\n"
        f"Spawn Time: {a['spawn_time']}\n"
        f"Sifat: {a['behavior']}\n"
        f"Min Weapon Grade: {a['min_weapon_grade']}\n"
        f"HP: {a['hp']}\n"
        f"EXP: {a['exp_reward']}\n"
        f"Status: {'✅ Aktif' if a['is_active'] else '❌ Nonaktif'}\n"
    )
    
    buttons = [
        [InlineKeyboardButton("📝 Edit Nama", callback_data=f"aedit_name_{a['id']}")],
        [InlineKeyboardButton("💰 Edit Harga Daging", callback_data=f"aedit_meat_{a['id']}"),
         InlineKeyboardButton("🧥 Edit Harga Kulit", callback_data=f"aedit_skin_{a['id']}")],
        [InlineKeyboardButton("📸 Upload Foto", callback_data=f"aedit_photo_{a['id']}")],
        [InlineKeyboardButton("🎯 Edit Rarity", callback_data=f"aedit_rarity_{a['id']}")],
        [InlineKeyboardButton("🗺️ Edit Map", callback_data=f"aedit_map_{a['id']}")],
        [InlineKeyboardButton("⚔️ Edit Behavior", callback_data=f"aedit_behavior_{a['id']}")],
        [InlineKeyboardButton(
            "❌ Nonaktifkan" if a['is_active'] else "✅ Aktifkan",
            callback_data=f"toggle_animal_{a['id']}"
        )],
        [InlineKeyboardButton("🗑️ Hapus Hewan", callback_data=f"del_animal_{a['id']}")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="content_animals")],
    ]
    
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def delete_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    animal_id = query.data.replace("del_animal_", "")
    
    if not animal_id.startswith("confirm_"):
        await query.edit_message_text(
            f"⚠️ <b>Konfirmasi Hapus</b>\n\nYakin hapus hewan <code>{animal_id}</code>?\nTindakan ini tidak bisa dibatalkan!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ya, Hapus!", callback_data=f"del_animal_confirm_{animal_id}")],
                [InlineKeyboardButton("❌ Batal", callback_data=f"edit_animal_{animal_id}")],
            ])
        )
        return
    
    real_id = animal_id.replace("confirm_", "")
    async with await get_db() as db:
        await db.execute("DELETE FROM animals WHERE id=?", (real_id,))
        await db.commit()
    
    await add_log(query.from_user.id, "delete_animal", f"Menghapus hewan {real_id}", "warning")
    await query.edit_message_text(
        f"✅ Hewan <code>{real_id}</code> berhasil dihapus!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Kembali", callback_data="content_animals")]])
    )

async def add_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    context.user_data['admin_action'] = 'add_animal'
    context.user_data['new_animal'] = {}
    
    await query.edit_message_text(
        "➕ <b>Tambah Hewan Baru</b>\n\n"
        "Kirim data hewan dengan format:\n\n"
        "<code>id|nama|emoji|rarity|map_id|meat_price|skin_price|reward_utama|spawn_time|behavior|min_grade|hp|exp</code>\n\n"
        "Contoh:\n"
        "<code>golden_deer|Rusa Emas|🦌|legendary|forest|5000|8000|Tanduk Emas|Night|flee|6|800|200</code>\n\n"
        "Rarity: common/uncommon/rare/epic/legendary/mythic/boss\n"
        "Behavior: flee/aggressive/neutral/boss",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="content_animals")]])
    )

async def handle_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads from admin"""
    user = update.effective_user
    if not await is_admin(user.id):
        return
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    action = context.user_data.get('upload_photo_for')
    
    if not action:
        await update.message.reply_text(
            "📸 Foto diterima!\n\nMau dipakai untuk apa?\n"
            "Set konteks dulu dari menu admin.",
        )
        return
    
    if action.startswith("animal_"):
        animal_id = action.replace("animal_", "")
        async with await get_db() as db:
            await db.execute("UPDATE animals SET photo_file_id=? WHERE id=?", (file_id, animal_id))
            await db.commit()
        await update.message.reply_text(f"✅ Foto hewan <code>{animal_id}</code> berhasil diupdate!", parse_mode="HTML")
    
    elif action.startswith("weapon_"):
        weapon_id = action.replace("weapon_", "")
        async with await get_db() as db:
            await db.execute("UPDATE weapons SET photo_file_id=? WHERE id=?", (file_id, weapon_id))
            await db.commit()
        await update.message.reply_text(f"✅ Foto senjata diupdate!", parse_mode="HTML")
    
    elif action.startswith("setting_"):
        key = action.replace("setting_", "")
        async with await get_db() as db:
            await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?,?)", (key, file_id))
            await db.commit()
        await update.message.reply_text(f"✅ Foto {key} berhasil diupdate!")
    
    context.user_data.pop('upload_photo_for', None)
    await add_log(user.id, "upload_photo", f"Upload foto untuk: {action}")

# ── WEAPONS ────────────────────────────────────────────────────
async def manage_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    weapons = await get_weapons(active_only=False)
    text = f"🔫 <b>Kelola Senjata</b>\nTotal: {len(weapons)}\n\n"
    buttons = []
    
    for w in weapons:
        status = "✅" if w['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {w['emoji']} {w['name']} G{w['grade']} | {format_number(w['price'])} koin",
            callback_data=f"edit_weapon_{w['id']}"
        )])
    
    buttons.append([InlineKeyboardButton("➕ Tambah Senjata", callback_data="add_weapon")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def add_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    context.user_data['admin_action'] = 'add_weapon'
    await query.edit_message_text(
        "➕ <b>Tambah Senjata Baru</b>\n\n"
        "Kirim data dengan format:\n"
        "<code>id|nama|emoji|grade|damage|accuracy|price|deskripsi</code>\n\n"
        "Contoh:\n"
        "<code>dragon_bow|Busur Naga|🏹|8|200|0.97|300000|Busur dari sisik naga</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="content_weapons")]])
    )

async def edit_weapon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    weapon_id = query.data.replace("edit_weapon_", "")
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM weapons WHERE id=?", (weapon_id,))
        w = await cur.fetchone()
    
    if not w: return
    
    text = (
        f"✏️ <b>Edit Senjata: {w['name']}</b>\n\n"
        f"Grade: {w['grade']} | Damage: {w['damage']} | Akurasi: {int(w['accuracy']*100)}%\n"
        f"Harga: {format_number(w['price'])} koin\n"
        f"Status: {'✅ Aktif' if w['is_active'] else '❌ Nonaktif'}"
    )
    
    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Edit Harga", callback_data=f"wedit_price_{w['id']}")],
            [InlineKeyboardButton("⚔️ Edit Damage", callback_data=f"wedit_damage_{w['id']}")],
            [InlineKeyboardButton("📸 Upload Foto", callback_data=f"wedit_photo_{w['id']}")],
            [InlineKeyboardButton(
                "❌ Nonaktifkan" if w['is_active'] else "✅ Aktifkan",
                callback_data=f"toggle_weapon_{w['id']}"
            )],
            [InlineKeyboardButton("◀️ Kembali", callback_data="content_weapons")],
        ])
    )

# ── ITEMS ──────────────────────────────────────────────────────
async def manage_items(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    items = await get_items(active_only=False)
    text = f"🎒 <b>Kelola Item</b>\nTotal: {len(items)}\n\n"
    buttons = []
    
    for item in items:
        status = "✅" if item['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {item['emoji']} {item['name']} | {format_number(item['price'])} koin",
            callback_data=f"edit_item_{item['id']}"
        )])
    
    buttons.append([InlineKeyboardButton("➕ Tambah Item", callback_data="add_item")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

# ── MAPS ───────────────────────────────────────────────────────
async def manage_maps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    maps = await get_maps(active_only=False)
    text = "🗺️ <b>Kelola Map</b>\n\nToggle untuk aktif/nonaktifkan map:\n\n"
    buttons = []
    
    for m in maps:
        status = "✅" if m['is_active'] else "❌"
        buttons.append([InlineKeyboardButton(
            f"{status} {m['emoji']} {m['name']} (Lv.{m['min_level']}+)",
            callback_data=f"toggle_map_{m['id']}"
        )])
    
    buttons.append([InlineKeyboardButton("➕ Tambah Map", callback_data="add_map")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def toggle_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    map_id = query.data.replace("toggle_map_", "")
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT is_active FROM maps WHERE id=?", (map_id,))
        row = await cur.fetchone()
        if row:
            new_status = 0 if row['is_active'] else 1
            await db.execute("UPDATE maps SET is_active=? WHERE id=?", (new_status, map_id))
            await db.commit()
    
    await add_log(query.from_user.id, "toggle_map", f"Toggle map {map_id}", "info")
    await manage_maps(update, context)

# ── HOMES ──────────────────────────────────────────────────────
async def manage_homes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM home_levels ORDER BY level")
        homes = await cur.fetchall()
    
    foods = await get_foods(active_only=False)
    
    text = "🏠 <b>Kelola Rumah & Makanan</b>\n\n"
    text += "<b>Level Rumah:</b>\n"
    buttons = []
    
    for h in homes:
        buttons.append([InlineKeyboardButton(
            f"Lv.{h['level']} {h['name']} - Upgrade: {format_number(h['upgrade_cost'])}",
            callback_data=f"edit_home_{h['level']}"
        )])
    
    text += f"\n<b>Makanan/Minuman:</b> {len(foods)} item\n"
    buttons.append([InlineKeyboardButton("🍖 Kelola Makanan", callback_data="manage_foods")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

# ── MUSEUM ─────────────────────────────────────────────────────
async def manage_museum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return
    
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM museum_slots ORDER BY required_rarity")
        slots = await cur.fetchall()
    
    text = f"🏛️ <b>Kelola Museum</b>\nTotal Slot: {len(slots)}\n\n"
    buttons = []
    
    for slot in slots:
        buttons.append([InlineKeyboardButton(
            f"🏆 {slot['name']} | Reward: {format_number(slot['trophy_reward'])}",
            callback_data=f"edit_museum_slot_{slot['id']}"
        )])
    
    buttons.append([InlineKeyboardButton("➕ Tambah Slot Trofi", callback_data="add_museum_slot")])
    buttons.append([InlineKeyboardButton("◀️ Konten", callback_data="admin_content")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
