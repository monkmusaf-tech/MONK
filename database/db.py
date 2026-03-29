import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = "data/huntgame.db"

# Variabel global untuk menyimpan koneksi tunggal (Singleton)
_db = None

async def get_db():
    """Mengambil koneksi database global"""
    global _db
    os.makedirs("data", exist_ok=True)
    
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        
    return _db

async def init_db():
    """Inisialisasi semua tabel dan seed data awal"""
    os.makedirs("data", exist_ok=True)
    db = await get_db()
    
    await db.executescript("""
        PRAGMA journal_mode=WAL;
        
        -- Players
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            coins INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            hunger REAL DEFAULT 100,
            thirst REAL DEFAULT 100,
            stamina REAL DEFAULT 100,
            rest REAL DEFAULT 100,
            home_level INTEGER DEFAULT 1,
            weapon_equipped TEXT DEFAULT 'default',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            is_muted INTEGER DEFAULT 0,
            total_hunts INTEGER DEFAULT 0,
            total_kills INTEGER DEFAULT 0,
            total_earnings INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT (datetime('now')),
            last_hunt TEXT,
            last_active TEXT DEFAULT (datetime('now'))
        );
        
        -- Inventory
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_type TEXT,
            item_id TEXT,
            item_name TEXT,
            quantity INTEGER DEFAULT 1,
            acquired_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );
        
        -- Weapons owned
        CREATE TABLE IF NOT EXISTS player_weapons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            weapon_id TEXT,
            weapon_name TEXT,
            acquired_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );

        -- Activity Logs (TAMBAHAN: Agar tidak error sqlite3.OperationalError)
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            severity TEXT DEFAULT 'info',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );
        
        -- Museum trophies
        CREATE TABLE IF NOT EXISTS museum_trophies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            animal_id TEXT,
            animal_name TEXT,
            rarity TEXT,
            added_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );
        
        -- P2P Market
        CREATE TABLE IF NOT EXISTS p2p_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            seller_name TEXT,
            item_type TEXT,
            item_id TEXT,
            item_name TEXT,
            quantity INTEGER,
            price_per_unit INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY(seller_id) REFERENCES players(user_id)
        );
        
        -- Transactions
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount INTEGER,
            description TEXT,
            status TEXT DEFAULT 'pending',
            proof_file_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            processed_at TEXT,
            processed_by INTEGER,
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );
        
        -- Master Data: Animals, Weapons, Items, Maps, Homes, Foods, Settings, Packages
        CREATE TABLE IF NOT EXISTS animals (id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '🦌', rarity TEXT DEFAULT 'common', map_id TEXT, meat_price INTEGER DEFAULT 100, skin_price INTEGER DEFAULT 150, main_reward TEXT, main_reward_amount INTEGER DEFAULT 1, spawn_time TEXT DEFAULT 'All Day', behavior TEXT DEFAULT 'flee', min_weapon_grade INTEGER DEFAULT 1, hp INTEGER DEFAULT 100, exp_reward INTEGER DEFAULT 10, photo_file_id TEXT, description TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS weapons (id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '🔫', grade INTEGER DEFAULT 1, damage INTEGER DEFAULT 10, accuracy REAL DEFAULT 0.7, price INTEGER DEFAULT 500, description TEXT, photo_file_id TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '🎒', type TEXT DEFAULT 'consumable', effect TEXT, effect_value REAL DEFAULT 0, price INTEGER DEFAULT 100, description TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS maps (id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '🗺️', description TEXT, min_level INTEGER DEFAULT 1, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS home_levels (level INTEGER PRIMARY KEY, name TEXT, upgrade_cost INTEGER, hunger_regen REAL DEFAULT 0, thirst_regen REAL DEFAULT 0, rest_regen REAL DEFAULT 0, storage_slots INTEGER DEFAULT 50, description TEXT);
        CREATE TABLE IF NOT EXISTS foods (id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '🍖', type TEXT DEFAULT 'food', hunger_restore REAL DEFAULT 0, thirst_restore REAL DEFAULT 0, stamina_restore REAL DEFAULT 0, craft_recipe TEXT, description TEXT, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS topup_packages (id TEXT PRIMARY KEY, name TEXT, coins INTEGER, price INTEGER, bonus_percent INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS museum_slots (id TEXT PRIMARY KEY, name TEXT, required_rarity TEXT, trophy_reward INTEGER DEFAULT 0, description TEXT);
    """)
    await db.commit()
    
    # Seed data
    await seed_default_data(db)
    print("✅ Database initialized successfully!")

async def seed_default_data(db):
    """Seed data awal jika tabel master masih kosong"""
    cursor = await db.execute("SELECT COUNT(*) FROM maps")
    if (await cursor.fetchone())[0] > 0:
        return
    
    print("🌱 Seeding default data...")
    maps = [
        ("forest", "Hutan Rimba", "🌲", "Hutan lebat penuh hewan liar", 1, 1),
        ("savanna", "Padang Savanna", "🌾", "Padang rumput luas, hewan langka", 5, 1),
        ("mountain", "Pegunungan", "⛰️", "Puncak berbahaya, hewan epic", 10, 1)
    ]
    await db.executemany("INSERT OR IGNORE INTO maps VALUES (?,?,?,?,?,?)", maps)
    await db.commit()
    print("✅ Default data seeded!")

async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        print("🔌 Database connection closed.")
