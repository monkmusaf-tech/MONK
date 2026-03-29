import json
import math
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import ADMIN_IDS
from database.queries import get_admin_role, get_setting, get_player

RARITY_COLORS = {
    "common": "⬜",
    "uncommon": "🟩",
    "rare": "🟦",
    "epic": "🟪",
    "legendary": "🟨",
    "mythic": "🟥",
    "boss": "💀"
}

RARITY_NAMES = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "epic": "Epic",
    "legendary": "Legendary",
    "mythic": "Mythic",
    "boss": "Boss"
}

def rarity_badge(rarity: str) -> str:
    return f"{RARITY_COLORS.get(rarity, '⬜')} {RARITY_NAMES.get(rarity, rarity.title())}"

def format_coins(amount: int) -> str:
    if amount >= 1_000_000:
        return f"{amount/1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"{amount/1_000:.1f}K"
    return str(amount)

def format_number(n) -> str:
    if n is None:
        return "0"
    return f"{int(n):,}".replace(",", ".")

async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    role = await get_admin_role(user_id)
    return role is not None

async def has_permission(user_id: int, permission: str) -> bool:
    if user_id in ADMIN_IDS:
        return True
    role = await get_admin_role(user_id)
    if not role:
        return False
    perms = json.loads(role.get('permissions', '[]'))
    return permission in perms or 'all' in perms

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🦌 Hunt", callback_data="menu_hunt"),
            InlineKeyboardButton("🏪 Market", callback_data="menu_market"),
        ],
        [
            InlineKeyboardButton("🏠 Rumah", callback_data="menu_home"),
            InlineKeyboardButton("🏛️ Museum", callback_data="menu_museum"),
        ],
        [
            InlineKeyboardButton("🔫 Senjata", callback_data="menu_weapons"),
            InlineKeyboardButton("🎒 Inventori", callback_data="menu_inventory"),
        ],
        [
            InlineKeyboardButton("👤 Profil", callback_data="menu_profile"),
            InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard"),
        ],
    ])

def back_to_main():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")
    ]])

def back_button(callback: str, label: str = "◀️ Kembali"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=callback)]])

async def send_with_photo(context, chat_id, photo_key, caption, reply_markup=None, parse_mode="HTML"):
    photo_file_id = await get_setting(photo_key)
    try:
        if photo_file_id:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode=parse_mode)

async def edit_with_photo(query, photo_key, caption, reply_markup=None, parse_mode="HTML"):
    photo_file_id = await get_setting(photo_key)
    try:
        if photo_file_id and hasattr(query.message, 'photo') and query.message.photo:
            await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await query.edit_message_text(text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            pass

def paginate(items: list, page: int, per_page: int = 8):
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    end = start + per_page
    return items[start:end], page, total_pages

def pagination_buttons(current_page: int, total_pages: int, prefix: str):
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}_page_{current_page-1}"))
    buttons.append(InlineKeyboardButton(f"{current_page+1}/{total_pages}", callback_data="noop"))
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}_page_{current_page+1}"))
    return buttons

def player_status_bar(value: float, max_val: float = 100, length: int = 10) -> str:
    value = max(0, min(value, max_val))
    filled = int((value / max_val) * length)
    empty = length - filled
    color = "🟩" if value > 60 else "🟨" if value > 30 else "🟥"
    return f"{'█' * filled}{'░' * empty} {color} {int(value)}/{int(max_val)}"

def get_survival_warning(player: dict) -> str:
    warnings = []
    if player['hunger'] < 20: warnings.append("⚠️ Sangat lapar! Segera makan!")
    elif player['hunger'] < 40: warnings.append("🍖 Mulai lapar")
    if player['thirst'] < 20: warnings.append("⚠️ Sangat haus! Segera minum!")
    elif player['thirst'] < 40: warnings.append("💧 Mulai haus")
    if player['stamina'] < 20: warnings.append("⚠️ Stamina kritis! Istirahat!")
    if player['rest'] < 20: warnings.append("⚠️ Sangat lelah!")
    return "\n".join(warnings) if warnings else "✅ Kondisi prima!"

async def update_survival_stats(user_id: int, hours_passed: float = None):
    """Update survival stats with fixed timezone handling"""
    player = await get_player(user_id)
    if not player:
        return
    
    now = datetime.now(timezone.utc)
    
    if hours_passed is None:
        last_active_str = player.get('last_active')
        if not last_active_str or last_active_str == "datetime('now')":
            last_active = now
        else:
            try:
                # Bersihkan string dari SQLite format jika perlu
                clean_ts = last_active_str.replace(' ', 'T').split('.')[0]
                if 'T' not in clean_ts: clean_ts += "T00:00:00"
                last_active = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
            except Exception:
                last_active = now
        
        hours_passed = (now - last_active).total_seconds() / 3600
    
    if hours_passed <= 0:
        return

    # Logika Drain
    new_hunger = max(0, player['hunger'] - (2 * hours_passed))
    new_thirst = max(0, player['thirst'] - (3 * hours_passed))
    new_rest = max(0, player['rest'] - (1 * hours_passed))
    
    # Regenerasi Stamina
    stamina_regen = 1 * hours_passed if new_rest > 50 else 0.5 * hours_passed
    new_stamina = min(100, player['stamina'] + stamina_regen)
    
    # Update langsung ke DB
    from database.db import get_db
    db = await get_db()
    await db.execute(
        """UPDATE players SET 
           hunger=?, thirst=?, rest=?, stamina=?, 
           last_active=CURRENT_TIMESTAMP 
           WHERE user_id=?""",
        (round(new_hunger, 2), round(new_thirst, 2), round(new_rest, 2), round(new_stamina, 2), user_id)
    )
    await db.commit()
