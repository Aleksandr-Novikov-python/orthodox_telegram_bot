import asyncio
import logging
import re

from aiogram import Bot
from aiogram.types import Message

from config.settings import BAD_WORDS

async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except Exception as e:
        logging.error(f"Ошибка проверки прав: {e}")
        return False

async def bot_can_restrict(bot: Bot, chat_id: int) -> bool:
    """Проверка прав бота на ограничение пользователей"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        return getattr(bot_member, "can_restrict_members", False)
    except Exception:
        return False

def contains_bad_word(text: str) -> tuple[bool, str]:
    if not text:
        return False, ""
    text_lower = text.lower()
    for word in BAD_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, text_lower):
            return True, word
    return False, ""

async def delete_warning(msg: Message):
    await asyncio.sleep(10)
    try:
        await msg.delete()
        logging.info("Предупреждение удалено")
    except Exception as e:
        logging.warning(f"Не удалось удалить предупреждение: {e}")