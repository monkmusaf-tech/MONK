import os
from dotenv import load_dotenv

load_dotenv()

# === BOT CONFIGURATION ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CHANNEL_ID = os.getenv("CHANNEL_ID", "")  # Channel jual beli
GROUP_ID = os.getenv("GROUP_ID", "")       # Group official
GROUP_LINK = os.getenv("GROUP_LINK", "https://t.me/huntgame")

# === DATABASE ===
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/huntgame.db")

# === GAME SETTINGS (bisa di-override dari DB) ===
DEFAULT_HUNT_COOLDOWN = 300        # 5 menit
DEFAULT_STAMINA_MAX = 100
DEFAULT_HUNGER_MAX = 100
DEFAULT_THIRST_MAX = 100
DEFAULT_REST_MAX = 100
DEFAULT_STAMINA_REGEN = 1          # per menit
DEFAULT_HUNGER_DRAIN = 2           # per jam
DEFAULT_THIRST_DRAIN = 3           # per jam
DEFAULT_REST_DRAIN = 1             # per jam

# Rarity multiplier default
RARITY_MULTIPLIERS = {
    "common": 1.0,
    "uncommon": 1.5,
    "rare": 2.0,
    "epic": 3.0,
    "legendary": 5.0,
    "mythic": 8.0,
    "boss": 15.0
}

# === MARKET ===
MARKET_FLUCTUATION = 0.1   # 10% fluktuasi harga
MARKET_UPDATE_INTERVAL = 3600  # 1 jam

# === VERSION ===
BOT_VERSION = "1.0.0"
BOT_NAME = "HuntGame Bot"
