import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from handlers.helpers import is_admin, log_to_admins
from handlers.moderation import db
from config.settings import BAD_WORDS, MAX_VIOLATIONS, BAN_DURATION

admin_router = Router()


@admin_router.message(Command("testlog"))
async def cmd_testlog(message: Message):
    logging.info("⚡ cmd_testlog вызван")
    await log_to_admins(message.bot, "📝 Тестовое сообщение: логирование работает!")
    await message.answer("Сообщение отправлено в канал логов ✅")


# ==================== ADMIN COMMANDS ====================

@admin_router.message(Command("warn"))
async def cmd_warn(message: Message):
    logging.info("⚡ cmd_warn вызван")
    if message.chat.type not in ["group", "supergroup"]:
        logging.warning("Команда /warn вызвана вне группы")
        return

    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        logging.warning(f"Пользователь {message.from_user.id} не админ, отказано в /warn")
        await message.reply("❌ Эта команда доступна только администраторам!")
        return

    if not message.reply_to_message:
        logging.warning("Команда /warn без ответа на сообщение")
        await message.reply("↩️ Ответьте на сообщение пользователя командой /warn")
        return

    target_user = message.reply_to_message.from_user
    if await is_admin(message.bot, message.chat.id, target_user.id):
        logging.warning(f"Попытка выдать предупреждение админу {target_user.id}")
        await message.reply("❌ Нельзя выдать предупреждение администратору!")
        return

    count = await db.add_violation(
        message.chat.id, target_user.id,
        target_user.username or "unknown",
        target_user.full_name,
        "Предупреждение от администратора"
    )

    await message.answer(
        f"⚠️ <b>{target_user.full_name}</b> получил предупреждение!\n"
        f"📊 Всего нарушений: {count}/{MAX_VIOLATIONS}",
        parse_mode="HTML"
    )

    logging.info(f"✅ Предупреждение выдано: {target_user.full_name} ({target_user.id}), count={count}")
    await log_to_admins(
        message.bot,
        f"⚙️ Админ {message.from_user.full_name} выдал предупреждение пользователю {target_user.full_name} в чате {message.chat.title}"
    )


@admin_router.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    logging.info("⚡ cmd_unwarn вызван")
    if message.chat.type not in ["group", "supergroup"]:
        return

    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        logging.warning(f"Пользователь {message.from_user.id} не админ, отказано в /unwarn")
        await message.reply("❌ Эта команда доступна только администраторам!")
        return

    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /unwarn")
        return

    target_user = message.reply_to_message.from_user
    await db.reset_violations(message.chat.id, target_user.id)

    await message.answer(
        f"✅ Все предупреждения сняты с <b>{target_user.full_name}</b>",
        parse_mode="HTML"
    )
    logging.info(f"✅ Предупреждения сняты: {target_user.full_name} ({target_user.id})")


@admin_router.message(Command("warns"))
async def cmd_warns(message: Message):
    logging.info("⚡ cmd_warns вызван")
    if message.chat.type not in ["group", "supergroup"]:
        return

    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    count = await db.get_violation_count(message.chat.id, target_user.id)

    await message.answer(
        f"📊 <b>{target_user.full_name}</b>\n"
        f"Предупреждений: {count}/{MAX_VIOLATIONS}",
        parse_mode="HTML"
    )
    logging.info(f"ℹ️ Проверка предупреждений: {target_user.full_name} ({target_user.id}), count={count}")


@admin_router.message(Command("ban"))
async def cmd_ban(message: Message):
    logging.info("⚡ cmd_ban вызван")
    if message.chat.type not in ["group", "supergroup"]:
        return

    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        logging.warning(f"Пользователь {message.from_user.id} не админ, отказано в /ban")
        await message.reply("❌ Эта команда доступна только администраторам!")
        return

    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /ban")
        return

    target_user = message.reply_to_message.from_user
    if await is_admin(message.bot, message.chat.id, target_user.id):
        logging.warning(f"Попытка забанить администратора {target_user.id}")
        await message.reply("❌ Нельзя забанить администратора!")
        return

    try:
        await message.bot.ban_chat_member(message.chat.id, target_user.id)
        await db.add_ban(
            message.chat.id, target_user.id,
            message.from_user.id, "Бан от администратора", 0
        )
        await message.answer(
            f"🚫 <b>{target_user.full_name}</b> заблокирован",
            parse_mode="HTML"
        )
        logging.info(f"✅ Пользователь забанен: {target_user.full_name} ({target_user.id})")
        await log_to_admins(
            message.bot,
            f"🚫 Админ <b>{message.from_user.full_name}</b> забанил пользователя <b>{target_user.full_name}</b> в чате <b>{message.chat.title}</b>"
        )
    except Exception as e:
        logging.error(f"❌ Ошибка при бане: {e}")
        await message.reply(f"❌ Ошибка: {e}")


@admin_router.message(Command("unban"))
async def cmd_unban(message: Message):
    logging.info("⚡ cmd_unban вызван")
    if message.chat.type not in ["group", "supergroup"]:
        return

    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        logging.warning(f"Пользователь {message.from_user.id} не админ, отказано в /unban")
        await message.reply("❌ Эта команда доступна только администраторам!")
        return

    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /unban")
        return

    target_user = message.reply_to_message.from_user
    try:
        await message.bot.unban_chat_member(message.chat.id, target_user.id)
        await message.answer(
            f"✅ <b>{target_user.full_name}</b> разблокирован",
            parse_mode="HTML"
        )
        logging.info(f"✅ Пользователь разбанен: {target_user.full_name} ({target_user.id})")
        await log_to_admins(
            message.bot,
            f"✅ Админ <b>{message.from_user.full_name}</b> разбанил пользователя <b>{target_user.full_name}</b> в чате <b>{message.chat.title}</b>"
        )
    except Exception as e:
        logging.error(f"❌ Ошибка при разбане: {e}")
        await message.reply(f"❌ Ошибка: {e}")


@admin_router.message(Command("help"))
async def cmd_help(message: Message):
    logging.info("⚡ cmd_help вызван")
    help_text = f"""
🤖 <b>Команды модерационного бота</b>

<b>Для всех:</b>
/warns — показать свои предупреждения
/help — эта справка

<b>Для администраторов:</b>
/warn — выдать предупреждение (ответить на сообщение)
/unwarn — снять предупреждения (ответить на сообщение)
/ban — забанить пользователя (ответить на сообщение)
/unban — разбанить пользователя (ответить на сообщение)

⚙️ <b>Настройки:</b>
• Максимум нарушений: {MAX_VIOLATIONS}
• Длительность бана: {BAN_DURATION // 3600} ч. если BAN_DURATION > 0 else "навсегда"
• Запрещённых слов: {len(BAD_WORDS)}
"""
    await message.answer(help_text, parse_mode="HTML")
    logging.info("✅ Справка отправлена")

