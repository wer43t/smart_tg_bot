import logging

from telegram import Update
from telegram.ext import Application, ChatMemberHandler, CommandHandler, MessageHandler, filters

from . import config
from .admin import cmd_add_subscriber, cmd_list_subscribers, cmd_remove_subscriber, cmd_start, handle_bot_added_to_chat
from .handlers import handle_message
from .outbound import start_server as start_outbound_server

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.WARNING,
)


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError("Environment variable BOT_TOKEN is required")
    builder = Application.builder().token(config.BOT_TOKEN)
    if config.TELEGRAM_PROXY_URL:
        builder = builder.proxy(config.TELEGRAM_PROXY_URL).get_updates_proxy(config.TELEGRAM_PROXY_URL)
    builder = builder.post_init(start_outbound_server)
    app = builder.build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add_subscriber", cmd_add_subscriber))
    app.add_handler(CommandHandler("remove_subscriber", cmd_remove_subscriber))
    app.add_handler(CommandHandler("list_subscribers", cmd_list_subscribers))
    app.add_handler(ChatMemberHandler(handle_bot_added_to_chat, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    return app


def main() -> None:
    app = build_application()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
