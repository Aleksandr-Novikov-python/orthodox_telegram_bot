import asyncio
import logging
import re

from aiogram import Bot
from aiogram.types import Message

from config.settings import BAD_WORDS, ADMIN_LOG_CHAT_ID


async def is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        logging.info(f"🔎 Проверка is_admin: user={user_id}, status={member.status}")
        return member.status in ["creator", "administrator"]
    except Exception as e:
        logging.error(f"Ошибка проверки прав: {e}")
        return False


async def bot_can_restrict(bot: Bot, chat_id: int) -> bool:
    """Проверка прав бота на ограничение пользователей"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        can_restrict = getattr(bot_member, "can_restrict_members", False)
        logging.info(f"🔎 Проверка прав бота: status={bot_member.status}, restrict={can_restrict}")
        return can_restrict
    except Exception as e:
        logging.error(f"Ошибка проверки прав бота: {e}")
        return False


def contains_bad_word(text: str) -> tuple[bool, str]:
    if not text:
        return False, ""
    text_lower = text.lower()
    for word in BAD_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, text_lower):
            logging.info(f"🚫 Найдено запрещённое слово: {word}")
            return True, word
    return False, ""


async def delete_warning(msg: Message):
    await asyncio.sleep(10)
    try:
        await msg.delete()
        logging.info("✅ Предупреждение удалено")
    except Exception as e:
        logging.warning(f"Не удалось удалить предупреждение: {e}")


async def log_to_admins(bot: Bot, text: str, chat_id: int = None, user_id: int = None):
    """Отправка лога в админ-канал"""
    try:
        await bot.send_message(ADMIN_LOG_CHAT_ID, text, parse_mode="HTML")
        logging.info(f"✅ Лог отправлен в админ-канал: {text}")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке лога: {e}")


