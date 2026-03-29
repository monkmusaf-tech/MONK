from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_active_bosses, spawn_boss, get_animals, add_log
from database.db import get_db
from utils.helpers import is_admin, format_number
from config.settings import CHANNEL_ID
import json

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    active_bosses = await get_active_bosses()
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM events WHERE is_active=1 ORDER BY start_at DESC LIMIT 5")
        active_events = await cur.fetchall()

    text = (
        f"🎉 <b>Event & Boss</b>\n\n"
        f"👹 Boss Aktif: {len(active_bosses)}\n"
        f"🎉 Event Aktif: {len(active_events)}\n\n"
        f"Pilih aksi:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👹 Spawn Boss Manual", callback_data="event_boss")],
        [InlineKeyboardButton("👁️ Boss Aktif", callback_data="event_active")],
        [InlineKeyboardButton("🎉 Buat Event", callback_data="event_create")],
        [InlineKeyboardButton("📋 Daftar Event", callback_data="event_list")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def spawn_boss_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    # Get boss-type animals
    animals = await get_animals()
    boss_animals = [a for a in animals if a['rarity'] in ['boss', 'mythic', 'legendary']]

    text = "👹 <b>Spawn Boss Manual</b>\n\nPilih hewan boss:"
    buttons = []

    for a in boss_animals:
        buttons.append([InlineKeyboardButton(
            f"{a['emoji']} {a['name']} [{a['rarity'].title()}]",
            callback_data=f"spawn_select_{a['id']}"
        )])

    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_events")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def active_bosses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    bosses = await get_active_bosses()

    if not bosses:
        await query.edit_message_text(
            "👹 <b>Boss Aktif</b>\n\nTidak ada boss aktif saat ini.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👹 Spawn Boss", callback_data="event_boss")],
                [InlineKeyboardButton("◀️ Kembali", callback_data="admin_events")],
            ])
        )
        return

    text = f"👹 <b>Boss Aktif ({len(bosses)})</b>\n\n"
    buttons = []

    for boss in bosses:
        hp_pct = int((boss['hp_current'] / boss['hp_max']) * 100)
        text += (
            f"• {boss['animal_name']}\n"
            f"  HP: {format_number(boss['hp_current'])}/{format_number(boss['hp_max'])} ({hp_pct}%)\n"
            f"  Map: {boss['map_id']} | Reward: {format_number(boss['reward_coins'])} koin\n\n"
        )
        buttons.append([InlineKeyboardButton(
            f"❌ Kill {boss['animal_name']}",
            callback_data=f"kill_boss_{boss['id']}"
        )])

    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_events")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def create_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    context.user_data['admin_action'] = 'create_event'
    await query.edit_message_text(
        "🎉 <b>Buat Event Baru</b>\n\n"
        "Kirim data event dengan format:\n"
        "<code>nama|tipe|deskripsi|multiplier|durasi_jam</code>\n\n"
        "Tipe: double_exp / double_coin / spawn_rate / all\n\n"
        "Contoh:\n"
        "<code>Weekend Hunt|double_exp|2x EXP selama weekend!|2.0|48</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_events")]])
    )

async def do_spawn_boss(context, animal_id: str, map_id: str, hp: int, reward: int, spawned_by: int):
    """Actually spawn the boss and notify channel"""
    from database.queries import get_animal
    animal = await get_animal(animal_id)
    if not animal:
        return None

    boss_id = await spawn_boss(
        animal_id, animal['name'], map_id, hp, reward,
        json.dumps({"special_item": 1}), spawned_by
    )

    # Notify channel if set
    if CHANNEL_ID:
        try:
            msg = (
                f"⚠️ <b>BOSS MUNCUL!</b>\n\n"
                f"👹 {animal['emoji']} <b>{animal['name']}</b>\n"
                f"📍 Map: {map_id}\n"
                f"❤️ HP: {format_number(hp)}\n"
                f"💰 Reward: {format_number(reward)} koin\n\n"
                f"Segera berburu dan kalahkan boss ini!"
            )
            await context.bot.send_message(CHANNEL_ID, msg, parse_mode="HTML")
        except Exception as e:
            print(f"Failed to notify channel: {e}")

    await add_log(spawned_by, "spawn_boss", f"Spawn boss {animal['name']} di {map_id}", "warning")
    return boss_id
