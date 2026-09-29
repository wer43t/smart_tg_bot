from datetime import datetime, timezone
from typing import Optional

from era_bot.era_client import EraClientError, send_create_chat, send_message

from . import config
from .api import MaxApi, MaxApiError

_FORWARDED_ATTACHMENTS = {"image", "file"}


async def _try_handle_link_command(api: MaxApi, bot_username: str, chat_id: int, text: str) -> bool:
    if not text.lower().startswith(f"@{bot_username.lower()}"):
        return False

    name = text[len(bot_username) + 1:].strip()
    if not name:
        await api.send_text(f"Использование: @{bot_username} Имя контрагента из Smart", chat_id=chat_id)
        return True

    try:
        api_response = await send_create_chat(name, str(chat_id), config.ERA_CHAT_TYPE)
    except EraClientError:
        await api.send_text("Не удалось связаться с Эрой, попробуйте позже.", chat_id=chat_id)
        return True

    if api_response.get("api_result") == "success":
        await api.send_text(f"Готово: чат привязан к контрагенту «{name}».", chat_id=chat_id)
    else:
        await api.send_text(
            f"Не получилось: {api_response.get('description', api_response.get('api_code'))}", chat_id=chat_id
        )
    return True


def _sender_name(sender: dict) -> Optional[str]:
    name = sender.get("name") or " ".join(p for p in (sender.get("first_name"), sender.get("last_name")) if p)
    return name or None


def _file_info(attachment: dict) -> tuple:
    payload = attachment.get("payload") or {}
    url = payload.get("url")
    if attachment["type"] == "image":
        photo_id = payload.get("photo_id") or "image"
        return url, f"{photo_id}.jpg", "image/jpeg", None
    return url, attachment.get("filename") or "file", "application/octet-stream", attachment.get("size")


async def handle_message(api: MaxApi, bot_username: str, message: dict) -> None:
    recipient = message.get("recipient") or {}
    chat_id = recipient.get("chat_id")
    if chat_id is None or recipient.get("chat_type") == "dialog":
        return

    body = message.get("body") or {}
    text = (body.get("text") or "").strip()

    if text and await _try_handle_link_command(api, bot_username, chat_id, text):
        return

    attachments = [a for a in (body.get("attachments") or []) if a.get("type") in _FORWARDED_ATTACHMENTS]
    if not text and not attachments:
        return

    sender = message.get("sender") or {}
    payload = {
        "chat_id": str(chat_id),
        "chat_type": config.ERA_CHAT_TYPE,
        "sender": str(sender["user_id"]) if sender.get("user_id") is not None else None,
        "sender_name": _sender_name(sender),
        "username": sender.get("username"),
        "message_id": body.get("seq"),
        "timestamp": datetime.fromtimestamp(message["timestamp"] / 1000, tz=timezone.utc).isoformat(),
        "text": text,
    }

    if not attachments:
        await _send(payload)
        return

    for index, attachment in enumerate(attachments):
        item = dict(payload)
        if index:
            item["text"] = ""
        url, filename, mime, size = _file_info(attachment)

        file_bytes = None
        if url and (size or 0) <= config.MAX_FILE_SIZE:
            try:
                file_bytes = await api.download(url, config.MAX_FILE_SIZE)
            except (MaxApiError, OSError):
                file_bytes = None
        if file_bytes is None:
            note = f"[файл {filename} не передан: >{config.MAX_FILE_SIZE // 1024 // 1024}МБ или недоступен]"
            item["text"] = (item["text"] + "\n" + note).strip()
            filename = mime = None
        await _send(item, file_bytes, filename, mime)


async def _send(payload: dict, file_bytes=None, filename=None, mime=None) -> None:
    try:
        await send_message(payload, file_bytes, filename, mime)
    except EraClientError:
        pass
