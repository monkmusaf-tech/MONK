import json
import math
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import ADMIN_IDS
from database.queries import get_admin_role, get_setting, get_player

RARITY_COLORS = {
    "common": "⬜", "uncommon": "🟩", "rare": "🟦",
    "epic": "🟪", "legendary": "🟨", "mythic": "🟥", "boss": "💀"
}

RARITY_NAMES = {
    "common": "Common", "uncommon": "Uncommon", "rare": "Rare",
    "epic": "Epic", "legendary": "Legendary", "mythic": "Mythic", "boss": "Boss"
}

def rarity_badge(rarity: str) -> str:
    return f"{RARITY_COLORS.get(rarity, '⬜')} {RARITY_NAMES.get(rarity, rarity.title())}"

def format_coins(amount: int) -> str:
    if amount >= 1_000_000: return f"{amount/1_000_000:.1f}M"
    elif amount >= 1_000: return f"{amount/1_000:.1f}K"
    return str(amount)

def format_number(n) -> str:
    if n is None: return "0"
    return f"{int(n):,}".replace(",", ".")

async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS: return True
    role = await get_admin_role(user_id)
    return role is not None

async def has_permission(user_id: int, permission: str) -> bool:
    if user_id in ADMIN_IDS: return True
    role = await get_admin_role(user_id)
    if not role: return False
    perms = json.loads(role.get('permissions', '[]'))
    return permission in perms or 'all' in perms

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🦌 Hunt", callback_data="menu_hunt"),
         InlineKeyboardButton("🏪 Market", callback_data="menu_market")],
        [InlineKeyboardButton("🏠 Rumah", callback_data="menu_home"),
         InlineKeyboardButton("🏛️ Museum", callback_data="menu_museum")],
        [InlineKeyboardButton("🔫 Senjata", callback_data="menu_weapons"),
         InlineKeyboardButton("🎒 Inventori", callback_data="menu_inventory")],
        [InlineKeyboardButton("👤 Profil", callback_data="menu_profile"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="menu_leaderboard")]
    ])

def back_to_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu")]])

async def send_with_photo(context, chat_id, photo_key, caption, reply_markup=None, parse_mode="HTML"):
    photo_file_id = await get_setting(photo_key)
    try:
        if photo_file_id:
            await context.bot.send_photo(chat_id=chat_id, photo=photo_file_id, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode=parse_mode)

def player_status_bar(value: float, max_val: float = 100, length: int = 10) -> str:
    val = max(0, min(value, max_val))
    filled = int((val / max_val) * length)
    empty = length - filled
    color = "🟩" if val > 60 else "🟨" if val > 30 else "🟥"
    return f"{'█' * filled}{'░' * empty} {color} {int(val)}/{int(max_val)}"

def get_survival_warning(player: dict) -> str:
    w = []
    if player['hunger'] < 20: w.append("⚠️ Sangat lapar!")
    if player['thirst'] < 20: w.append("⚠️ Sangat haus!")
    if player['stamina'] < 20: w.append("⚠️ Stamina kritis!")
    return "\n".join(w) if w else "✅ Kondisi prima!"

async def update_survival_stats(user_id: int):
    """Update stats dengan paksaan Naive Datetime agar tidak error subtract"""
    player = await get_player(user_id)
    if not player: return

    # PAKSA NAIVE (Tanpa Timezone)
    now = datetime.now()
    
    last_active_str = player.get('last_active')
    if not last_active_str or "datetime" in str(last_active_str):
        last_active = now
    else:
        try:
            # Bersihkan string dari format ISO/DB
            clean_ts = str(last_active_str).replace('T', ' ').split('.')[0].replace('Z', '')
            last_active = datetime.strptime(clean_ts, '%Y-%m-%d %H:%M:%S')
        except:
            last_active = now

    hours_passed = (now - last_active).total_seconds() / 3600
    if hours_passed <= 0.005: return # Abaikan jika kurang dari 18 detik

    # Hitung pengurangan (drain)
    new_hunger = max(0, player['hunger'] - (2 * hours_passed))
    new_thirst = max(0, player['thirst'] - (3 * hours_passed))
    new_rest = max(0, player.get('rest', 100) - (1 * hours_passed))
    
    # Regen stamina
    stamina_regen = 1 * hours_passed if new_rest > 50 else 0.5 * hours_passed
    new_stamina = min(100, player['stamina'] + stamina_regen)

    # Update manual via DB koneksi
    from database.db import get_db
    db = await get_db()
    await db.execute(
        "UPDATE players SET hunger=?, thirst=?, rest=?, stamina=?, last_active=? WHERE user_id=?",
        (round(new_hunger, 2), round(new_thirst, 2), round(new_rest, 2), round(new_stamina, 2), now.strftime('%Y-%m-%d %H:%M:%S'), user_id)
    )
    await db.commit()
