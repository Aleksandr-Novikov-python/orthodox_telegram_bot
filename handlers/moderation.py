import aiosqlite
from datetime import datetime, timedelta



class AsyncDatabase:
    def __init__(self, db_name="moderation.db"):
        self.db_name = db_name

    async def init_db(self):
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    full_name TEXT,
                    violation_text TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS violation_counts (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    count INTEGER DEFAULT 0,
                    last_violation DATETIME,
                    PRIMARY KEY (chat_id, user_id)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    banned_by INTEGER,
                    reason TEXT,
                    banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ban_until DATETIME
                )
            """)
            await conn.commit()

    async def add_violation(self, chat_id: int, user_id: int, username: str,
                            full_name: str, text: str) -> int:
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute("""
                INSERT INTO violation_counts (chat_id, user_id, count, last_violation)
                VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET
                    count = count + 1,
                    last_violation = CURRENT_TIMESTAMP
            """, (chat_id, user_id))
            await conn.execute("""
                INSERT INTO violations (chat_id, user_id, username, full_name, violation_text)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, user_id, username, full_name, text))
            async with conn.execute("""
                SELECT count FROM violation_counts WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id)) as cursor:
                row = await cursor.fetchone()
            await conn.commit()
            return row[0] if row else 1

    async def get_violation_count(self, chat_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_name) as conn:
            async with conn.execute("""
                SELECT count FROM violation_counts WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def reset_violations(self, chat_id: int, user_id: int):
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute("DELETE FROM violation_counts WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            await conn.execute("DELETE FROM violations WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            await conn.commit()

    async def add_ban(self, chat_id: int, user_id: int, banned_by: int,
                      reason: str, duration: int = 0):
        async with aiosqlite.connect(self.db_name) as conn:
            ban_until = None
            if duration > 0:
                ban_until = datetime.now() + timedelta(seconds=duration)
            await conn.execute("""
                INSERT INTO bans (chat_id, user_id, banned_by, reason, ban_until)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, user_id, banned_by, reason, ban_until))
            await conn.commit()

db = AsyncDatabase()