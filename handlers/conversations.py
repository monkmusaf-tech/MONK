import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from database.queries import (
    get_player, create_player, get_animals, search_animals,
    add_coins, add_inventory, add_log, get_topup_packages,
    create_transaction, get_items
)
from database.db import get_db
from utils.helpers import format_number, rarity_badge, is_admin, RARITY_COLORS

# ── CONVERSATION STATES ────────────────────────────────────────
WAITING_INPUT = 1

# ── UNIVERSAL MESSAGE HANDLER ──────────────────────────────────
async def universal_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Central handler for all text input based on user_data state"""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()
    action = context.user_data.get('admin_action') or context.user_data.get('waiting_for')

    if not action:
        return

    # ── PLAYER ACTIONS ──
    if action == 'search_animal':
        await _handle_search_animal(update, context, text)

    elif action == 'p2p_create':
        await _handle_p2p_create(update, context, text)

    # ── ADMIN ACTIONS ──
    elif action == 'search_player' and await is_admin(user.id):
        await _handle_search_player(update, context, text)

    elif action == 'give_coins' and await is_admin(user.id):
        await _handle_give_coins(update, context, text)

    elif action == 'take_coins' and await is_admin(user.id):
        await _handle_take_coins(update, context, text)

    elif action == 'set_level' and await is_admin(user.id):
        await _handle_set_level(update, context, text)

    elif action == 'ban_player' and await is_admin(user.id):
        await _handle_ban_player(update, context, text)

    elif action == 'broadcast' and await is_admin(user.id):
        await _handle_broadcast(update, context, text)

    elif action == 'add_animal' and await is_admin(user.id):
        await _handle_add_animal(update, context, text)

    elif action == 'add_weapon' and await is_admin(user.id):
        await _handle_add_weapon(update, context, text)

    elif action == 'set_payment_info' and await is_admin(user.id):
        await _handle_set_payment(update, context, text)

    elif action == 'create_event' and await is_admin(user.id):
        await _handle_create_event(update, context, text)

    elif action == 'add_admin' and await is_admin(user.id):
        await _handle_add_admin(update, context, text)

    elif action == 'edit_param' and await is_admin(user.id):
        await _handle_edit_param(update, context, text)

    elif action == 'edit_animal_field' and await is_admin(user.id):
        await _handle_edit_animal_field(update, context, text)

    elif action == 'edit_price' and await is_admin(user.id):
        await _handle_edit_price(update, context, text)

    elif action == 'topup_submit':
        await _handle_topup_submit(update, context, text)

    elif action == 'set_welcome' and await is_admin(user.id):
        await _handle_set_welcome(update, context, text)

    # Clear action after handling
    context.user_data.pop('admin_action', None)
    context.user_data.pop('waiting_for', None)

# ── PLAYER HANDLERS ───────────────────────────────────────────
async def _handle_search_animal(update, context, keyword):
    results = await search_animals(keyword)

    if not results:
        await update.message.reply_text(
            f"🔍 Tidak ada hewan dengan nama '<b>{keyword}</b>'",
            parse_mode="HTML"
        )
        return

    text = f"🔍 <b>Hasil Pencarian: '{keyword}'</b>\n\n"
    buttons = []

    for a in results[:10]:
        badge = RARITY_COLORS.get(a['rarity'], '⬜')
        text += f"{badge} {a['emoji']} {a['name']} — {rarity_badge(a['rarity'])}\n"
        buttons.append([InlineKeyboardButton(
            f"{badge} {a['name']} ({a['map_id']})",
            callback_data=f"hunt_animal_{a['id']}"
        )])

    buttons.append([InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def _handle_p2p_create(update, context, text_input):
    user = update.effective_user
    player = await get_player(user.id)

    parts = [p.strip() for p in text_input.split("|")]
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ Format salah!\nGunakan: <code>nama_item | jumlah | harga_per_unit</code>",
            parse_mode="HTML"
        )
        return

    item_name = parts[0]
    try:
        quantity = int(parts[1])
        price = int(parts[2])
    except ValueError:
        await update.message.reply_text("❌ Jumlah dan harga harus angka!")
        return

    if quantity <= 0 or price <= 0:
        await update.message.reply_text("❌ Jumlah dan harga harus lebih dari 0!")
        return

    # Check inventory
    from database.queries import get_inventory
    inv = await get_inventory(user.id)
    item = next((i for i in inv if item_name.lower() in i['item_name'].lower()), None)

    if not item or item['quantity'] < quantity:
        await update.message.reply_text(f"❌ Item '{item_name}' tidak cukup di inventori!")
        return

    # Create listing
    from database.queries import create_p2p_listing
    await create_p2p_listing(
        user.id,
        user.username or user.first_name,
        item['item_type'],
        item['item_id'],
        item['item_name'],
        quantity,
        price
    )

    from database.queries import remove_inventory
    await remove_inventory(user.id, item['item_type'], item['item_id'], quantity)

    await update.message.reply_text(
        f"✅ <b>Listing Dibuat!</b>\n\n"
        f"📦 {item['item_name']} x{quantity}\n"
        f"💰 Harga: {format_number(price)}/unit\n"
        f"💎 Total: {format_number(price * quantity)} koin\n\n"
        f"Listing aktif dan bisa dibeli player lain!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤝 Lihat P2P", callback_data="p2p_list")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")],
        ])
    )

# ── ADMIN HANDLERS ────────────────────────────────────────────
async def _handle_search_player(update, context, keyword):
    from database.queries import get_all_players
    players = await get_all_players(search=keyword)

    if not players:
        await update.message.reply_text(f"❌ Tidak ada player dengan nama/username '{keyword}'")
        return

    text = f"🔍 <b>Hasil Pencarian: '{keyword}'</b>\n\n"
    buttons = []

    for p in players[:10]:
        name = p['username'] or p['full_name'] or f"ID:{p['user_id']}"
        status = "🔴" if p['is_banned'] else "🟢"
        text += f"{status} {name} | Lv.{p['level']} | {format_number(p['coins'])} koin\n"
        buttons.append([InlineKeyboardButton(
            f"{status} {name}",
            callback_data=f"player_detail_{p['user_id']}"
        )])

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def _handle_give_coins(update, context, amount_str):
    target_id = context.user_data.get('target_player')
    if not target_id:
        await update.message.reply_text("❌ Target player tidak ditemukan!")
        return

    try:
        amount = int(amount_str.replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka!")
        return

    await add_coins(target_id, amount)
    await add_log(update.effective_user.id, "give_coins", f"Beri {format_number(amount)} koin ke {target_id}", "info")

    try:
        await update.get_bot().send_message(
            target_id,
            f"🎁 <b>Admin mengirim koin!</b>\n\n💰 +{format_number(amount)} koin ditambahkan ke akunmu!",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await update.message.reply_text(
        f"✅ Berhasil mengirim <b>{format_number(amount)} koin</b> ke player {target_id}!",
        parse_mode="HTML"
    )

async def _handle_take_coins(update, context, amount_str):
    target_id = context.user_data.get('target_player')
    if not target_id: return

    try:
        amount = int(amount_str.replace(".", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka!"); return

    await add_coins(target_id, -amount)
    await add_log(update.effective_user.id, "take_coins", f"Kurangi {format_number(amount)} koin dari {target_id}", "warning")
    await update.message.reply_text(f"✅ Berhasil mengurangi {format_number(amount)} koin dari player {target_id}!")

async def _handle_set_level(update, context, level_str):
    target_id = context.user_data.get('target_player')
    if not target_id: return

    try:
        level = int(level_str)
        assert 1 <= level <= 999
    except (ValueError, AssertionError):
        await update.message.reply_text("❌ Level harus angka 1-999!"); return

    async with await get_db() as db:
        await db.execute("UPDATE players SET level=?, exp=0 WHERE user_id=?", (level, target_id))
        await db.commit()

    await add_log(update.effective_user.id, "set_level", f"Set level {target_id} -> {level}", "info")
    await update.message.reply_text(f"✅ Level player {target_id} berhasil diset ke {level}!")

async def _handle_ban_player(update, context, reason):
    target_id = context.user_data.get('target_player')
    if not target_id: return

    async with await get_db() as db:
        await db.execute(
            "UPDATE players SET is_banned=1, ban_reason=? WHERE user_id=?",
            (reason, target_id)
        )
        await db.commit()

    await add_log(update.effective_user.id, "ban_player", f"Ban player {target_id}: {reason}", "critical")

    try:
        await update.get_bot().send_message(
            target_id,
            f"🚫 <b>Akun Dibanned</b>\n\nAkunmu telah dilarang bermain.\nAlasan: {reason}\n\nHubungi admin jika ada pertanyaan.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await update.message.reply_text(f"✅ Player {target_id} berhasil dibanned!\nAlasan: {reason}")

async def _handle_broadcast(update, context, message):
    from database.queries import get_all_players
    players = await get_all_players()

    sent = 0
    failed = 0
    total = len(players)

    await update.message.reply_text(f"📢 Mengirim broadcast ke {total} player...")

    bot = update.get_bot()
    for player in players:
        try:
            await bot.send_message(
                player['user_id'],
                f"📢 <b>Pesan dari Admin</b>\n\n{message}",
                parse_mode="HTML"
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ <b>Broadcast Selesai!</b>\n\n"
        f"✅ Terkirim: {sent}\n"
        f"❌ Gagal: {failed}\n"
        f"📊 Total: {total}"
    )
    await add_log(update.effective_user.id, "broadcast", f"Broadcast ke {sent}/{total} player", "info")

async def _handle_add_animal(update, context, data_str):
    parts = [p.strip() for p in data_str.split("|")]
    if len(parts) < 13:
        await update.message.reply_text(
            "❌ Format kurang lengkap! Butuh 13 field.\n"
            "Format: <code>id|nama|emoji|rarity|map_id|meat_price|skin_price|reward_utama|spawn_time|behavior|min_grade|hp|exp</code>",
            parse_mode="HTML"
        )
        return

    try:
        animal_data = (
            parts[0], parts[1], parts[2], parts[3], parts[4],
            int(parts[5]), int(parts[6]), parts[7],
            1,  # main_reward_amount default
            parts[8], parts[9], int(parts[10]), int(parts[11]), int(parts[12]),
            None, None, 1
        )

        async with await get_db() as db:
            await db.execute(
                """INSERT INTO animals 
                (id, name, emoji, rarity, map_id, meat_price, skin_price, main_reward,
                main_reward_amount, spawn_time, behavior, min_weapon_grade, hp, exp_reward,
                photo_file_id, description, is_active) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                animal_data
            )
            await db.commit()

        await add_log(update.effective_user.id, "add_animal", f"Tambah hewan {parts[1]}", "info")
        await update.message.reply_text(
            f"✅ <b>Hewan Ditambahkan!</b>\n\n"
            f"{parts[2]} <b>{parts[1]}</b>\n"
            f"Rarity: {parts[3]} | Map: {parts[4]}\n"
            f"Daging: {format_number(int(parts[5]))} | Kulit: {format_number(int(parts[6]))}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal menambahkan hewan!\nError: {str(e)}")

