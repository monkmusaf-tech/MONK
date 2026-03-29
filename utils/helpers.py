from datetime import datetime, timezone
import math
from database.queries import get_player, update_player_stats

# Fungsi pemformat angka (agar 1000 jadi 1.000)
def format_number(n):
    return "{:,}".format(n).replace(",", ".")

def rarity_badge(rarity):
    badges = {
        "common": "⚪ Common",
        "uncommon": "🟢 Uncommon",
        "rare": "🔵 Rare",
        "epic": "🟣 Epic",
        "legendary": "🟡 Legendary",
        "mythic": "🔴 Mythic"
    }
    return badges.get(rarity.lower(), "⚪ Common")

async def update_survival_stats(user_id):
    """
    Update hunger, thirst, dan stamina berdasarkan waktu yang berlalu.
    Memperbaiki error: can't subtract offset-naive and offset-aware datetimes
    """
    player = await get_player(user_id)
    if not player:
        return
    
    # Ambil waktu sekarang (Naive - tanpa timezone agar cocok dengan SQLite)
    now = datetime.now()
    
    # Ambil last_active dari DB
    last_active_str = player.get('last_active')
    
    if not last_active_str:
        # Jika belum ada data, set ke sekarang dan keluar
        await update_player_stats(user_id, last_active=now.strftime('%Y-%m-%d %H:%M:%S'))
        return

    try:
        # Convert string DB ke objek datetime (Naive)
        last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Jika format di DB beda, paksa reset ke sekarang
        await update_player_stats(user_id, last_active=now.strftime('%Y-%m-%d %H:%M:%S'))
        return

    # Hitung selisih jam (Keduanya sekarang sudah Naive, jadi tidak bentrok)
    duration = now - last_active
    hours_passed = duration.total_seconds() / 3600
    
    if hours_passed < 0.01: # Belum sampai 36 detik, abaikan
        return

    # Logika pengurangan (Contoh: Berkurang 5 poin per jam)
    new_hunger = max(0, player['hunger'] - (hours_passed * 5))
    new_thirst = max(0, player['thirst'] - (hours_passed * 7))
    
    # Stamina nambah saat istirahat (Contoh: Nambah 10 per jam)
    new_stamina = min(100, player['stamina'] + (hours_passed * 10))
    
    # Simpan ke DB
    await update_player_stats(
        user_id, 
        hunger=round(new_hunger, 2), 
        thirst=round(new_thirst, 2), 
        stamina=round(new_stamina, 2),
        last_active=now.strftime('%Y-%m-%d %H:%M:%S')
    )

# --- Tambahkan fungsi helper lain milikmu di bawah sini ---
def main_menu_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("🦌 Hunt", callback_query_data="menu_hunt"),
         InlineKeyboardButton("🎒 Bag", callback_query_data="menu_inventory")],
        [InlineKeyboardButton("🏪 Market", callback_query_data="menu_market"),
         InlineKeyboardButton("🏠 Home", callback_query_data="menu_home")],
        [InlineKeyboardButton("🏛️ Museum", callback_query_data="menu_museum"),
         InlineKeyboardButton("⚙️ Stats", callback_query_data="menu_stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_with_photo(context, chat_id, photo_key, text, reply_markup=None):
    # Dummy implementation, sesuaikan dengan cara kamu ambil foto
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )
