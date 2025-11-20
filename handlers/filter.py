import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import Message

from config.settings import MAX_VIOLATIONS, BAN_DURATION
from handlers.helpers import bot_can_restrict, contains_bad_word, delete_warning, is_admin, log_to_admins
from handlers.moderation import db


filter_router = Router()


@filter_router.message(F.chat.type.in_({"group", "supergroup"}))
async def filter_messages(message: Message):
    if not message.text:
        return

    has_bad_word, found_word = contains_bad_word(message.text)
    if not has_bad_word:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    # Если админ нарушил
    if await is_admin(message.bot, chat_id, user_id):
        try:
            await message.delete()
            logging.info(f"Удалено сообщение админа {message.from_user.full_name} со словом '{found_word}'")
            await log_to_admins(
                message.bot,
                f"⚠️ Админ <b>{message.from_user.full_name}</b> написал запрещённое слово <code>{found_word}</code> в чате <b>{message.chat.title}</b>"
            )
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение админа: {e}")
        return

    # Удаляем сообщение обычного пользователя
    try:
        await message.delete()
        logging.info(f"Удалено сообщение пользователя {message.from_user.full_name} со словом '{found_word}'")
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение: {e}")

    count = await db.add_violation(
        chat_id, user_id,
        message.from_user.username or "unknown",
        message.from_user.full_name,
        message.text[:200]
    )

    warning_msg = await message.answer(
        f"⚠️ <b>{message.from_user.full_name}</b>, нарушение #{count}!\n"
        f"📝 Найдено запрещённое слово: <code>{found_word}</code>\n"
        f"🚫 После {MAX_VIOLATIONS} нарушений последует бан.",
        parse_mode="HTML"
    )

    asyncio.create_task(delete_warning(warning_msg))

    # Логируем нарушение
    await log_to_admins(
        message.bot,
        f"⚠️ Нарушение в чате <b>{message.chat.title}</b>\n"
        f"👤 Пользователь: <b>{message.from_user.full_name}</b> (@{message.from_user.username or 'нет'})\n"
        f"📝 Сообщение: <code>{message.text[:200]}</code>\n"
        f"🚫 Найдено слово: <code>{found_word}</code>\n"
        f"📊 Нарушений: {count}/{MAX_VIOLATIONS}"
    )

    # Бан при превышении лимита
    if count >= MAX_VIOLATIONS:
        if not await bot_can_restrict(message.bot, chat_id):
            await message.answer("❌ Бот не имеет прав на блокировку пользователей!")
            return
        try:
            if BAN_DURATION > 0:
                until_date = datetime.now() + timedelta(seconds=BAN_DURATION)
                await message.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
                ban_text = f"на {BAN_DURATION // 3600} ч."
            else:
                await message.bot.ban_chat_member(chat_id, user_id)
                ban_text = "навсегда"

            await db.add_ban(
                chat_id, user_id, message.bot.id,
                f"Превышен лимит нарушений ({MAX_VIOLATIONS})",
                BAN_DURATION
            )
            await db.reset_violations(chat_id, user_id)

            await message.answer(
                f"🚫 <b>{message.from_user.full_name}</b> заблокирован {ban_text}\n"
                f"Причина: превышен лимит нарушений ({MAX_VIOLATIONS})",
                parse_mode="HTML"
            )

            # Логируем успешный бан
            await log_to_admins(
                message.bot,
                f"🚫 Пользователь <b>{message.from_user.full_name}</b> заблокирован {ban_text}\n"
                f"Причина: превышен лимит нарушений ({MAX_VIOLATIONS})\n"
                f"Чат: <b>{message.chat.title}</b>"
            )
        except Exception as e:
            logging.error(f"Не удалось забанить пользователя: {e}")
            await message.answer(f"❌ Ошибка при попытке блокировки: {e}")


