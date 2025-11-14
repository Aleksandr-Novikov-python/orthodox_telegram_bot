import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

BAD_WORDS = {"плохое", "запрещённое", "ругательство"}
violations = {}

@dp.message()
async def filter_messages(message: Message):
    text = message.text.lower()
    if any(bad in text for bad in BAD_WORDS):
        try:
            await message.delete()
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение: {e}")

        user_id = message.from_user.id
        chat_id = message.chat.id
        violations[user_id] = violations.get(user_id, 0) + 1
        count = violations[user_id]

        await message.answer(
            f"⚠️ {message.from_user.full_name}, нарушение #{count}. "
            "После 3 нарушений будет бан."
        )

        if count >= 3:
            try:
                await bot.ban_chat_member(chat_id, user_id)
                await message.answer(
                    f"🚫 Пользователь {message.from_user.full_name} заблокирован."
                )
            except Exception as e:
                logging.error(f"Не удалось забанить: {e}")

async def main():
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

