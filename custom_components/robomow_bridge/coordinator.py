"""Data update coordinator for the Robomow HTTP Bridge."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import RobomowApi, RobomowApiError, RobomowAuthError
from .const import (
    BLE_ON_VALUE,
    BLE_WAIT_SECONDS,
    CMD_BLE,
    DOMAIN,
    KEY_BLE_STATE,
    KEY_SCHEDULE,
    ONCE_EVERY_N_CYCLES,
)

_LOGGER = logging.getLogger(__name__)


class RobomowCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the bridge and serialise commands sent to it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: RobomowApi,
        interval: int,
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api
        self._cycle = 0
        self._once_cache: dict[str, Any] = {}
        self._force_once = False
        self._command_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the current state.

        /renew is read on every cycle, /once only every ONCE_EVERY_N_CYCLES
        cycles -- the bridge talks BLE to the mower and does not like being
        hammered with two parallel requests.
        """
        try:
            renew = await self.api.renew()
            if not self._once_cache or self._cycle % ONCE_EVERY_N_CYCLES == 0:
                self._once_cache = await self.api.once()
            self._cycle += 1
        except RobomowAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RobomowApiError as err:
            raise UpdateFailed(str(err)) from err

        return {"renew": renew, "once": self._once_cache}

    @property
    def ble_connected(self) -> bool:
        """Return True when the bridge reports an active BLE link."""
        value = (self.data or {}).get("renew", {}).get(KEY_BLE_STATE, "")
        return str(value).lower() == BLE_ON_VALUE

    @property
    def schedule_on(self) -> bool:
        """Return True when the weekly schedule is enabled."""
        value = (self.data or {}).get("once", {}).get(KEY_SCHEDULE, "0")
        return str(value) == "1"

    def _publish(self, renew: dict[str, Any]) -> None:
        """Push a freshly fetched /renew payload to the entities."""
        self.async_set_updated_data({"renew": renew, "once": self._once_cache})

    async def async_ensure_ble(self) -> bool:
        """Switch BLE on and wait until the bridge confirms the link."""
        if self.ble_connected:
            return True

        await self.api.command(CMD_BLE, 1)
        for _ in range(BLE_WAIT_SECONDS):
            await asyncio.sleep(1)
            try:
                renew = await self.api.renew()
            except RobomowApiError:
                continue
            if str(renew.get(KEY_BLE_STATE, "")).lower() == BLE_ON_VALUE:
                self._publish(renew)
                return True

        _LOGGER.warning(
            "BLE link not established within %s seconds -- command may be lost",
            BLE_WAIT_SECONDS,
        )
        return False

    async def async_command(
        self,
        key: int,
        value: int,
        *,
        require_ble: bool = False,
        refresh: bool = True,
    ) -> None:
        """Send a command, optionally bringing up BLE first."""
        async with self._command_lock:
            if require_ble:
                await self.async_ensure_ble()
            await self.api.command(key, value)

        if refresh:
            await self.async_refresh()
