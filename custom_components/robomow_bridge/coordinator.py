"""Data update coordinator for the Robomow HTTP Bridge."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .alarms import stop_reason_code
from .api import RobomowApi, RobomowApiError, RobomowAuthError
from .const import (
    BLE_ON_VALUE,
    BLE_WAIT_SECONDS,
    CMD_BLE,
    CMD_SCHEDULE,
    DOMAIN,
    KEY_BLE_STATE,
    KEY_SCHEDULE,
    ONCE_EVERY_N_CYCLES,
    SCHEDULE_MODE_KEYS,
)

_LOGGER = logging.getLogger(__name__)

# German number format: "." is the thousands separator, "," the decimal point.
_THOUSANDS = re.compile(r"^\\d{1,3}(\\.\\d{3})+$")


def parse_number(raw: object) -> float | None:
    """Parse the bridge's German-formatted numbers.

    The bridge mixes German formatting into machine values, so a plain
    float() would turn "3.357 V" into 3357 V. Three digits after a dot are
    read as a thousands separator, anything else as a decimal point.
    """
    if raw is None:
        return None

    text = str(raw).replace("\\xa0", " ").strip()
    if not text:
        return None

    text = re.sub(r"[^0-9.,\\-]", "", text)
    if not text:
        return None

    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif "." in text:
        head, _, tail = text.partition(".")
        if len(tail) == 3 and head.isdigit() and not _THOUSANDS.match(text):
            text = head + tail

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


class RobomowCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the bridge, serialise commands and hold on-demand payloads."""

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
        # Filled only when the user presses the corresponding button.
        self.telemetry: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the current state.

        /renew is read on every cycle, /once only every ONCE_EVERY_N_CYCLES
        cycles -- the bridge talks BLE to the mower and does not like being
        hammered. A schedule command sets _force_once so the new state shows
        up immediately.
        """
        try:
            renew = await self.api.renew()
            if (
                self._force_once
                or not self._once_cache
                or self._cycle % ONCE_EVERY_N_CYCLES == 0
            ):
                self._once_cache = await self.api.once()
                self._force_once = False
            self._cycle += 1
        except RobomowAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RobomowApiError as err:
            raise UpdateFailed(str(err)) from err

        return {"renew": renew, "once": self._once_cache}

    # ---------------------------------------------------------------- state

    @property
    def renew(self) -> dict[str, Any]:
        """Return the raw /renew payload."""
        return (self.data or {}).get("renew", {})

    @property
    def once(self) -> dict[str, Any]:
        """Return the cached /once payload."""
        return (self.data or {}).get("once", {})

    @property
    def ble_connected(self) -> bool:
        """Return True when the bridge reports an active BLE link."""
        return str(self.renew.get(KEY_BLE_STATE, "")).lower() == BLE_ON_VALUE

    @property
    def schedule_raw(self) -> int | None:
        """Return the numeric value of /once key "50"."""
        raw = self.once.get(KEY_SCHEDULE, "0")
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            return None

    @property
    def schedule_on(self) -> bool:
        """Return True when the weekly schedule is enabled."""
        return self.schedule_raw in SCHEDULE_MODE_KEYS and self.schedule_raw != 96

    @property
    def schedule_mode(self) -> str:
        """Return the schedule mode as a translation key."""
        raw = self.schedule_raw
        if raw is None:
            return "unknown"
        return SCHEDULE_MODE_KEYS.get(raw, "unknown")

    def _publish(self, renew: dict[str, Any]) -> None:
        """Push a freshly fetched /renew payload to the entities."""
        self.async_set_updated_data({"renew": renew, "once": self._once_cache})

    # ------------------------------------------------------------- commands

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

        if key == CMD_SCHEDULE:
            self._force_once = True

        if refresh:
            await self.async_refresh()

    # ------------------------------------------------------------ on demand

    async def async_fetch_telemetry(self) -> bool:
        """Fetch /renewtelem once. Never called from the polling cycle."""
        try:
            raw = await self.api.telemetry()
        except RobomowApiError as err:
            _LOGGER.error("Could not fetch telemetry: %s", err)
            return False

        parsed: dict[str, Any] = {}
        for key, value in raw.items():
            key = str(key)
            parsed[key] = parse_number(value) if key.isdigit() else value
        self.telemetry = parsed
        self.async_update_listeners()
        return True

    async def async_fetch_events(self) -> bool:
        """Fetch /oncemisc once and keep the event list. On demand only."""
        try:
            raw = await self.api.oncemisc()
        except RobomowApiError as err:
            _LOGGER.error("Could not fetch events: %s", err)
            return False

        events: list[dict[str, Any]] = []
        index = 0
        while True:
            if f"m{index + 1}" not in raw:
                break

            reason_raw = str(raw.get(f"m{index + 2}", "")).replace("\\xa0", " ").strip()
            date = str(raw.get(f"m{index + 1}", "")).strip()
            if not re.match(r"^\\d{2}\\.\\d{2}\\.\\d{4}$", date):
                break

            events.append(
                {
                    "date": date,
                    "time": str(raw.get(f"m{index}", "")).strip(),
                    "reason": reason_raw,
                    "code": stop_reason_code(reason_raw),
                    "activity": str(raw.get(f"m{index + 4}", "")).replace("\\xa0", " ").strip(),
                    "zone": str(raw.get(f"m{index + 5}", "")).strip(),
                    "battery": parse_number(raw.get(f"m{index + 3}")),
                }
            )
            index += 7

            if len(events) >= 10:
                break

        self.events = events
        self.async_update_listeners()
        return True
