import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = "data/huntgame.db"

# Variabel global untuk menyimpan koneksi tunggal
_db = None

async def get_db():
    """Mengambil koneksi database global (Singleton Pattern)"""
    global _db
    os.makedirs("data", exist_ok=True)
    
    # Jika koneksi belum ada, buat baru
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        # Agar hasil query bisa diakses dengan nama kolom (misal: player['username'])
        _db.row_factory = aiosqlite.Row
        
    return _db

async def init_db():
    """Inisialisasi tabel dan seed data awal"""
    os.makedirs("data", exist_ok=True)
    
    # Gunakan koneksi global
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
        
        -- Animals (master data)
        CREATE TABLE IF NOT EXISTS animals (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🦌',
            rarity TEXT DEFAULT 'common',
            map_id TEXT,
            meat_price INTEGER DEFAULT 100,
            skin_price INTEGER DEFAULT 150,
            main_reward TEXT,
            main_reward_amount INTEGER DEFAULT 1,
            spawn_time TEXT DEFAULT 'All Day',
            behavior TEXT DEFAULT 'flee',
            min_weapon_grade INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 100,
            exp_reward INTEGER DEFAULT 10,
            photo_file_id TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        -- Weapons (master data)
        CREATE TABLE IF NOT EXISTS weapons (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🔫',
            grade INTEGER DEFAULT 1,
            damage INTEGER DEFAULT 10,
            accuracy REAL DEFAULT 0.7,
            price INTEGER DEFAULT 500,
            description TEXT,
            photo_file_id TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        -- Items (master data)
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🎒',
            type TEXT DEFAULT 'consumable',
            effect TEXT,
            effect_value REAL DEFAULT 0,
            price INTEGER DEFAULT 100,
            description TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        -- Maps (master data)
        CREATE TABLE IF NOT EXISTS maps (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🗺️',
            description TEXT,
            min_level INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1
        );
        
        -- Home levels config
        CREATE TABLE IF NOT EXISTS home_levels (
            level INTEGER PRIMARY KEY,
            name TEXT,
            upgrade_cost INTEGER,
            hunger_regen REAL DEFAULT 0,
            thirst_regen REAL DEFAULT 0,
            rest_regen REAL DEFAULT 0,
            storage_slots INTEGER DEFAULT 50,
            description TEXT
        );
        
        -- Foods
        CREATE TABLE IF NOT EXISTS foods (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🍖',
            type TEXT DEFAULT 'food',
            hunger_restore REAL DEFAULT 0,
            thirst_restore REAL DEFAULT 0,
            stamina_restore REAL DEFAULT 0,
            craft_recipe TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1
        );
        
        -- Bot settings
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Topup packages
        CREATE TABLE IF NOT EXISTS topup_packages (
            id TEXT PRIMARY KEY,
            name TEXT,
            coins INTEGER,
            price INTEGER,
            bonus_percent INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );

        -- Museum slots config
        CREATE TABLE IF NOT EXISTS museum_slots (
            id TEXT PRIMARY KEY,
            name TEXT,
            required_rarity TEXT,
            trophy_reward INTEGER DEFAULT 0,
            description TEXT
        );
    """)
    await db.commit()
    
    # Seed default data
    await seed_default_data(db)
    print("✅ Database initialized successfully!")

async def seed_default_data(db):
    """Seed data awal jika belum ada"""
    cursor = await db.execute("SELECT COUNT(*) FROM animals")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return
    
    print("🌱 Seeding default data...")
    
    # --- MASUKKAN SEMUA LIST DATA KAMU DI SINI ---
    # (Maps, Animals, Weapons, Items, Homes, Foods, Packages, Settings, Museum)
    # Gunakan db.executemany seperti kode awalmu
    
    # Contoh Maps:
    maps = [
        ("forest", "Hutan Rimba", "🌲", "Hutan lebat penuh hewan liar", 1, 1),
        ("savanna", "Padang Savanna", "🌾", "Padang rumput luas, hewan langka", 5, 1),
        ("mountain", "Pegunungan", "⛰️", "Puncak berbahaya, hewan epic", 10, 1),
        ("swamp", "Rawa Gelap", "🌿", "Rawa misterius penuh bahaya", 15, 1),
        ("volcano", "Gunung Berapi", "🌋", "Area ekstrem, hewan mythic", 25, 1),
        ("ocean_coast", "Pantai Samudera", "🌊", "Tepi laut, hewan laut langka", 20, 1),
    ]
    await db.executemany("INSERT OR IGNORE INTO maps VALUES (?,?,?,?,?,?)", maps)
    
    # (Lanjutkan masukkan data animals, weapons, dll sesuai kode aslimu)
    # ... bagian executemany yang panjang tadi letakkan di sini ...

    await db.commit()
    print("✅ Default data seeded!")

async def close_db():
    """Menutup koneksi database dengan aman saat bot dimatikan"""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        print("🔌 Database connection closed.")
