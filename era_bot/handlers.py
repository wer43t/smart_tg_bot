from telegram import Update
from telegram.ext import ContextTypes

from . import config
from .era_client import EraClientError, send_create_chat, send_message, send_migrate


async def _try_handle_link_command(msg, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    text = (msg.text or "").strip()
    bot_username = ctx.bot.username or ""
    if not bot_username or not text.lower().startswith(f"@{bot_username.lower()}"):
        return False

    name = text[len(bot_username) + 1:].strip()
    if not name:
        await ctx.bot.send_message(
            chat_id=msg.chat_id,
            text=f"Использование: @{bot_username} Имя контрагента из Smart",
        )
        return True

    try:
        api_response = await send_create_chat(name, str(msg.chat_id))
    except EraClientError:
        await ctx.bot.send_message(chat_id=msg.chat_id, text="Не удалось связаться с Эрой, попробуйте позже.")
        return True

    if api_response.get("api_result") == "success":
        await ctx.bot.send_message(chat_id=msg.chat_id, text=f"Готово: чат привязан к контрагенту «{name}».")
    else:
        await ctx.bot.send_message(
            chat_id=msg.chat_id,
            text=f"Не получилось: {api_response.get('description', api_response.get('api_code'))}",
        )
    return True


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return

    if msg.chat.type == "private":
        return

    if msg.text and await _try_handle_link_command(msg, ctx):
        return

    if msg.migrate_to_chat_id:
        migrate_request = {
            "chat_id": str(msg.chat_id),
            "chat_type": "telegram",
            "migrate_to_chat_id": str(msg.migrate_to_chat_id),
        }
        try:
            await send_migrate(migrate_request)
        except EraClientError:
            pass
        return

    if msg.voice or msg.audio or msg.video_note:
        return

    text = msg.text or msg.caption or ""
    payload = {
        "chat_id": str(msg.chat_id),
        "chat_type": "telegram",
        "sender": str(msg.from_user.id) if msg.from_user else None,
        "sender_name": msg.from_user.full_name if msg.from_user else None,
        "username": msg.from_user.username if msg.from_user else None,
        "message_id": msg.message_id,
        "timestamp": msg.date.isoformat(),
        "text": text,
    }

    tg_file = None
    filename = None
    mime = None

    if msg.photo:
        largest = msg.photo[-1]
        tg_file = await largest.get_file()
        filename = f"{largest.file_unique_id}.jpg"
        mime = "image/jpeg"
    elif msg.document:
        tg_file = await msg.document.get_file()
        filename = msg.document.file_name or msg.document.file_unique_id
        mime = msg.document.mime_type or "application/octet-stream"
    elif not text:
        return

    file_bytes = None
    if tg_file is not None:
        if (tg_file.file_size or 0) > config.MAX_FILE_SIZE:
            payload["text"] = (text + "\n[файл >20МБ пропущен]").strip()
        else:
            file_bytes = bytes(await tg_file.download_as_bytearray())

    try:
        await send_message(payload, file_bytes, filename, mime)
    except EraClientError:
        pass
