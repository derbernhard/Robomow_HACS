from __future__ import annotations
import asyncio
from typing import Any
from aiohttp import BasicAuth, ClientError, ClientSession

class RobomowApiError(Exception):
    pass

class RobomowApi:
    def __init__(self, session: ClientSession, host: str, username: str, password: str) -> None:
        self._session = session
        self._base = f"http://{host.strip().rstrip('/')}"
        self._auth = BasicAuth(username, password)

    async def _get(self, path: str) -> Any:
        try:
            async with asyncio.timeout(15):
                response = await self._session.get(f"{self._base}{path}", auth=self._auth)
                response.raise_for_status()
                ctype = response.headers.get("Content-Type", "")
                if "json" in ctype:
                    return await response.json(content_type=None)
                text = await response.text()
                try:
                    import json
                    return json.loads(text)
                except ValueError:
                    return text
        except (TimeoutError, ClientError) as err:
            raise RobomowApiError(str(err)) from err

    async def renew(self) -> dict[str, Any]:
        data = await self._get("/renew")
        if not isinstance(data, dict):
            raise RobomowApiError("/renew did not return a JSON object")
        return data

    async def once(self) -> dict[str, Any]:
        data = await self._get("/once")
        if not isinstance(data, dict):
            raise RobomowApiError("/once did not return a JSON object")
        return data

    async def command(self, key: int, value: int) -> None:
        await self._get(f"/setcmds?{key}={value}")
