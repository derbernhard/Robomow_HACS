from __future__ import annotations
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import RobomowApi, RobomowApiError
from .const import DOMAIN

class RobomowCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, api: RobomowApi, interval: int) -> None:
        super().__init__(hass, logger=__import__('logging').getLogger(__name__), name=DOMAIN, update_interval=timedelta(seconds=interval))
        self.api = api

    async def _async_update_data(self) -> dict:
        try:
            renew, once = await __import__('asyncio').gather(self.api.renew(), self.api.once())
            return {"renew": renew, "once": once}
        except RobomowApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_command(self, key: int, value: int) -> None:
        await self.api.command(key, value)
        await self.async_request_refresh()

