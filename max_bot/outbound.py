import logging

from aiohttp import web

from era_bot import config as era_config

from . import config as max_config
from .api import MaxApi

log = logging.getLogger("outbound")


async def _send_max(chat_id: str, text: str) -> None:
    async with MaxApi() as api:
        await api.send_text(text, chat_id=int(chat_id))


async def _handle_send(request: web.Request) -> web.Response:
    if not era_config.OUTBOUND_SECRET or request.headers.get("Authorization") != f"Bearer {era_config.OUTBOUND_SECRET}":
        return web.json_response({"error": "unauthorized"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    chat_type = body.get("chat_type")
    chat_id = body.get("chat_id")
    text = body.get("text")
    if not chat_type or not chat_id or not text:
        return web.json_response({"error": "chat_type, chat_id и text обязательны"}, status=400)

    try:
        if chat_type == "max":
            await _send_max(str(chat_id), text)
        else:
            return web.json_response({"error": f"этот relay не обслуживает chat_type={chat_type}"}, status=400)
    except Exception as e:
        log.exception("outbound send failed: chat_type=%s chat_id=%s", chat_type, chat_id)
        return web.json_response({"error": str(e)}, status=502)

    return web.json_response({"ok": True})


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/send", _handle_send)
    return app


async def run_server() -> None:
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", max_config.OUTBOUND_PORT)
    await site.start()
    log.warning("Outbound relay listening on :%d", max_config.OUTBOUND_PORT)
