import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _derive_log_endpoint(era_endpoint: str) -> str:
    suffix = "/rest/v1/domain/nservices/"
    idx = era_endpoint.find(suffix)
    if idx == -1:
        return era_endpoint
    server_url = era_endpoint[:idx]
    return server_url + suffix + "smart_log.LogService"


BOT_TOKEN = os.environ.get("BOT_TOKEN")

ERA_ENDPOINT = _require("ERA_ENDPOINT")
ERA_SECRET = _require("ERA_SECRET")
ERA_LOG_ENDPOINT = os.environ.get("ERA_LOG_ENDPOINT") or _derive_log_endpoint(ERA_ENDPOINT)

TELEGRAM_PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "753403409"))
SUBSCRIBERS_FILE = os.environ.get("SUBSCRIBERS_FILE", "subscribers.json")

MAX_FILE_SIZE = 20 * 1024 * 1024

OUTBOUND_PORT = int(os.environ.get("OUTBOUND_PORT", "8091"))
OUTBOUND_SECRET = os.environ.get("OUTBOUND_SECRET")
