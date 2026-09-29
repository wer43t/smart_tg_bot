import ssl
from typing import Optional

import aiohttp

from . import config


class MaxApiError(Exception):
    pass


def _ssl_context() -> Optional[ssl.SSLContext]:
    if not config.MAX_CA_BUNDLE:
        return None
    return ssl.create_default_context(cafile=config.MAX_CA_BUNDLE)


class MaxApi:
    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "MaxApi":
        connector = aiohttp.TCPConnector(ssl=_ssl_context())
        self._session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._session is not None:
            await self._session.close()

    async def _request(self, method: str, path: str, *, params: Optional[dict] = None,
                        json: Optional[dict] = None, timeout: float = 30) -> dict:
        headers = {"Authorization": config.MAX_BOT_TOKEN}
        url = f"{config.MAX_API_URL}{path}"
        async with self._session.request(method, url, params=params, json=json, headers=headers,
                                          timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status >= 400:
                raise MaxApiError(f"{method} {path} -> {resp.status}: {(await resp.text())[:500]}")
            return await resp.json(content_type=None)

    async def get_me(self) -> dict:
        return await self._request("GET", "/me")

    async def get_updates(self, marker: Optional[int]) -> dict:
        params = {"timeout": config.POLL_TIMEOUT, "limit": 100, "types": "message_created,bot_added,bot_started"}
        if marker is not None:
            params["marker"] = marker
        return await self._request("GET", "/updates", params=params, timeout=config.POLL_TIMEOUT + 15)

    async def get_chat(self, chat_id: int) -> dict:
        return await self._request("GET", f"/chats/{chat_id}")

    async def send_text(self, text: str, *, chat_id: Optional[int] = None, user_id: Optional[int] = None) -> None:
        params = {"chat_id": chat_id} if chat_id is not None else {"user_id": user_id}
        await self._request("POST", "/messages", params=params, json={"text": text})

    async def download(self, url: str, max_size: int) -> Optional[bytes]:
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status >= 400:
                raise MaxApiError(f"download {resp.status}")
            if (resp.content_length or 0) > max_size:
                return None
            data = bytearray()
            async for chunk in resp.content.iter_chunked(64 * 1024):
                data += chunk
                if len(data) > max_size:
                    return None
            return bytes(data)
