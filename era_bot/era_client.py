import base64
from typing import Optional

import aiohttp

from . import config

METHOD_ADD = "MessengersHistoryAPI_ADD"
METHOD_MIGRATE = "MessengersHistoryAPI_MIGRATE"
METHOD_CREATECHAT = "MessengersHistoryAPI_CREATECHAT"

SERVICE_NAME = "telegram-bot"


class EraClientError(Exception):
    pass


def set_service_name(name: str) -> None:
    global SERVICE_NAME
    SERVICE_NAME = name


def build_file_field(file_bytes: Optional[bytes], filename: Optional[str], mime: Optional[str]) -> dict:
    if file_bytes is None:
        return {}
    return {
        "name": filename,
        "mime": mime,
        "size": len(file_bytes),
        "content": base64.b64encode(file_bytes).decode("ascii"),
    }


async def send_log(message: str, message_type: str, method_name: str,
                    operation_kind: str = "OTHER", objectid: Optional[str] = None,
                    objectname: Optional[str] = None) -> None:
    body = {
        "method": "CreateLogMessage",
        "request": {
            "objectid": objectid,
            "objectname": objectname,
            "serviceName": SERVICE_NAME,
            "message": message,
            "messageType": message_type,
            "methodName": method_name,
            "operationKind": operation_kind,
        },
    }
    headers = {"Authorization": f"Bearer {config.ERA_SECRET}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config.ERA_LOG_ENDPOINT, json=body, headers=headers,
                                     timeout=aiohttp.ClientTimeout(total=10)):
                pass
    except (aiohttp.ClientError, TimeoutError):
        pass


async def _invoke(method: str, request: dict) -> dict:
    body = {"method": method, "request": request}
    headers = {"Authorization": f"Bearer {config.ERA_SECRET}"}
    async with aiohttp.ClientSession() as session:
        async with session.post(config.ERA_ENDPOINT, json=body, headers=headers) as resp:
            if resp.status >= 400:
                body_text = await resp.text()
                await send_log(f"{method} HTTP {resp.status}: {body_text[:500]}", "ERROR", method,
                                objectid=str(request.get("chat_id") or ""))
                raise EraClientError(f"Era endpoint returned {resp.status}: {body_text[:500]}")

            data = await resp.json(content_type=None)
            api_response = (data or {}).get("response", {})
            await send_log(
                f"{method}: api_result={api_response.get('api_result')} api_code={api_response.get('api_code')}",
                "INFO" if api_response.get("api_result") == "success" else "ERROR",
                method,
                objectid=str(request.get("chat_id") or ""),
            )
            return api_response


async def send_message(payload: dict, file_bytes: Optional[bytes] = None,
                        filename: Optional[str] = None, mime: Optional[str] = None) -> None:
    request = dict(payload)
    if request.get("username") is None:
        request["username"] = ""
    request["file"] = build_file_field(file_bytes, filename, mime)
    api_response = await _invoke(METHOD_ADD, request)
    if api_response.get("api_result") != "success":
        raise EraClientError(f"{METHOD_ADD} failed: {api_response.get('api_code')} {api_response.get('description')}")


async def send_migrate(payload: dict) -> None:
    api_response = await _invoke(METHOD_MIGRATE, payload)
    if api_response.get("api_result") != "success":
        raise EraClientError(
            f"{METHOD_MIGRATE} failed: {api_response.get('api_code')} {api_response.get('description')}"
        )


async def send_create_chat(name: str, chat_id: str, chat_type: str = "telegram") -> dict:
    return await _invoke(METHOD_CREATECHAT, {"name": name, "chat_id": chat_id, "chat_type": chat_type})
