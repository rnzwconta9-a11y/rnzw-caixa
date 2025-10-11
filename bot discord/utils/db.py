import aiosqlite
import os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'mystery_bot.db')

async def init_db():
    print("DEBUG: Initializing database...")
    async with aiosqlite.connect(db_path) as conn:
        print("DEBUG: Database connection established.")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                username TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mystery_boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                price REAL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_id INTEGER,
                name TEXT NOT NULL,
                rarity TEXT,
                value REAL DEFAULT 0.0,
                FOREIGN KEY (box_id) REFERENCES mystery_boxes(id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                prize_id INTEGER,
                key_code TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (prize_id) REFERENCES prizes(id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_code TEXT UNIQUE NOT NULL,
                box_id INTEGER,
                user_id INTEGER NULL,
                used BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (box_id) REFERENCES mystery_boxes(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS test_key_usage (
                user_id TEXT PRIMARY KEY,
                used INTEGER DEFAULT 0
            )
        """)
        await conn.commit()

async def add_user(discord_id, username):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT OR IGNORE INTO users (discord_id, username) VALUES (?, ?)", (discord_id, username))
        await conn.commit()
        cursor = await conn.execute("SELECT id, discord_id, username FROM users WHERE discord_id = ?", (discord_id,))
        return await cursor.fetchone()

async def get_user_by_discord_id(discord_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT id, discord_id, username FROM users WHERE discord_id = ?", (discord_id,))
        return await cursor.fetchone()

async def add_mystery_box(name, description, price):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT INTO mystery_boxes (name, description, price) VALUES (?, ?, ?)", (name, description, price))
        await conn.commit()
        cursor = await conn.execute("SELECT id FROM mystery_boxes WHERE name = ?", (name,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_mystery_box_by_name(name):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT id, name, description, price FROM mystery_boxes WHERE name = ?", (name,))
        return await cursor.fetchone()

async def add_prize(box_id, name, rarity, value=0.0):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT INTO prizes (box_id, name, rarity, value) VALUES (?, ?, ?, ?)", (box_id, name, rarity, value))
        await conn.commit()

async def get_prizes_by_box_id(box_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT id, box_id, name, rarity, value FROM prizes WHERE box_id = ?", (box_id,))
        return await cursor.fetchall()

async def get_all_prizes():
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT id, box_id, name, rarity, value FROM prizes")
        return await cursor.fetchall()

async def add_key(key_code, box_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("INSERT INTO keys (key_code, box_id) VALUES (?, ?)", (key_code, box_id))
        await conn.commit()
        return cursor.lastrowid

async def use_key(key_code, user_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("UPDATE keys SET used = 1, user_id = ? WHERE key_code = ? AND used = 0", (user_id, key_code))
        await conn.commit()
        return cursor.rowcount > 0

async def get_key_by_code(key_code):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT * FROM keys WHERE key_code = ?", (key_code,))
        return await cursor.fetchone()

async def get_all_keys():
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT * FROM keys")
        return await cursor.fetchall()

async def get_unused_key_for_box(box_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT key_code FROM keys WHERE box_id = ? AND used = 0 LIMIT 1", (box_id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def set_config(key, value):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()

async def get_config(key):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def record_test_key_usage(user_id):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT OR REPLACE INTO test_key_usage (user_id, used) VALUES (?, 1)", (user_id,))
        await conn.commit()

async def has_used_test_key(user_id):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT used FROM test_key_usage WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result[0] == 1 if result else False



async def record_prize_won(user_db_id, prize_id, key_code=None):
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("INSERT INTO user_prizes (user_id, prize_id, key_code) VALUES (?, ?, ?)", (user_db_id, prize_id, key_code))
        await conn.commit()



async def get_or_create_prize(box_id, name, rarity, value=None):
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT id, box_id, name, rarity, value FROM prizes WHERE box_id = ? AND name = ?", (box_id, name))
        prize = await cursor.fetchone()
        if prize:
            return prize
        else:
            await conn.execute("INSERT INTO prizes (box_id, name, rarity, value) VALUES (?, ?, ?, ?)", (box_id, name, rarity, value))
            await conn.commit()
            cursor = await conn.execute("SELECT id, box_id, name, rarity, value FROM prizes WHERE box_id = ? AND name = ?", (box_id, name))
            return await cursor.fetchone()



async def get_usage_history():
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            SELECT 
                u.discord_id, 
                u.username, 
                p.name as prize_name, 
                up.key_code, 
                up.timestamp
            FROM user_prizes up
            JOIN users u ON up.user_id = u.id
            JOIN prizes p ON up.prize_id = p.id
            ORDER BY up.timestamp DESC
            LIMIT 100
        """)
        return await cursor.fetchall()

