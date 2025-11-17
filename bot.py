import logging
import asyncio

from aiogram import Bot, Dispatcher, F

from handlers.filter import filter_router
from handlers.admin import admin_router
from handlers.moderation import db

from config.config import API_TOKEN

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ==================== BOT INIT ====================
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

dp.include_router(filter_router)
dp.include_router(admin_router)

# ==================== MAIN ====================
async def main():
    logging.info("🛠️ Инициализация БД...")
    await db.init_db()
    logging.info("🚀 Старт поллинга...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
