import json
from datetime import datetime
from database.db import get_db

# ===================== PLAYER QUERIES =====================

async def get_player(user_id: int):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
        return await cursor.fetchone()

async def create_player(user_id: int, username: str, full_name: str):
    async with await get_db() as db:
        await db.execute(
            """INSERT OR IGNORE INTO players (user_id, username, full_name) VALUES (?,?,?)""",
            (user_id, username, full_name)
        )
        await db.commit()
    return await get_player(user_id)

async def update_player(user_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with await get_db() as db:
        await db.execute(f"UPDATE players SET {sets} WHERE user_id=?", vals)
        await db.commit()

async def add_coins(user_id: int, amount: int):
    async with await get_db() as db:
        await db.execute(
            "UPDATE players SET coins=coins+?, total_earnings=total_earnings+? WHERE user_id=?",
            (amount, max(0, amount), user_id)
        )
        await db.commit()

async def add_exp(user_id: int, amount: int):
    """Add EXP and handle level up"""
    player = await get_player(user_id)
    if not player:
        return 0, False
    
    new_exp = player['exp'] + amount
    new_level = player['level']
    leveled_up = False
    
    # Level formula: needs level*100 EXP per level
    while new_exp >= new_level * 100:
        new_exp -= new_level * 100
        new_level += 1
        leveled_up = True
    
    await update_player(user_id, exp=new_exp, level=new_level)
    return new_level, leveled_up

# ===================== INVENTORY QUERIES =====================

async def get_inventory(user_id: int, item_type: str = None):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        if item_type:
            cursor = await db.execute(
                "SELECT * FROM inventory WHERE user_id=? AND item_type=? ORDER BY acquired_at DESC",
                (user_id, item_type)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM inventory WHERE user_id=? ORDER BY item_type, acquired_at DESC",
                (user_id,)
            )
        return await cursor.fetchall()

async def add_inventory(user_id: int, item_type: str, item_id: str, item_name: str, quantity: int = 1):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (user_id, item_type, item_id)
        )
        existing = await cursor.fetchone()
        if existing:
            await db.execute(
                "UPDATE inventory SET quantity=quantity+? WHERE id=?",
                (quantity, existing[0])
            )
        else:
            await db.execute(
                "INSERT INTO inventory (user_id, item_type, item_id, item_name, quantity) VALUES (?,?,?,?,?)",
                (user_id, item_type, item_id, item_name, quantity)
            )
        await db.commit()

async def remove_inventory(user_id: int, item_type: str, item_id: str, quantity: int = 1):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (user_id, item_type, item_id)
        )
        item = await cursor.fetchone()
        if not item or item[1] < quantity:
            return False
        if item[1] == quantity:
            await db.execute("DELETE FROM inventory WHERE id=?", (item[0],))
        else:
            await db.execute("UPDATE inventory SET quantity=quantity-? WHERE id=?", (quantity, item[0]))
        await db.commit()
        return True

async def count_inventory(user_id: int):
    async with await get_db() as db:
        cursor = await db.execute("SELECT SUM(quantity) FROM inventory WHERE user_id=?", (user_id,))
        result = await cursor.fetchone()
        return result[0] or 0

# ===================== ANIMAL QUERIES =====================

