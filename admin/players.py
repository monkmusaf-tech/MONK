from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_all_players, get_player, add_coins, add_log, get_items
from database.db import get_db
from utils.helpers import is_admin, format_number

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    total_players = len(await get_all_players())
    await query.edit_message_text(
        f"👤 <b>Manajemen Player</b>\nTotal Player: {total_players}\n\nPilih aksi:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Cari Player", callback_data="player_search")],
            [InlineKeyboardButton("📋 Daftar Player Terbaru", callback_data="player_list")],
            [InlineKeyboardButton("📢 Broadcast Pesan", callback_data="player_broadcast")],
            [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
        ])
    )

async def search_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    context.user_data['admin_action'] = 'search_player'
    await query.edit_message_text(
        "🔍 <b>Cari Player</b>\n\nKetik username atau nama player:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
    )

async def show_player_detail(query, player_id: int):
    """Show player management options"""
    player = await get_player(player_id)
    if not player:
        await query.answer("❌ Player tidak ditemukan!", show_alert=True)
        return

    name = player['username'] or player['full_name'] or f"ID:{player_id}"
    ban_status = "🔴 BANNED" if player['is_banned'] else "🟢 Aktif"

    text = (
        f"👤 <b>Player: {name}</b>\n"
        f"ID: <code>{player_id}</code>\n\n"
        f"Status: {ban_status}\n"
        f"💰 Koin: {format_number(player['coins'])}\n"
        f"⭐ Level: {player['level']}\n"
        f"🎯 Hunt: {format_number(player['total_hunts'])}\n"
        f"☠️ Kill: {format_number(player['total_kills'])}\n"
        f"💵 Total Earn: {format_number(player['total_earnings'])}\n"
        f"📅 Joined: {player['joined_at'][:10] if player['joined_at'] else '-'}\n"
        f"🕐 Last Active: {player['last_active'][:16] if player['last_active'] else '-'}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Beri Koin", callback_data=f"player_give_coin_{player_id}"),
            InlineKeyboardButton("➖ Kurangi Koin", callback_data=f"player_take_coin_{player_id}"),
        ],
        [InlineKeyboardButton("🎁 Kirim Item", callback_data=f"player_item_{player_id}")],
        [InlineKeyboardButton("⭐ Set Level", callback_data=f"player_level_{player_id}")],
        [
            InlineKeyboardButton(
                "✅ Unban" if player['is_banned'] else "🚫 Ban",
                callback_data=f"player_ban_{player_id}"
            ),
            InlineKeyboardButton("🔇 Mute", callback_data=f"player_mute_{player_id}"),
        ],
        [InlineKeyboardButton("📋 Riwayat Transaksi", callback_data=f"player_txn_{player_id}")],
        [InlineKeyboardButton("◀️ Kembali", callback_data="admin_players")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def give_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    data = query.data
    if data.startswith("player_give_coin_"):
        player_id = int(data.replace("player_give_coin_", ""))
        context.user_data['admin_action'] = 'give_coins'
        context.user_data['target_player'] = player_id
        await query.edit_message_text(
            f"➕ <b>Beri Koin</b>\n\nPlayer ID: <code>{player_id}</code>\n\nKetik jumlah koin yang mau diberikan:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
        )
    elif data.startswith("player_take_coin_"):
        player_id = int(data.replace("player_take_coin_", ""))
        context.user_data['admin_action'] = 'take_coins'
        context.user_data['target_player'] = player_id
        await query.edit_message_text(
            f"➖ <b>Kurangi Koin</b>\n\nPlayer ID: <code>{player_id}</code>\n\nKetik jumlah koin yang mau dikurangi:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
        )
    elif data.startswith("player_coins_"):
        # Legacy pattern
        player_id = int(data.replace("player_coins_", ""))
        context.user_data['admin_action'] = 'give_coins'
        context.user_data['target_player'] = player_id
        await query.edit_message_text(
            f"➕ <b>Beri Koin ke Player {player_id}</b>\n\nKetik jumlah koin:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
        )

async def give_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    player_id = int(query.data.replace("player_item_", ""))
    items = await get_items()

    text = f"🎁 <b>Kirim Item ke Player {player_id}</b>\n\nPilih item:"
    buttons = []

    for item in items:
        buttons.append([InlineKeyboardButton(
            f"{item['emoji']} {item['name']}",
            callback_data=f"send_item_{player_id}_{item['id']}"
        )])

    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data=f"player_detail_{player_id}")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def set_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    player_id = int(query.data.replace("player_level_", ""))
    context.user_data['admin_action'] = 'set_level'
    context.user_data['target_player'] = player_id

    await query.edit_message_text(
        f"⭐ <b>Set Level Player {player_id}</b>\n\nKetik level baru (1-999):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
    )

async def ban_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    player_id = int(query.data.replace("player_ban_", ""))
    player = await get_player(player_id)

    if player['is_banned']:
        # Unban
        async with await get_db() as db:
            await db.execute("UPDATE players SET is_banned=0, ban_reason=NULL WHERE user_id=?", (player_id,))
            await db.commit()
        await add_log(query.from_user.id, "unban_player", f"Unban player {player_id}", "warning")
        await query.answer("✅ Player berhasil di-unban!", show_alert=True)
    else:
        context.user_data['admin_action'] = 'ban_player'
        context.user_data['target_player'] = player_id
        await query.edit_message_text(
            f"🚫 <b>Ban Player {player_id}</b>\n\nKetik alasan ban:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_players")]])
        )
        return

    await show_player_detail(query, player_id)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    context.user_data['admin_action'] = 'broadcast'
    await query.edit_message_text(
        "📢 <b>Broadcast Pesan</b>\n\n"
        "Pesan akan dikirim ke SEMUA player!\n\n"
        "Ketik pesan yang ingin dikirim:\n"
        "(Supports HTML formatting)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Broadcast Semua", callback_data="broadcast_all")],
            [InlineKeyboardButton("🟢 Broadcast Online", callback_data="broadcast_online")],
            [InlineKeyboardButton("❌ Batal", callback_data="admin_players")],
        ])
    )
