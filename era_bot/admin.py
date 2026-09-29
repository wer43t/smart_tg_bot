from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from . import config, subscribers
from .era_client import send_log

_JOINED_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}


def _is_admin_dm(update: Update) -> bool:
    msg = update.effective_message
    return bool(msg and msg.chat.type == "private" and msg.from_user and msg.from_user.id == config.ADMIN_ID)


def _parse_id_arg(ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or not ctx.args[0].lstrip("-").isdigit():
        return None
    return int(ctx.args[0])


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if not msg or not msg.from_user:
        return
    await msg.reply_text(f"Ваш Telegram id: {msg.from_user.id}")


async def cmd_add_subscriber(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_dm(update):
        return
    msg = update.effective_message
    chat_id = _parse_id_arg(ctx)
    if chat_id is None:
        await msg.reply_text("Использование: /add_subscriber <telegram_id>")
        return
    added = subscribers.add(chat_id)
    await msg.reply_text(f"{'Добавлен в рассылку' if added else 'Уже был в рассылке'}: {chat_id}")


async def cmd_remove_subscriber(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_dm(update):
        return
    msg = update.effective_message
    chat_id = _parse_id_arg(ctx)
    if chat_id is None:
        await msg.reply_text("Использование: /remove_subscriber <telegram_id>")
        return
    removed = subscribers.remove(chat_id)
    await msg.reply_text(f"{'Удалён из рассылки' if removed else 'Не найден в рассылке'}: {chat_id}")


async def cmd_list_subscribers(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_dm(update):
        return
    msg = update.effective_message
    ids = sorted(subscribers.load())
    await msg.reply_text("Список пуст" if not ids else "\n".join(str(i) for i in ids))


async def handle_bot_added_to_chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cm = update.my_chat_member
    if cm is None:
        return

    old_joined = cm.old_chat_member.status in _JOINED_STATUSES
    new_joined = cm.new_chat_member.status in _JOINED_STATUSES
    if old_joined or not new_joined:
        return

    chat = cm.chat
    text = f"Бот добавлен в новый чат: «{chat.title or chat.id}» (chat_id: {chat.id})"

    for subscriber_id in subscribers.load():
        try:
            await ctx.bot.send_message(chat_id=subscriber_id, text=text)
        except Exception as e:
            await send_log(
                f"Не удалось отправить уведомление о новом чате подписчику {subscriber_id}: {e}",
                "WARNING",
                "handle_bot_added_to_chat",
                objectid=str(chat.id),
            )
