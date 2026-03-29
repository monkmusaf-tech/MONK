import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = "data/huntgame.db"

async def get_db():
    os.makedirs("data", exist_ok=True)
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
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
        
        -- Inventory - hasil buruan dan item
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_type TEXT,  -- 'animal_meat', 'animal_skin', 'item', 'food', 'drink'
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
        
        -- Achievements
        CREATE TABLE IF NOT EXISTS player_achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            achievement_id TEXT,
            unlocked_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES players(user_id)
        );
        
        -- P2P Market listings
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
            type TEXT,  -- 'topup', 'sell', 'buy', 'p2p', 'admin_give'
            amount INTEGER,
            description TEXT,
            status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
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
            behavior TEXT DEFAULT 'flee',  -- 'flee', 'aggressive', 'neutral', 'boss'
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
        
        -- Foods (craftable)
        CREATE TABLE IF NOT EXISTS foods (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '🍖',
            type TEXT DEFAULT 'food',  -- 'food', 'drink'
            hunger_restore REAL DEFAULT 0,
            thirst_restore REAL DEFAULT 0,
            stamina_restore REAL DEFAULT 0,
            craft_recipe TEXT,  -- JSON: {"animal_id": qty, ...}
            description TEXT,
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
        
        -- Leaderboard cache
        CREATE TABLE IF NOT EXISTS leaderboard_cache (
            type TEXT PRIMARY KEY,
            data TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Bot settings
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Active bosses
        CREATE TABLE IF NOT EXISTS active_bosses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_id TEXT,
            animal_name TEXT,
            map_id TEXT,
            hp_current INTEGER,
            hp_max INTEGER,
            reward_coins INTEGER,
            reward_items TEXT,
            spawned_at TEXT DEFAULT (datetime('now')),
            spawned_by INTEGER,
            is_alive INTEGER DEFAULT 1
        );
        
        -- Events
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            description TEXT,
            multiplier REAL DEFAULT 1.0,
            start_at TEXT,
            end_at TEXT,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER
        );
        
        -- Admin roles
        CREATE TABLE IF NOT EXISTS admin_roles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'moderator',
            permissions TEXT,  -- JSON array
            added_by INTEGER,
            added_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Activity logs
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip_hint TEXT,
            severity TEXT DEFAULT 'info',  -- 'info', 'warning', 'critical'
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        -- Topup packages
        CREATE TABLE IF NOT EXISTS topup_packages (
            id TEXT PRIMARY KEY,
            name TEXT,
            coins INTEGER,
            price INTEGER,  -- dalam rupiah/IDR
            bonus_percent INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        
        -- Market prices cache (dynamic)
        CREATE TABLE IF NOT EXISTS market_prices (
            item_id TEXT PRIMARY KEY,
            base_price INTEGER,
            current_price INTEGER,
            last_updated TEXT DEFAULT (datetime('now'))
        );
        """)
        await db.commit()
        
        # Seed default data
        await seed_default_data(db)
        print("✅ Database initialized successfully!")

async def seed_default_data(db):
    """Seed data awal jika belum ada"""
    
    # Check if already seeded
    cursor = await db.execute("SELECT COUNT(*) FROM animals")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return
    
    print("🌱 Seeding default data...")
    
    # === MAPS ===
    maps = [
        ("forest", "Hutan Rimba", "🌲", "Hutan lebat penuh hewan liar", 1),
        ("savanna", "Padang Savanna", "🌾", "Padang rumput luas, hewan langka", 5),
        ("mountain", "Pegunungan", "⛰️", "Puncak berbahaya, hewan epic", 10),
        ("swamp", "Rawa Gelap", "🌿", "Rawa misterius penuh bahaya", 15),
        ("volcano", "Gunung Berapi", "🌋", "Area ekstrem, hewan mythic", 25),
        ("ocean_coast", "Pantai Samudera", "🌊", "Tepi laut, hewan laut langka", 20),
    ]
    await db.executemany(
        "INSERT OR IGNORE INTO maps VALUES (?,?,?,?,?)",
        maps
    )
    
    # === ANIMALS (40+ spesies) ===
    animals = [
        # COMMON
        ("rabbit", "Kelinci", "🐰", "common", "forest", 50, 30, "Bulu Kelinci", 2, "All Day", "flee", 1, 30, 5, None, "Kelinci liar yang sering berlari", 1),
        ("chicken", "Ayam Hutan", "🐔", "common", "forest", 60, 40, "Bulu Ayam", 3, "Morning", "flee", 1, 40, 6, None, "Ayam hutan jinak", 1),
        ("duck", "Bebek Liar", "🦆", "common", "ocean_coast", 55, 35, "Bulu Bebek", 2, "Morning", "flee", 1, 35, 5, None, "Bebek liar di tepi air", 1),
        ("pigeon", "Merpati Liar", "🕊️", "common", "forest", 40, 25, "Bulu Merpati", 1, "All Day", "flee", 1, 25, 4, None, "Merpati yang terbang rendah", 1),
        ("squirrel", "Tupai", "🐿️", "common", "forest", 45, 30, "Ekor Tupai", 1, "Morning", "flee", 1, 30, 5, None, "Tupai lincah di pohon", 1),
        
        # UNCOMMON
        ("deer", "Rusa Biasa", "🦌", "uncommon", "forest", 150, 200, "Tanduk Rusa", 2, "All Day", "flee", 2, 80, 15, None, "Rusa yang anggun", 1),
        ("wild_boar", "Babi Hutan", "🐗", "uncommon", "forest", 200, 180, "Taring Babi", 2, "Night", "aggressive", 2, 120, 20, None, "Babi hutan yang agresif", 1),
        ("fox", "Rubah", "🦊", "uncommon", "forest", 180, 250, "Bulu Rubah", 1, "Night", "flee", 2, 70, 18, None, "Rubah licik dan cepat", 1),
        ("turkey", "Kalkun", "🦃", "uncommon", "savanna", 170, 160, "Bulu Kalkun", 3, "Morning", "flee", 2, 85, 16, None, "Kalkun besar berbulu indah", 1),
        ("peacock", "Merak", "🦚", "uncommon", "savanna", 160, 300, "Bulu Merak", 2, "All Day", "flee", 2, 75, 20, None, "Merak dengan ekor cantik", 1),
        ("monkey", "Monyet", "🐒", "uncommon", "forest", 130, 140, "Ekor Monyet", 1, "All Day", "aggressive", 2, 90, 17, None, "Monyet liar yang nakal", 1),
        
        # RARE
        ("wolf", "Serigala", "🐺", "rare", "forest", 350, 400, "Gigi Serigala", 3, "Night", "aggressive", 3, 200, 40, None, "Serigala pemimpin kawanan", 1),
        ("leopard", "Macan Tutul", "🐆", "rare", "savanna", 400, 500, "Kulit Macan Tutul", 2, "Night", "aggressive", 3, 250, 50, None, "Predator berbintik mematikan", 1),
        ("eagle", "Elang Emas", "🦅", "rare", "mountain", 380, 450, "Bulu Elang", 3, "Morning", "aggressive", 3, 180, 45, None, "Elang perkasa penguasa langit", 1),
        ("crocodile", "Buaya", "🐊", "rare", "swamp", 450, 520, "Kulit Buaya", 2, "All Day", "aggressive", 3, 350, 55, None, "Buaya berkulit keras", 1),
        ("bear", "Beruang Coklat", "🐻", "rare", "mountain", 500, 480, "Cakar Beruang", 2, "All Day", "aggressive", 4, 400, 60, None, "Beruang besar dan kuat", 1),
        ("python", "Piton Raksasa", "🐍", "rare", "swamp", 420, 500, "Sisik Python", 2, "Night", "aggressive", 3, 300, 50, None, "Ular piton yang melilit", 1),
        
        # EPIC
        ("tiger", "Harimau Bengal", "🐯", "epic", "savanna", 800, 1000, "Taring Harimau", 3, "Night", "aggressive", 5, 600, 100, None, "Raja hutan yang gagah", 1),
        ("lion", "Singa Afrika", "🦁", "epic", "savanna", 900, 1100, "Surai Singa", 3, "All Day", "aggressive", 5, 650, 110, None, "Raja sabana yang perkasa", 1),
        ("gorilla", "Gorila Perak", "🦍", "epic", "forest", 750, 900, "Tengkorak Gorila", 2, "All Day", "aggressive", 5, 700, 95, None, "Gorila besar dan kuat", 1),
        ("rhino", "Badak Putih", "🦏", "epic", "savanna", 1000, 1200, "Cula Badak", 2, "Morning", "aggressive", 5, 800, 120, None, "Badak langka bercula tunggal", 1),
        ("polar_bear", "Beruang Kutub", "🐻‍❄️", "epic", "mountain", 950, 1050, "Cakar Kutub", 3, "All Day", "aggressive", 5, 750, 115, None, "Beruang kutub mematikan", 1),
        ("shark", "Hiu Putih", "🦈", "epic", "ocean_coast", 1100, 1300, "Gigi Hiu", 3, "Night", "aggressive", 5, 850, 130, None, "Predator laut terganas", 1),
        
        # LEGENDARY
        ("white_tiger", "Harimau Putih", "⬜🐯", "legendary", "mountain", 2000, 3000, "Bulu Harimau Putih", 2, "Night", "aggressive", 7, 1500, 250, None, "Harimau putih mitos", 1),
        ("black_panther", "Pantera Hitam", "🐈‍⬛", "legendary", "forest", 2500, 3500, "Cakar Pantera", 2, "Night", "aggressive", 7, 1200, 300, None, "Predator gelap yang misterius", 1),
        ("golden_eagle", "Elang Emas Langka", "🦅", "legendary", "mountain", 3000, 4000, "Sayap Elang Emas", 2, "Morning", "flee", 7, 1000, 350, None, "Elang paling langka di dunia", 1),
        ("silver_wolf", "Serigala Perak", "🐺", "legendary", "forest", 2200, 3200, "Gigi Serigala Perak", 3, "Night", "aggressive", 7, 1300, 280, None, "Pemimpin kawanan legenda", 1),
        ("giant_croc", "Buaya Raksasa", "🐊", "legendary", "swamp", 2800, 4500, "Kulit Buaya Purba", 2, "Night", "aggressive", 7, 2000, 400, None, "Buaya purba berusia ratusan tahun", 1),
        
        # MYTHIC
        ("phoenix_bird", "Burung Phoenix", "🔥🦅", "mythic", "volcano", 8000, 12000, "Bulu Phoenix", 1, "All Day", "aggressive", 9, 3000, 800, None, "Burung mitologi api abadi", 1),
        ("ice_dragon", "Naga Es", "🐉", "mythic", "mountain", 10000, 15000, "Sisik Naga Es", 2, "Night", "aggressive", 9, 5000, 1000, None, "Naga legenda dari puncak beku", 1),
        ("shadow_leopard", "Macan Bayangan", "🐆", "mythic", "swamp", 9000, 13000, "Kulit Bayangan", 1, "Night", "aggressive", 9, 4000, 900, None, "Macan dimensi lain", 1),
        ("ocean_serpent", "Ular Laut Raksasa", "🐍", "mythic", "ocean_coast", 11000, 16000, "Sisik Laut Purba", 2, "Night", "aggressive", 9, 5500, 1100, None, "Leviathan dari kedalaman samudra", 1),
        ("thunder_bull", "Banteng Petir", "⚡🐂", "mythic", "savanna", 9500, 14000, "Tanduk Petir", 2, "All Day", "aggressive", 9, 4500, 950, None, "Banteng dengan kekuatan petir", 1),
        
        # BOSS
        ("forest_guardian", "Penjaga Hutan", "👹", "boss", "forest", 20000, 30000, "Jimat Hutan", 1, "Event", "boss", 10, 10000, 2000, None, "Boss hutan kuno yang sakti", 1),
        ("volcano_lord", "Tuan Gunung Berapi", "🌋👑", "boss", "volcano", 30000, 50000, "Inti Api", 1, "Event", "boss", 10, 15000, 3000, None, "Penguasa gunung berapi purba", 1),
        ("sea_god", "Dewa Laut", "🌊👑", "boss", "ocean_coast", 25000, 40000, "Trisula Emas", 1, "Event", "boss", 10, 12000, 2500, None, "Dewa penguasa lautan", 1),
        ("shadow_king", "Raja Bayangan", "👑🌑", "boss", "swamp", 35000, 60000, "Mahkota Kegelapan", 1, "Event", "boss", 10, 18000, 3500, None, "Raja dimensi kegelapan", 1),
        ("storm_dragon", "Naga Badai", "⛈️🐉", "boss", "mountain", 50000, 80000, "Jantung Badai", 1, "Event", "boss", 10, 25000, 5000, None, "Naga paling kuat di seluruh penjuru", 1),
        ("world_serpent", "Ular Dunia", "🌍🐍", "boss", "swamp", 45000, 70000, "Sisik Dunia", 1, "Event", "boss", 10, 22000, 4500, None, "Ular mitologi penopang dunia", 1),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO animals 
        (id, name, emoji, rarity, map_id, meat_price, skin_price, main_reward, 
        main_reward_amount, spawn_time, behavior, min_weapon_grade, hp, 
        exp_reward, photo_file_id, description, is_active) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        animals
    )
    
    # === WEAPONS ===
    weapons = [
        ("slingshot", "Ketapel", "🪃", 1, 5, 0.50, 0, "Senjata pemula gratis", None, 1),
        ("bow", "Busur Panah", "🏹", 2, 15, 0.65, 500, "Busur standar perburuan", None, 1),
        ("rifle", "Senapan Angin", "🔫", 3, 30, 0.70, 2000, "Senapan angin akurat", None, 1),
        ("shotgun", "Shotgun", "🔫", 4, 50, 0.65, 5000, "Damage tinggi jarak dekat", None, 1),
        ("sniper", "Sniper Rifle", "🎯", 5, 80, 0.85, 12000, "Akurasi tinggi jarak jauh", None, 1),
        ("assault_rifle", "Senapan Serbu", "🔫", 6, 100, 0.75, 20000, "Senapan serbu militer", None, 1),
        ("rocket_launcher", "Peluncur Roket", "🚀", 7, 200, 0.90, 50000, "Senjata boss slayer", None, 1),
        ("golden_bow", "Busur Emas", "✨🏹", 8, 150, 0.95, 100000, "Busur legendaris pemburu elite", None, 1),
        ("thunder_gun", "Pistol Petir", "⚡🔫", 9, 300, 0.95, 200000, "Senjata milik dewa", None, 1),
        ("ultima_blade", "Pedang Ultima", "⚔️", 10, 500, 0.99, 500000, "Senjata tersakti di dunia", None, 1),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO weapons 
        (id, name, emoji, grade, damage, accuracy, price, description, photo_file_id, is_active) 
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        weapons
    )
    
    # === ITEMS ===
    items = [
        ("health_potion", "Ramuan Stamina", "💊", "consumable", "stamina", 30, 200, "Pulihkan stamina 30", 1),
        ("energy_drink", "Energy Drink", "⚡", "consumable", "stamina", 50, 500, "Pulihkan stamina 50", 1),
        ("lucky_charm", "Jimat Keberuntungan", "🍀", "buff", "luck", 0.2, 1000, "Tingkatkan peluang rarity 20%", 1),
        ("bait_common", "Umpan Biasa", "🪱", "bait", "spawn_rate", 1.5, 300, "Tingkatkan spawn rate 50%", 1),
        ("bait_rare", "Umpan Langka", "✨🪱", "bait", "rare_rate", 2.0, 2000, "Tingkatkan peluang rare+", 1),
        ("trap", "Jebakan", "🪤", "tool", "auto_catch", 0.3, 1500, "30% auto tangkap hewan kabur", 1),
        ("binoculars", "Teropong", "🔭", "tool", "info", 1.0, 800, "Lihat info hewan sebelum berburu", 1),
        ("compass", "Kompas Ajaib", "🧭", "tool", "map", 1.0, 3000, "Unlock map rahasia sementara", 1),
        ("exp_scroll", "Gulungan EXP", "📜", "buff", "exp", 2.0, 5000, "2x EXP selama 1 jam", 1),
        ("coin_magnet", "Magnet Koin", "🧲", "buff", "coin", 1.5, 8000, "1.5x coin selama 2 jam", 1),
        ("revive_token", "Token Revive", "💫", "special", "revive", 1.0, 10000, "Revive saat mati kelaparan", 1),
        ("golden_ticket", "Tiket Emas", "🎟️", "special", "guaranteed_rare", 1.0, 25000, "Jamin dapat legendary hunt", 1),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO items 
        (id, name, emoji, type, effect, effect_value, price, description, is_active) 
        VALUES (?,?,?,?,?,?,?,?,?)""",
        items
    )
    
    # === HOME LEVELS ===
    homes = [
        (1, "Gubuk Bambu", 0, 0, 0, 5, 50, "Tempat tinggal sederhana"),
        (2, "Rumah Kayu", 5000, 2, 1, 8, 100, "Rumah kayu yang nyaman"),
        (3, "Rumah Bata", 20000, 5, 3, 12, 200, "Rumah bata kokoh"),
        (4, "Rumah Mewah", 100000, 10, 7, 18, 500, "Rumah mewah dengan fasilitas lengkap"),
        (5, "Istana Pemburu", 500000, 20, 15, 30, 1000, "Istana elite para legenda"),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO home_levels 
        (level, name, upgrade_cost, hunger_regen, thirst_regen, rest_regen, storage_slots, description) 
        VALUES (?,?,?,?,?,?,?,?)""",
        homes
    )
    
    # === FOODS ===
    foods = [
        ("grilled_meat", "Daging Panggang", "🍖", "food", 40, 0, 10, '{"rabbit": 2}', "Daging kelinci panggang", 1),
        ("roasted_bird", "Ayam Panggang", "🍗", "food", 50, 0, 15, '{"chicken": 1}', "Ayam hutan panggang lezat", 1),
        ("venison_stew", "Sup Rusa", "🍲", "food", 80, 20, 20, '{"deer": 1, "rabbit": 1}', "Sup rusa hangat bergizi", 1),
        ("beast_feast", "Pesta Daging", "🥩", "food", 100, 30, 30, '{"wild_boar": 1, "rabbit": 2}', "Makan besar pemburu legendaris", 1),
        ("fresh_water", "Air Segar", "💧", "drink", 0, 50, 5, '{}', "Air jernih dari sumber alami", 1),
        ("herbal_tea", "Teh Herbal", "🍵", "drink", 10, 60, 10, '{"squirrel": 1}', "Teh dari tumbuhan hutan", 1),
        ("energy_broth", "Kaldu Energi", "🥣", "drink", 20, 80, 25, '{"wolf": 1}', "Kaldu serigala penuh energi", 1),
        ("mythic_elixir", "Elixir Mitik", "✨🍵", "drink", 50, 100, 50, '{"phoenix_bird": 1}', "Elixir dari Phoenix langka", 1),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO foods 
        (id, name, emoji, type, hunger_restore, thirst_restore, stamina_restore, craft_recipe, description, is_active) 
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        foods
    )
    
    # === TOPUP PACKAGES ===
    packages = [
        ("pkg_starter", "Starter Pack", 1000, 10000, 0),
        ("pkg_bronze", "Bronze Pack", 5500, 50000, 10),
        ("pkg_silver", "Silver Pack", 12000, 100000, 20),
        ("pkg_gold", "Gold Pack", 65000, 500000, 30),
        ("pkg_diamond", "Diamond Pack", 150000, 1000000, 50),
        ("pkg_legend", "Legend Pack", 800000, 5000000, 60),
    ]
    
    await db.executemany(
        """INSERT OR IGNORE INTO topup_packages 
        (id, name, coins, price, bonus_percent) 
        VALUES (?,?,?,?,?)""",
        packages
    )
    
    # === BOT SETTINGS ===
    settings = [
        ("bot_name", "HuntGame Bot"),
        ("lobby_photo", ""),
        ("hunt_photo", ""),
        ("market_photo", ""),
        ("home_photo", ""),
        ("museum_photo", ""),
        ("boss_photo", ""),
        ("hunt_cooldown", "300"),
        ("double_exp", "0"),
        ("double_coin", "0"),
        ("maintenance_mode", "0"),
        ("max_inventory", "100"),
        ("spawn_rate", "1.0"),
        ("payment_info", "Transfer ke rekening:\nBCA: 1234567890\na.n. HuntGame\n\nSetelah transfer, kirim bukti ke admin"),
        ("welcome_message", "Selamat datang di HuntGame! 🦌\n\nGame berburu seru dengan 40+ hewan langka!\n\nGunakan /start untuk mulai bermain."),
    ]
    
    await db.executemany(
        "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?,?)",
        settings
    )
    
    # === MUSEUM SLOTS ===
    museum = [
        ("slot_common_1", "Koleksi Umum I", "common", 100),
        ("slot_common_2", "Koleksi Umum II", "common", 100),
        ("slot_uncommon_1", "Koleksi Langka I", "uncommon", 300),
        ("slot_uncommon_2", "Koleksi Langka II", "uncommon", 300),
        ("slot_rare_1", "Koleksi Berharga I", "rare", 700),
        ("slot_rare_2", "Koleksi Berharga II", "rare", 700),
        ("slot_epic_1", "Koleksi Epic I", "epic", 1500),
        ("slot_legendary_1", "Koleksi Legendaris I", "legendary", 5000),
        ("slot_mythic_1", "Koleksi Mitik I", "mythic", 15000),
        ("slot_boss_1", "Mahkota Boss I", "boss", 50000),
    ]
    
    await db.executemany(
        "INSERT OR IGNORE INTO museum_slots (id, name, required_rarity, trophy_reward) VALUES (?,?,?,?)",
        museum
    )
    
    await db.commit()
    print("✅ Default data seeded!")
