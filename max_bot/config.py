import os

from era_bot import config as era_config


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


MAX_BOT_TOKEN = _require("MAX_BOT_TOKEN")

MAX_API_URL = os.environ.get("MAX_API_URL", "https://platform-api2.max.ru").rstrip("/")
MAX_CA_BUNDLE = os.environ.get("MAX_CA_BUNDLE")

ERA_CHAT_TYPE = os.environ.get("ERA_MAX_CHAT_TYPE", "max")

MAX_ADMIN_ID = int(os.environ["MAX_ADMIN_ID"]) if os.environ.get("MAX_ADMIN_ID") else None
MAX_SUBSCRIBERS_FILE = os.environ.get("MAX_SUBSCRIBERS_FILE", "max_subscribers.json")
MAX_STATE_FILE = os.environ.get("MAX_STATE_FILE", "max_state.json")

MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024

POLL_TIMEOUT = 30

OUTBOUND_PORT = int(os.environ.get("OUTBOUND_PORT", "8090"))
