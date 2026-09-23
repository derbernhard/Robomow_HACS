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

from .alarms import STOP_REASONS
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
)

_LOGGER = logging.getLogger(__name__)

# German number format: "." thousands separator, "," decimal point.
_THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})+$")


def parse_number(raw: object) -> float | None:
    """Parse the bridge's German-formatted numbers.

    The bridge mixes German formatting into machine values, so float()
    alone would turn "3.357 V" into 3357 V. Three digits after a dot are
    read as a thousands separator, anything else as a decimal point.
    """
    if raw is None:
        return None
    text = str(raw).replace("\xa0", " ").strip()
    if not text:
        return None

    text = re.sub(r"[^0-9.,\-]", "", text)
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
        # Filled only when the user presses the telemetry button.
        self.telemetry: dict[str, Any] = {}
        # Filled only when the user presses the events button.
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

    # ------------------------------------------------------------ state

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
        value = self.renew.get(KEY_BLE_STATE, "")
        return str(value).lower() == BLE_ON_VALUE

    @property
    def schedule_on(self) -> bool:
        """Return True when the weekly schedule is enabled.

        /once key "50" carries the state in bits 4-5, so the value is 96
        when off and 52 / 56 / 60 for daily, 1x and 2x weekly.
        """
        raw = self.once.get(KEY_SCHEDULE, "0")
        try:
            mode = int(str(raw).strip())
        except (TypeError, ValueError):
            return False
        return mode in (52, 56, 60)

    @property
    def schedule_mode(self) -> str:
        """Return the schedule mode as a translation key."""
        raw = self.once.get(KEY_SCHEDULE, "0")
        try:
            mode = int(str(raw).strip())
        except (TypeError, ValueError):
            return "unknown"
        return {
            96: "off",
            52: "daily",
            56: "weekly_1x",
            60: "weekly_2x",
        }.get(mode, "unknown")

    def _publish(self, renew: dict[str, Any]) -> None:
        """Push a freshly fetched /renew payload to the entities."""
        self.async_set_updated_data({"renew": renew, "once": self._once_cache})

    # --------------------------------------------------------- commands

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

    # ------------------------------------------------------ on demand

    async def async_fetch_telemetry(self) -> bool:
        """Fetch /renewtelem once. Never called from the polling cycle."""
        try:
            raw = await self.api.telemetry()
        except RobomowApiError as err:
            _LOGGER.error("Could not fetch telemetry: %s", err)
            return False

        parsed: dict[str, Any] = {}
        for key, value in raw.items():
            parsed[str(key)] = parse_number(value) if str(key).isdigit() else value
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
            date = raw.get(f"m{index + 1}")
            if date is None:
                break
            if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", str(date)):
                break

            reason_raw = str(raw.get(f"m{index + 2}", "")).replace("\xa0", " ").strip()
            code = None
            match = re.match(r"^(\d+)", reason_raw)
            if match:
                code = int(match.group(1))

            events.append(
                {
                    "date": str(date),
                    "time": str(raw.get(f"m{index + 1}", "")),
                    "reason": reason_raw,
                    "reason_key": STOP_REASONS.get(code) if code is not None else None,
                    "code": code,
                    "zone": str(raw.get(f"m{index + 5}", "")),
                    "activity": str(raw.get(f"m{index + 4}", "")),
                    "battery": parse_number(raw.get(f"m{index + 3}")),
                }
            )
            index += 7

        self.events = events
        self.async_update_listeners()
        return True
