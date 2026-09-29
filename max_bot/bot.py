import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from era_bot.era_client import send_log, set_service_name

from . import config
from .admin import handle_admin_dm, handle_bot_added, handle_bot_started
from .api import MaxApi, MaxApiError
from .handlers import handle_message
from .outbound import run_server as run_outbound_server

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.WARNING,
)
log = logging.getLogger("max_bot")

SERVICE_NAME = "max-bot"


def _load_marker() -> Optional[int]:
    try:
        return json.loads(Path(config.MAX_STATE_FILE).read_text(encoding="utf-8")).get("marker")
    except (OSError, json.JSONDecodeError):
        return None


def _save_marker(marker: int) -> None:
    Path(config.MAX_STATE_FILE).write_text(json.dumps({"marker": marker}), encoding="utf-8")


async def _dispatch(api: MaxApi, bot_username: str, update: dict) -> None:
    update_type = update.get("update_type")
    if update_type == "bot_added":
        await handle_bot_added(api, update)
    elif update_type == "bot_started":
        await handle_bot_started(api, update)
    elif update_type == "message_created":
        message = update.get("message") or {}
        if (message.get("recipient") or {}).get("chat_type") == "dialog":
            await handle_admin_dm(api, message)
        else:
            await handle_message(api, bot_username, message)


async def _poll_loop(api: MaxApi, bot_username: str) -> None:
    marker = _load_marker()
    backoff = 1

    while True:
        try:
            data = await api.get_updates(marker)
        except (MaxApiError, OSError, asyncio.TimeoutError) as e:
            log.warning("get_updates failed: %s", e)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        backoff = 1

        for update in data.get("updates") or []:
            try:
                await _dispatch(api, bot_username, update)
            except Exception as e:
                log.exception("update handling failed")
                await send_log(f"Ошибка обработки update: {e}", "ERROR", "dispatch")

        if data.get("marker") is not None and data["marker"] != marker:
            marker = data["marker"]
            _save_marker(marker)


async def run() -> None:
    set_service_name(SERVICE_NAME)
    async with MaxApi() as api:
        me = await api.get_me()
        bot_username = me["username"]
        await asyncio.gather(_poll_loop(api, bot_username), run_outbound_server())


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
