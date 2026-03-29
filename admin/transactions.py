from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import (
    get_pending_topups, get_transactions, update_transaction,
    add_coins, add_log, get_player, get_topup_packages
)
from database.db import get_db
from utils.helpers import is_admin, format_number
import csv
import io
from datetime import datetime

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    pending = await get_pending_topups()
    text = (
        f"💳 <b>Transaksi & Top-Up</b>\n\n"
        f"⏳ Pending Verifikasi: <b>{len(pending)}</b>\n\n"
        f"Pilih aksi:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"✅ Verifikasi Top-Up ({len(pending)} pending)",
            callback_data="txn_verify"
        )],
        [InlineKeyboardButton("📋 Riwayat Transaksi", callback_data="txn_history")],
        [InlineKeyboardButton("📤 Export CSV", callback_data="txn_export")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def verify_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    pending = await get_pending_topups()

    if not pending:
        await query.edit_message_text(
            "✅ <b>Tidak Ada Pending Topup</b>\n\nSemua top-up sudah diverifikasi!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Transaksi", callback_data="admin_transactions")]])
        )
        return

    # Show first pending
    txn = pending[0]
    name = txn.get('username') or txn.get('full_name') or f"ID:{txn['user_id']}"

    text = (
        f"⏳ <b>Verifikasi Top-Up</b>\n"
        f"({len(pending)} pending)\n\n"
        f"👤 Player: {name} (ID: {txn['user_id']})\n"
        f"💰 Jumlah: Rp {format_number(txn['amount'])}\n"
        f"📝 Keterangan: {txn['description']}\n"
        f"📅 Waktu: {txn['created_at'][:16]}\n\n"
        f"ID Transaksi: #{txn['id']}"
    )

    buttons = []

    # Show proof if available
    if txn.get('proof_file_id'):
        text += "\n\n📸 Bukti transfer tersedia (foto di bawah)"

    buttons.append([
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_txn_{txn['id']}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_txn_{txn['id']}"),
    ])
    buttons.append([InlineKeyboardButton("⏭️ Skip", callback_data="txn_verify")])
    buttons.append([InlineKeyboardButton("◀️ Transaksi", callback_data="admin_transactions")])

    if txn.get('proof_file_id'):
        try:
            await query.message.reply_photo(
                photo=txn['proof_file_id'],
                caption=text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await query.message.delete()
            return
        except Exception:
            pass

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def approve_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    txn_id = int(query.data.replace("approve_txn_", ""))

    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM transactions WHERE id=?", (txn_id,))
        txn = await cur.fetchone()

    if not txn:
        await query.answer("❌ Transaksi tidak ditemukan!", show_alert=True); return

    if txn['status'] != 'pending':
        await query.answer("⚠️ Transaksi sudah diproses!", show_alert=True); return

    # Find the package to determine coin amount
    packages = await get_topup_packages()
    pkg = next((p for p in packages if p['price'] == txn['amount']), None)

    if pkg:
        coin_amount = int(pkg['coins'] * (1 + pkg['bonus_percent'] / 100))
    else:
        # Estimate: 1 IDR = 0.1 coin
        coin_amount = int(txn['amount'] * 0.1)

    await add_coins(txn['user_id'], coin_amount)
    await update_transaction(txn_id, 'approved', query.from_user.id)
    await add_log(query.from_user.id, "approve_topup", f"Approve topup #{txn_id} untuk user {txn['user_id']}", "info")

    # Notify player
    try:
        await context.bot.send_message(
            txn['user_id'],
            f"✅ <b>Top-Up Berhasil!</b>\n\n"
            f"💰 +{format_number(coin_amount)} koin telah ditambahkan ke akunmu!\n"
            f"ID Transaksi: #{txn_id}\n\n"
            f"Selamat berburu! 🦌",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await query.answer(f"✅ Top-up approved! +{format_number(coin_amount)} koin", show_alert=True)
    await verify_topup(update, context)

async def reject_topup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    txn_id = int(query.data.replace("reject_txn_", ""))

    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM transactions WHERE id=?", (txn_id,))
        txn = await cur.fetchone()

    if not txn: return

    await update_transaction(txn_id, 'rejected', query.from_user.id)
    await add_log(query.from_user.id, "reject_topup", f"Reject topup #{txn_id}", "warning")

    try:
        await context.bot.send_message(
            txn['user_id'],
            f"❌ <b>Top-Up Ditolak</b>\n\n"
            f"Top-up #{txn_id} sebesar Rp {format_number(txn['amount'])} tidak dapat diverifikasi.\n\n"
            f"Hubungi admin jika ada pertanyaan.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await query.answer("❌ Top-up rejected!", show_alert=True)
    await verify_topup(update, context)

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    txns = await get_transactions(limit=20)
    text = "📋 <b>Riwayat Transaksi (20 Terbaru)</b>\n\n"

    for txn in txns:
        status_emoji = {"approved": "✅", "rejected": "❌", "pending": "⏳"}.get(txn['status'], "❓")
        type_emoji = {"topup": "💎", "sell": "💰", "p2p": "🤝", "admin_give": "🎁"}.get(txn['type'], "💳")
        text += (
            f"{status_emoji} {type_emoji} #{txn['id']} | "
            f"User:{txn['user_id']} | "
            f"Rp {format_number(txn['amount'])} | "
            f"{txn['created_at'][:10]}\n"
        )

    await query.edit_message_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Export CSV", callback_data="txn_export")],
            [InlineKeyboardButton("◀️ Transaksi", callback_data="admin_transactions")],
        ])
    )

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("📤 Membuat file CSV...")
    if not await is_admin(query.from_user.id): return

    txns = await get_transactions(limit=1000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User ID', 'Type', 'Amount', 'Description', 'Status', 'Created At', 'Processed At'])

    for txn in txns:
        writer.writerow([
            txn['id'], txn['user_id'], txn['type'],
            txn['amount'], txn['description'], txn['status'],
            txn['created_at'], txn.get('processed_at', '')
        ])

    output.seek(0)
    csv_bytes = output.getvalue().encode('utf-8')

    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    await context.bot.send_document(
        chat_id=query.from_user.id,
        document=io.BytesIO(csv_bytes),
        filename=filename,
        caption=f"📤 Export {len(txns)} transaksi\n{datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    await query.answer("✅ File CSV dikirim!", show_alert=True)