async def _handle_add_weapon(update, context, data_str):
    parts = [p.strip() for p in data_str.split("|")]
    if len(parts) < 7:
        await update.message.reply_text("❌ Format kurang! Butuh 7 field."); return

    try:
        async with await get_db() as db:
            await db.execute(
                "INSERT INTO weapons (id, name, emoji, grade, damage, accuracy, price, description, is_active) VALUES (?,?,?,?,?,?,?,?,1)",
                (parts[0], parts[1], parts[2], int(parts[3]), int(parts[4]), float(parts[5]), int(parts[6]), parts[7] if len(parts) > 7 else "")
            )
            await db.commit()
        await update.message.reply_text(f"✅ Senjata '{parts[1]}' berhasil ditambahkan!")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def _handle_set_payment(update, context, text):
    async with await get_db() as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('payment_info', ?)", (text,))
        await db.commit()
    await update.message.reply_text("✅ Info pembayaran berhasil diupdate!")

async def _handle_create_event(update, context, data_str):
    parts = [p.strip() for p in data_str.split("|")]
    if len(parts) < 5:
        await update.message.reply_text("❌ Format kurang!"); return

    try:
        from datetime import datetime, timedelta
        duration_hours = int(parts[4])
        end_at = (datetime.now() + timedelta(hours=duration_hours)).isoformat()

        async with await get_db() as db:
            await db.execute(
                """INSERT INTO events (name, type, description, multiplier, start_at, end_at, is_active, created_by)
                VALUES (?,?,?,?,datetime('now'),?,1,?)""",
                (parts[0], parts[1], parts[2], float(parts[3]), end_at, update.effective_user.id)
            )
            await db.commit()

        # Auto-set double exp/coin if applicable
        if parts[1] == 'double_exp':
            async with await get_db() as db:
                await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('double_exp', '1')", ())
                await db.commit()
        elif parts[1] == 'double_coin':
            async with await get_db() as db:
                await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('double_coin', '1')", ())
                await db.commit()

        await update.message.reply_text(
            f"✅ <b>Event Dibuat!</b>\n\n"
            f"🎉 {parts[0]}\n"
            f"Tipe: {parts[1]} | Multiplier: {parts[3]}x\n"
            f"Durasi: {duration_hours} jam",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def _handle_add_admin(update, context, data_str):
    parts = [p.strip() for p in data_str.split("|")]
    if len(parts) < 2:
        await update.message.reply_text("❌ Format: user_id|role"); return

    try:
        from admin.roles import ROLE_PERMISSIONS
        admin_id = int(parts[0])
        role = parts[1]
        permissions = json.dumps(ROLE_PERMISSIONS.get(role, []))

        async with await get_db() as db:
            await db.execute(
                "INSERT OR REPLACE INTO admin_roles (user_id, role, permissions, added_by) VALUES (?,?,?,?)",
                (admin_id, role, permissions, update.effective_user.id)
            )
            await db.commit()

        await add_log(update.effective_user.id, "add_admin", f"Tambah admin {admin_id} role {role}", "warning")
        await update.message.reply_text(f"✅ User {admin_id} berhasil ditambahkan sebagai {role}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def _handle_edit_param(update, context, value_str):
    param_key = context.user_data.get('edit_param_key')
    if not param_key: return

    async with await get_db() as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?,?)", (param_key, value_str))
        await db.commit()

    await update.message.reply_text(f"✅ Parameter '{param_key}' diset ke '{value_str}'!")

async def _handle_edit_animal_field(update, context, value_str):
    animal_id = context.user_data.get('edit_animal_id')
    field = context.user_data.get('edit_animal_field')
    if not animal_id or not field: return

    try:
        async with await get_db() as db:
            if field in ['meat_price', 'skin_price', 'hp', 'exp_reward', 'min_weapon_grade', 'main_reward_amount']:
                await db.execute(f"UPDATE animals SET {field}=? WHERE id=?", (int(value_str), animal_id))
            else:
                await db.execute(f"UPDATE animals SET {field}=? WHERE id=?", (value_str, animal_id))
            await db.commit()
        await update.message.reply_text(f"✅ Field '{field}' hewan '{animal_id}' berhasil diupdate!")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def _handle_edit_price(update, context, value_str):
    animal_id = context.user_data.get('edit_price_animal')
    price_type = context.user_data.get('edit_price_type')  # 'meat' or 'skin'
    if not animal_id or not price_type: return

    try:
        field = 'meat_price' if price_type == 'meat' else 'skin_price'
        price = int(value_str.replace(".", "").replace(",", ""))
        async with await get_db() as db:
            await db.execute(f"UPDATE animals SET {field}=? WHERE id=?", (price, animal_id))
            await db.commit()
        await update.message.reply_text(f"✅ Harga {price_type} hewan '{animal_id}' diset ke {format_number(price)}!")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def _handle_topup_submit(update, context, pkg_id):
    """Handle topup submission with proof"""
    pass  # Handled by photo handler

async def _handle_set_welcome(update, context, text):
    async with await get_db() as db:
        await db.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('welcome_message', ?)", (text,))
        await db.commit()
    await update.message.reply_text("✅ Welcome message berhasil diupdate!")

# ── CONVERSATION HANDLER SETUP ────────────────────────────────
# All conversations use the same universal handler
search_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^search_animal$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

p2p_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^p2p_create$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

broadcast_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^player_broadcast$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

add_animal_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^add_animal$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

add_weapon_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^add_weapon$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

set_price_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^eco_prices$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

player_action_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^player_search$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

event_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^event_create$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

boss_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^event_boss$")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

topup_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(lambda u, c: None, pattern="^topup_select_")],
    states={WAITING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler)]},
    fallbacks=[],
    per_message=False,
)

# Register the universal text handler directly (simpler approach)
universal_message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    universal_text_handler
)
