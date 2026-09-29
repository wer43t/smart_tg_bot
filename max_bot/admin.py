from era_bot import subscribers
from era_bot.era_client import send_log

from . import config
from .api import MaxApi


def _parse_command(text: str):
    parts = text.strip().split()
    if not parts or not parts[0].startswith("/"):
        return None, None
    arg = parts[1] if len(parts) > 1 and parts[1].lstrip("-").isdigit() else None
    return parts[0].lower(), int(arg) if arg is not None else None


async def handle_admin_dm(api: MaxApi, message: dict) -> None:
    sender = message.get("sender") or {}
    user_id = sender.get("user_id")
    text = (message.get("body") or {}).get("text") or ""

    if text.strip().lower() == "/start":
        await api.send_text(f"Ваш Max id: {user_id}", user_id=user_id)
        return

    if config.MAX_ADMIN_ID is None or user_id != config.MAX_ADMIN_ID:
        return

    command, arg = _parse_command(text)
    path = config.MAX_SUBSCRIBERS_FILE

    if command == "/add_subscriber":
        if arg is None:
            reply = "Использование: /add_subscriber <max_user_id>"
        else:
            reply = f"{'Добавлен в рассылку' if subscribers.add(arg, path) else 'Уже был в рассылке'}: {arg}"
    elif command == "/remove_subscriber":
        if arg is None:
            reply = "Использование: /remove_subscriber <max_user_id>"
        else:
            reply = f"{'Удалён из рассылки' if subscribers.remove(arg, path) else 'Не найден в рассылке'}: {arg}"
    elif command == "/list_subscribers":
        ids = sorted(subscribers.load(path))
        reply = "Список пуст" if not ids else "\n".join(str(i) for i in ids)
    else:
        return

    await api.send_text(reply, user_id=user_id)


async def handle_bot_started(api: MaxApi, update: dict) -> None:
    user_id = (update.get("user") or {}).get("user_id")
    if user_id is None:
        return
    await api.send_text(f"Ваш Max id: {user_id}", user_id=user_id)


async def handle_bot_added(api: MaxApi, update: dict) -> None:
    chat_id = update.get("chat_id")
    if chat_id is None or update.get("is_channel"):
        return

    try:
        title = (await api.get_chat(chat_id)).get("title")
    except Exception:
        title = None
    text = f"Бот добавлен в новый чат: «{title or chat_id}» (chat_id: {chat_id})"

    for subscriber_id in subscribers.load(config.MAX_SUBSCRIBERS_FILE):
        try:
            await api.send_text(text, user_id=subscriber_id)
        except Exception as e:
            await send_log(
                f"Не удалось отправить уведомление о новом чате подписчику {subscriber_id}: {e}",
                "WARNING",
                "handle_bot_added",
                objectid=str(chat_id),
            )
