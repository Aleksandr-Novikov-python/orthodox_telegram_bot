
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from handlers.helpers import is_admin
from handlers.moderation import db
from config.settings import BAD_WORDS, MAX_VIOLATIONS, BAN_DURATION

admin_router = Router()

# ==================== ADMIN COMMANDS ====================
@admin_router.message(Command("warn"))
async def cmd_warn(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ Эта команда доступна только администраторам!")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /warn")
        return

    target_user = message.reply_to_message.from_user
    if await is_admin(message.chat.id, target_user.id):
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

@admin_router.message(Command("unwarn"))
async def cmd_unwarn(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
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

@admin_router.message(Command("warns"))
async def cmd_warns(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    count = await db.get_violation_count(message.chat.id, target_user.id)

    await message.answer(
        f"📊 <b>{target_user.full_name}</b>\n"
        f"Предупреждений: {count}/{MAX_VIOLATIONS}",
        parse_mode="HTML"
    )

@admin_router.message(Command("ban"))
async def cmd_ban(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply("❌ Эта команда доступна только администраторам!")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /ban")
        return

    target_user = message.reply_to_message.from_user
    if await is_admin(message.bot, message.chat.id, target_user.id):
        await message.reply("❌ Нельзя забанить администратора!")
        return

    try:
        await message.bot.ban_chat_member(message.bot, message.chat.id, target_user.id)
        await db.add_ban(
            message.chat.id, target_user.id,
            message.from_user.id, "Бан от администратора", 0
        )
        await message.answer(
            f"🚫 <b>{target_user.full_name}</b> заблокирован",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("unban"))
async def cmd_unban(message: Message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    if not await is_admin(message.bot, message.chat.id, message.from_user.id):
        await message.reply("❌ Эта команда доступна только администраторам!")
        return
    if not message.reply_to_message:
        await message.reply("↩️ Ответьте на сообщение пользователя командой /unban")
        return

    target_user = message.reply_to_message.from_user
    try:
        await message.bot.unban_chat_member(message.bot, message.chat.id, target_user.id)
        await message.answer(
            f"✅ <b>{target_user.full_name}</b> разблокирован",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@admin_router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
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
• Максимум нарушений: {max_violations}
• Длительность бана: {ban_duration}
• Запрещённых слов: {bad_words_count}
""".format(
        max_violations=MAX_VIOLATIONS,
        ban_duration=f"{BAN_DURATION // 3600} ч." if BAN_DURATION > 0 else "навсегда",
        bad_words_count=len(BAD_WORDS)
    )
    await message.answer(help_text, parse_mode="HTML")