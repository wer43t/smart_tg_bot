import logging

from aiohttp import web
from telegram import Bot
from telegram.ext import Application

from . import config

log = logging.getLogger("outbound")


async def _handle_send(request: web.Request) -> web.Response:
    if not config.OUTBOUND_SECRET or request.headers.get("Authorization") != f"Bearer {config.OUTBOUND_SECRET}":
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

    if chat_type != "telegram":
        return web.json_response({"error": f"этот relay не обслуживает chat_type={chat_type}"}, status=400)

    try:
        bot: Bot = request.app["bot"]
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        log.exception("outbound send failed: chat_id=%s", chat_id)
        return web.json_response({"error": str(e)}, status=502)

    return web.json_response({"ok": True})


def build_app(bot: Bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post("/send", _handle_send)
    return app


async def start_server(app: Application) -> None:
    web_app = build_app(app.bot)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.OUTBOUND_PORT)
    await site.start()
    log.warning("Outbound relay listening on :%d", config.OUTBOUND_PORT)
