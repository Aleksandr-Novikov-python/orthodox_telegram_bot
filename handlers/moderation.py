import aiosqlite
import logging
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
            # Индексы для ускорения поиска
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_violations_chat_user ON violations(chat_id, user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bans_chat_user ON bans(chat_id, user_id)")
            await conn.commit()
            logging.info("✅ База данных инициализирована")

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
            count = row[0] if row else 1
            logging.info(f"⚠️ Нарушение добавлено: chat={chat_id}, user={user_id}, count={count}")
            return count

    async def get_violation_count(self, chat_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.db_name) as conn:
            async with conn.execute("""
                SELECT count FROM violation_counts WHERE chat_id = ? AND user_id = ?
            """, (chat_id, user_id)) as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
                logging.info(f"ℹ️ Получено количество нарушений: chat={chat_id}, user={user_id}, count={count}")
                return count

    async def reset_violations(self, chat_id: int, user_id: int):
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute("DELETE FROM violation_counts WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            await conn.execute("DELETE FROM violations WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
            await conn.commit()
            logging.info(f"✅ Нарушения сброшены: chat={chat_id}, user={user_id}")

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
            logging.info(f"🚫 Бан добавлен: chat={chat_id}, user={user_id}, by={banned_by}, duration={duration}")

    async def get_violations(self, chat_id: int, user_id: int, limit: int = 10):
        """Получить историю нарушений"""
        async with aiosqlite.connect(self.db_name) as conn:
            async with conn.execute("""
                SELECT violation_text, timestamp
                FROM violations
                WHERE chat_id = ? AND user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (chat_id, user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                logging.info(f"ℹ️ Получена история нарушений: chat={chat_id}, user={user_id}, count={len(rows)}")
                return rows

    async def is_banned(self, chat_id: int, user_id: int) -> bool:
        """Проверка, есть ли активный бан"""
        async with aiosqlite.connect(self.db_name) as conn:
            async with conn.execute("""
                SELECT ban_until FROM bans
                WHERE chat_id = ? AND user_id = ?
                ORDER BY banned_at DESC LIMIT 1
            """, (chat_id, user_id)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                if row[0] is None:
                    logging.info(f"🚫 Пользователь {user_id} забанен навсегда")
                    return True
                active = datetime.now() < datetime.fromisoformat(row[0])
                logging.info(f"🚫 Проверка бана: user={user_id}, active={active}")
                return active


db = AsyncDatabase()

