"""HTTP client for the Robomow bridge."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import BasicAuth, ClientError, ClientResponseError, ClientSession

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


class RobomowApiError(Exception):
    """The bridge could not be reached or returned an error."""


class RobomowAuthError(RobomowApiError):
    """The bridge rejected the supplied credentials."""


class RobomowApi:
    """Wrapper around the bridge's JSON endpoints."""

    def __init__(
        self, session: ClientSession, host: str, username: str, password: str
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._base = f"http://{host.strip().rstrip('/')}"
        self._auth = BasicAuth(username, password)

    async def _get(self, path: str, timeout: int = REQUEST_TIMEOUT) -> Any:
        """Perform a GET request and decode the payload."""
        url = f"{self._base}{path}"
        try:
            async with asyncio.timeout(timeout):
                response = await self._session.get(url, auth=self._auth)
                response.raise_for_status()
                if "json" in response.headers.get("Content-Type", ""):
                    return await response.json(content_type=None)
                text = await response.text()
                try:
                    return json.loads(text)
                except ValueError:
                    return text
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise RobomowAuthError(
                    f"Bridge rejected the credentials ({err.status})"
                ) from err
            raise RobomowApiError(f"Bridge returned HTTP {err.status}") from err
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise RobomowApiError(f"Timeout while calling {path}") from err
        except ClientError as err:
            raise RobomowApiError(str(err)) from err

    async def renew(self) -> dict[str, Any]:
        """Return the live state of the mower."""
        data = await self._get("/renew")
        if not isinstance(data, dict):
            raise RobomowApiError("/renew did not return a JSON object")
        return data

    async def once(self) -> dict[str, Any]:
        """Return the slow-changing settings of the mower."""
        data = await self._get("/once")
        if not isinstance(data, dict):
            raise RobomowApiError("/once did not return a JSON object")
        return data

    async def telemetry(self) -> dict[str, Any]:
        """Return /renewtelem -- a large payload, fetched on demand only."""
        data = await self._get("/renewtelem", timeout=30)
        if not isinstance(data, dict):
            raise RobomowApiError("/renewtelem did not return a JSON object")
        return data

    async def oncemisc(self) -> dict[str, Any]:
        """Return /oncemisc -- a large payload, fetched on demand only."""
        data = await self._get("/oncemisc", timeout=30)
        if not isinstance(data, dict):
            raise RobomowApiError("/oncemisc did not return a JSON object")
        return data

    async def command(self, key: int, value: int) -> None:
        """Send a single command to the bridge."""
        _LOGGER.debug("Sending command %s=%s", key, value)
        await self._get(f"/setcmds?{key}={value}")