async def get_animals(map_id: str = None, rarity: str = None, active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM animals WHERE 1=1"
        params = []
        if active_only:
            query += " AND is_active=1"
        if map_id:
            query += " AND map_id=?"
            params.append(map_id)
        if rarity:
            query += " AND rarity=?"
            params.append(rarity)
        query += " ORDER BY CASE rarity WHEN 'common' THEN 1 WHEN 'uncommon' THEN 2 WHEN 'rare' THEN 3 WHEN 'epic' THEN 4 WHEN 'legendary' THEN 5 WHEN 'mythic' THEN 6 WHEN 'boss' THEN 7 END"
        cursor = await db.execute(query, params)
        return await cursor.fetchall()

async def get_animal(animal_id: str):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM animals WHERE id=?", (animal_id,))
        return await cursor.fetchone()

async def search_animals(keyword: str):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute(
            "SELECT * FROM animals WHERE name LIKE ? AND is_active=1",
            (f"%{keyword}%",)
        )
        return await cursor.fetchall()

# ===================== WEAPON QUERIES =====================

async def get_weapons(active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM weapons"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY grade"
        cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_weapon(weapon_id: str):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM weapons WHERE id=?", (weapon_id,))
        return await cursor.fetchone()

async def get_player_weapons(user_id: int):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute(
            "SELECT pw.*, w.grade, w.damage, w.accuracy FROM player_weapons pw JOIN weapons w ON pw.weapon_id=w.id WHERE pw.user_id=?",
            (user_id,)
        )
        return await cursor.fetchall()

async def player_has_weapon(user_id: int, weapon_id: str):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM player_weapons WHERE user_id=? AND weapon_id=?",
            (user_id, weapon_id)
        )
        return await cursor.fetchone() is not None

async def give_weapon(user_id: int, weapon_id: str, weapon_name: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO player_weapons (user_id, weapon_id, weapon_name) VALUES (?,?,?)",
            (user_id, weapon_id, weapon_name)
        )
        await db.commit()

# ===================== MARKET QUERIES =====================

async def get_current_price(item_id: str, base_price: int):
    """Get dynamic market price"""
    import random
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM market_prices WHERE item_id=?", (item_id,))
        price_data = await cursor.fetchone()
        
        if not price_data:
            current = base_price
            await db.execute(
                "INSERT INTO market_prices (item_id, base_price, current_price) VALUES (?,?,?)",
                (item_id, base_price, current)
            )
            await db.commit()
            return current
        
        # Fluctuate price
        fluctuation = random.uniform(-0.1, 0.1)
        new_price = int(price_data['base_price'] * (1 + fluctuation))
        new_price = max(int(price_data['base_price'] * 0.5), min(int(price_data['base_price'] * 2), new_price))
        
        await db.execute(
            "UPDATE market_prices SET current_price=?, last_updated=datetime('now') WHERE item_id=?",
            (new_price, item_id)
        )
        await db.commit()
        return new_price

async def get_p2p_listings(active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM p2p_listings"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY created_at DESC LIMIT 50"
        cursor = await db.execute(query)
        return await cursor.fetchall()

async def create_p2p_listing(seller_id: int, seller_name: str, item_type: str, item_id: str, item_name: str, quantity: int, price_per_unit: int):
    async with await get_db() as db:
        await db.execute(
            """INSERT INTO p2p_listings 
            (seller_id, seller_name, item_type, item_id, item_name, quantity, price_per_unit) 
            VALUES (?,?,?,?,?,?,?)""",
            (seller_id, seller_name, item_type, item_id, item_name, quantity, price_per_unit)
        )
        await db.commit()

async def buy_p2p(listing_id: int, buyer_id: int, quantity: int):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM p2p_listings WHERE id=? AND is_active=1", (listing_id,))
        listing = await cursor.fetchone()
        if not listing or listing['quantity'] < quantity:
            return None
        
        total_cost = listing['price_per_unit'] * quantity
        
        # Check buyer coins
        cursor = await db.execute("SELECT coins FROM players WHERE user_id=?", (buyer_id,))
        buyer = await cursor.fetchone()
        if not buyer or buyer[0] < total_cost:
            return None
        
        # Deduct buyer coins
        await db.execute("UPDATE players SET coins=coins-? WHERE user_id=?", (total_cost, buyer_id))
        # Add seller coins
        await db.execute("UPDATE players SET coins=coins+? WHERE user_id=?", (total_cost, listing['seller_id']))
        
        # Update listing
        remaining = listing['quantity'] - quantity
        if remaining <= 0:
            await db.execute("UPDATE p2p_listings SET is_active=0 WHERE id=?", (listing_id,))
        else:
            await db.execute("UPDATE p2p_listings SET quantity=? WHERE id=?", (remaining, listing_id))
        
        await db.commit()
        return listing

# ===================== MUSEUM QUERIES =====================

async def get_museum_trophies(user_id: int):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM museum_trophies WHERE user_id=? ORDER BY added_at DESC", (user_id,))
        return await cursor.fetchall()

async def add_trophy(user_id: int, animal_id: str, animal_name: str, rarity: str, trophy_reward: int):
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM museum_trophies WHERE user_id=? AND animal_id=?",
            (user_id, animal_id)
        )
        if await cursor.fetchone():
            return False  # Already have this trophy
        
        await db.execute(
            "INSERT INTO museum_trophies (user_id, animal_id, animal_name, rarity) VALUES (?,?,?,?)",
            (user_id, animal_id, animal_name, rarity)
        )
        await db.execute("UPDATE players SET coins=coins+? WHERE user_id=?", (trophy_reward, user_id))
        await db.commit()
        return True

async def get_museum_leaderboard():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("""
            SELECT p.user_id, p.username, p.full_name, COUNT(mt.id) as trophy_count
            FROM players p
            LEFT JOIN museum_trophies mt ON p.user_id=mt.user_id
            GROUP BY p.user_id
            ORDER BY trophy_count DESC
            LIMIT 20
        """)
        return await cursor.fetchall()

# ===================== LEADERBOARD QUERIES =====================

async def get_leaderboard(lb_type: str):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        
        if lb_type == "coins":
            cursor = await db.execute(
                "SELECT user_id, username, full_name, coins FROM players ORDER BY coins DESC LIMIT 20"
            )
        elif lb_type == "level":
            cursor = await db.execute(
                "SELECT user_id, username, full_name, level, exp FROM players ORDER BY level DESC, exp DESC LIMIT 20"
            )
        elif lb_type == "kills":
            cursor = await db.execute(
                "SELECT user_id, username, full_name, total_kills FROM players ORDER BY total_kills DESC LIMIT 20"
            )
        elif lb_type == "earnings":
            cursor = await db.execute(
                "SELECT user_id, username, full_name, total_earnings FROM players ORDER BY total_earnings DESC LIMIT 20"
            )
        else:
            return []
        
        return await cursor.fetchall()

# ===================== TRANSACTION QUERIES =====================

async def create_transaction(user_id: int, txn_type: str, amount: int, description: str, proof_file_id: str = None):
    async with await get_db() as db:
        cursor = await db.execute(
            """INSERT INTO transactions (user_id, type, amount, description, proof_file_id) 
            VALUES (?,?,?,?,?)""",
            (user_id, txn_type, amount, description, proof_file_id)
        )
        await db.commit()
        return cursor.lastrowid

async def get_pending_topups():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute(
            """SELECT t.*, p.username, p.full_name 
            FROM transactions t 
            JOIN players p ON t.user_id=p.user_id
            WHERE t.type='topup' AND t.status='pending' 
            ORDER BY t.created_at ASC"""
        )
        return await cursor.fetchall()

async def get_transactions(user_id: int = None, limit: int = 50):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        if user_id:
            cursor = await db.execute(
                "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return await cursor.fetchall()

async def update_transaction(txn_id: int, status: str, processed_by: int):
    async with await get_db() as db:
        await db.execute(
            """UPDATE transactions SET status=?, processed_by=?, processed_at=datetime('now') 
            WHERE id=?""",
            (status, processed_by, txn_id)
        )
        await db.commit()

# ===================== BOT SETTINGS QUERIES =====================

async def get_setting(key: str):
    async with await get_db() as db:
        cursor = await db.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_setting(key: str, value: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?,?,datetime('now'))",
            (key, value)
        )
        await db.commit()

async def get_all_settings():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM bot_settings")
        rows = await cursor.fetchall()
        return {r['key']: r['value'] for r in rows}

# ===================== LOG QUERIES =====================

async def add_log(user_id: int, action: str, details: str, severity: str = "info"):
    async with await get_db() as db:
        await db.execute(
            "INSERT INTO activity_logs (user_id, action, details, severity) VALUES (?,?,?,?)",
            (user_id, action, details, severity)
        )
        await db.commit()

async def get_logs(limit: int = 100, severity: str = None):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        if severity:
            cursor = await db.execute(
                "SELECT * FROM activity_logs WHERE severity=? ORDER BY created_at DESC LIMIT ?",
                (severity, limit)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return await cursor.fetchall()

# ===================== ADMIN QUERIES =====================

async def get_admin_role(user_id: int):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM admin_roles WHERE user_id=?", (user_id,))
        return await cursor.fetchone()

async def get_all_admins():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM admin_roles ORDER BY role")
        return await cursor.fetchall()

async def get_all_players(limit: int = None, search: str = None):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        if search:
            cursor = await db.execute(
                "SELECT * FROM players WHERE username LIKE ? OR full_name LIKE ? ORDER BY joined_at DESC",
                (f"%{search}%", f"%{search}%")
            )
        else:
            query = "SELECT * FROM players ORDER BY last_active DESC"
            if limit:
                query += f" LIMIT {limit}"
            cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_stats():
    """Get game statistics for dashboard"""
    async with await get_db() as db:
        stats = {}
        
        cursor = await db.execute("SELECT COUNT(*) FROM players")
        stats['total_players'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM players WHERE last_active > datetime('now', '-1 hour')"
        )
        stats['online_players'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT SUM(amount) FROM transactions WHERE type='topup' AND status='approved' AND created_at > datetime('now', 'start of day')"
        )
        result = await cursor.fetchone()
        stats['revenue_today'] = result[0] or 0
        
        cursor = await db.execute("SELECT SUM(total_hunts) FROM players")
        result = await cursor.fetchone()
        stats['total_hunts'] = result[0] or 0
        
        cursor = await db.execute("SELECT COUNT(*) FROM transactions WHERE type='topup' AND status='pending'")
        stats['pending_topups'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM active_bosses WHERE is_alive=1")
        stats['active_bosses'] = (await cursor.fetchone())[0]
        
        return stats

async def get_active_bosses():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM active_bosses WHERE is_alive=1 ORDER BY spawned_at DESC")
        return await cursor.fetchall()

async def spawn_boss(animal_id: str, animal_name: str, map_id: str, hp: int, reward_coins: int, reward_items: str, spawned_by: int):
    async with await get_db() as db:
        cursor = await db.execute(
            """INSERT INTO active_bosses 
            (animal_id, animal_name, map_id, hp_current, hp_max, reward_coins, reward_items, spawned_by) 
            VALUES (?,?,?,?,?,?,?,?)""",
            (animal_id, animal_name, map_id, hp, hp, reward_coins, reward_items, spawned_by)
        )
        await db.commit()
        return cursor.lastrowid

async def get_maps(active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM maps"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY min_level"
        cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_topup_packages():
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cursor = await db.execute("SELECT * FROM topup_packages WHERE is_active=1 ORDER BY price")
        return await cursor.fetchall()

async def get_foods(active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM foods"
        if active_only:
            query += " WHERE is_active=1"
        cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_items(active_only: bool = True):
    async with await get_db() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        query = "SELECT * FROM items"
        if active_only:
            query += " WHERE is_active=1"
        cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_achievements():
    """Return hardcoded achievements list"""
    return [
        {"id": "first_hunt", "name": "Pemburu Pertama", "desc": "Selesaikan 1 perburuan", "req": 1, "type": "hunts", "reward": 100},
        {"id": "hunt_10", "name": "Pemburu Aktif", "desc": "Selesaikan 10 perburuan", "req": 10, "type": "hunts", "reward": 500},
        {"id": "hunt_100", "name": "Pemburu Veteran", "desc": "Selesaikan 100 perburuan", "req": 100, "type": "hunts", "reward": 5000},
        {"id": "hunt_1000", "name": "Legenda Pemburu", "desc": "Selesaikan 1000 perburuan", "req": 1000, "type": "hunts", "reward": 50000},
        {"id": "level_10", "name": "Petualang", "desc": "Capai level 10", "req": 10, "type": "level", "reward": 2000},
        {"id": "level_50", "name": "Elite", "desc": "Capai level 50", "req": 50, "type": "level", "reward": 20000},
        {"id": "level_100", "name": "Grandmaster", "desc": "Capai level 100", "req": 100, "type": "level", "reward": 200000},
        {"id": "trophy_5", "name": "Kolektor Pemula", "desc": "Kumpulkan 5 trofi", "req": 5, "type": "trophies", "reward": 1000},
        {"id": "trophy_20", "name": "Kolektor Sejati", "desc": "Kumpulkan 20 trofi", "req": 20, "type": "trophies", "reward": 10000},
        {"id": "millionaire", "name": "Jutawan", "desc": "Kumpulkan 1.000.000 koin", "req": 1000000, "type": "coins", "reward": 50000},
    ]

async def check_achievements(user_id: int):
    """Check and award achievements"""
    player = await get_player(user_id)
    if not player:
        return []
    
    achievements = await get_achievements()
    trophies = await get_museum_trophies(user_id)
    
    newly_unlocked = []
    
    for ach in achievements:
        # Check if already unlocked
        async with await get_db() as db:
            cursor = await db.execute(
                "SELECT id FROM player_achievements WHERE user_id=? AND achievement_id=?",
                (user_id, ach['id'])
            )
            if await cursor.fetchone():
                continue
        
        unlocked = False
        if ach['type'] == 'hunts' and player['total_hunts'] >= ach['req']:
            unlocked = True
        elif ach['type'] == 'level' and player['level'] >= ach['req']:
            unlocked = True
        elif ach['type'] == 'trophies' and len(trophies) >= ach['req']:
            unlocked = True
        elif ach['type'] == 'coins' and player['coins'] >= ach['req']:
            unlocked = True
        
        if unlocked:
            async with await get_db() as db:
                await db.execute(
                    "INSERT INTO player_achievements (user_id, achievement_id) VALUES (?,?)",
                    (user_id, ach['id'])
                )
                await db.execute(
                    "UPDATE players SET coins=coins+? WHERE user_id=?",
                    (ach['reward'], user_id)
                )
                await db.commit()
            newly_unlocked.append(ach)
    
    return newly_unlocked
