import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import get_all_admins, get_admin_role, add_log
from database.db import get_db
from config.settings import ADMIN_IDS
from utils.helpers import is_admin, format_number

ROLE_TYPES = {
    "super_admin": "👑 Super Admin",
    "content": "🗂️ Admin Konten",
    "finance": "💰 Admin Keuangan",
    "moderator": "🛡️ Moderator",
    "cs": "🎧 Customer Service",
}

ROLE_PERMISSIONS = {
    "super_admin": ["all"],
    "content": ["content_animals", "content_weapons", "content_items", "content_maps"],
    "finance": ["transactions", "economy", "topup"],
    "moderator": ["players", "ban", "broadcast", "logs"],
    "cs": ["players_view", "broadcast", "transactions_view"],
}

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    admins = await get_all_admins()
    text = (
        f"🛡️ <b>Admin & Role</b>\n\n"
        f"👑 Super Admin (dari env): {len(ADMIN_IDS)}\n"
        f"🛡️ Sub-Admin DB: {len(admins)}\n\n"
        f"Sub-Admin Terdaftar:\n"
    )

    for admin in admins:
        role_label = ROLE_TYPES.get(admin['role'], admin['role'])
        text += f"• {admin.get('username', f'ID:{admin[\"user_id\"]}')} — {role_label}\n"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tambah Sub-Admin", callback_data="role_add")],
        [InlineKeyboardButton("✏️ Edit Role", callback_data="role_list_edit")],
        [InlineKeyboardButton("🗑️ Hapus Sub-Admin", callback_data="role_list_remove")],
        [InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_dashboard")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    context.user_data['admin_action'] = 'add_admin'
    await query.edit_message_text(
        "➕ <b>Tambah Sub-Admin</b>\n\n"
        "Kirim data dengan format:\n"
        "<code>user_id|role</code>\n\n"
        "Role tersedia:\n"
        "• super_admin - Semua akses\n"
        "• content - Kelola konten\n"
        "• finance - Keuangan & topup\n"
        "• moderator - Kelola player\n"
        "• cs - Customer service\n\n"
        "Contoh:\n"
        "<code>123456789|moderator</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Batal", callback_data="admin_roles")]])
    )

async def edit_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    if query.data == "role_list_edit":
        admins = await get_all_admins()
        if not admins:
            await query.answer("Tidak ada sub-admin!", show_alert=True); return

        text = "✏️ <b>Edit Role Sub-Admin</b>\n\nPilih admin:"
        buttons = []
        for admin in admins:
            buttons.append([InlineKeyboardButton(
                f"{admin.get('username', f'ID:{admin[\"user_id\"]}')} — {admin['role']}",
                callback_data=f"role_edit_{admin['user_id']}"
            )])
        buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_roles")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    admin_id = int(query.data.replace("role_edit_", ""))
    role_data = await get_admin_role(admin_id)

    text = f"✏️ Edit Role Admin ID: {admin_id}\nRole saat ini: {role_data['role'] if role_data else '-'}\n\nPilih role baru:"
    buttons = []

    for role_key, role_label in ROLE_TYPES.items():
        buttons.append([InlineKeyboardButton(
            role_label,
            callback_data=f"set_role_{admin_id}_{role_key}"
        )])

    buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_roles")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    if query.data == "role_list_remove":
        admins = await get_all_admins()
        if not admins:
            await query.answer("Tidak ada sub-admin!", show_alert=True); return

        text = "🗑️ <b>Hapus Sub-Admin</b>\n\nPilih admin yang mau dihapus:"
        buttons = []
        for admin in admins:
            buttons.append([InlineKeyboardButton(
                f"🗑️ {admin.get('username', f'ID:{admin[\"user_id\"]}')}",
                callback_data=f"role_remove_{admin['user_id']}"
            )])
        buttons.append([InlineKeyboardButton("◀️ Kembali", callback_data="admin_roles")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    admin_id = int(query.data.replace("role_remove_", ""))
    async with await get_db() as db:
        await db.execute("DELETE FROM admin_roles WHERE user_id=?", (admin_id,))
        await db.commit()

    await add_log(query.from_user.id, "remove_admin", f"Hapus sub-admin {admin_id}", "warning")
    await query.answer(f"✅ Sub-admin {admin_id} dihapus!", show_alert=True)
    await menu(update, context)

async def set_role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle set_role_{admin_id}_{role} callback"""
    query = update.callback_query
    await query.answer()
    if not await is_admin(query.from_user.id): return

    parts = query.data.replace("set_role_", "").split("_", 1)
    if len(parts) < 2: return

    admin_id = int(parts[0])
    new_role = parts[1]
    permissions = json.dumps(ROLE_PERMISSIONS.get(new_role, []))

    async with await get_db() as db:
        await db.execute(
            "UPDATE admin_roles SET role=?, permissions=? WHERE user_id=?",
            (new_role, permissions, admin_id)
        )
        await db.commit()

    role_label = ROLE_TYPES.get(new_role, new_role)
    await add_log(query.from_user.id, "edit_role", f"Set role {admin_id} -> {new_role}", "info")
    await query.answer(f"✅ Role diubah ke {role_label}!", show_alert=True)
    await menu(update, context)
