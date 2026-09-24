"""Rain handling: send the mower home and suspend its weekly schedule."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store

from .api import RobomowApiError
from .const import CMD_GO_HOME, CMD_SCHEDULE
from .coordinator import RobomowCoordinator

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
STORE_KEY_PREFIX = "robomow_bridge_rain_"

class RobomowRainManager:
    """Replicate the rain automations: go home + schedule off, re-enable when dry."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: RobomowCoordinator,
        entry_id: str,
        entity_id: str,
        dry_delay_minutes: int,
        go_home: bool = True,
    ) -> None:
        """Initialise the manager."""
        self.hass = hass
        self.coordinator = coordinator
        self.entity_id = entity_id
        self.dry_delay_seconds = max(0, dry_delay_minutes) * 60
        self.go_home = go_home
        self.rain_disabled = False

        self._listeners: list[Callable[[], None]] = []
        self._callbacks: list[Callable[[], None]] = []
        self._cancel_timer: Callable[[], None] | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass, STORE_VERSION, f"{STORE_KEY_PREFIX}{entry_id}"
        )

    async def async_start(self) -> None:
        """Restore the saved state and start watching the rain sensor."""
        saved = await self._store.async_load() or {}
        self.rain_disabled = bool(saved.get("rain_disabled", False))

        self._listeners.append(
            async_track_state_change_event(
                self.hass, [self.entity_id], self._state_changed
            )
        )

        state = self.hass.states.get(self.entity_id)
        if state is None:
            return
        if state.state == STATE_ON:
            await self._handle_wet()
        elif state.state == STATE_OFF and self.rain_disabled:
            self._schedule_dry()

    async def async_stop(self) -> None:
        """Stop watching and cancel any pending timer."""
        for unsub in self._listeners:
            unsub()
        self._listeners.clear()
        self._cancel_dry_timer()

    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback fired whenever the rain flag changes."""
        self._callbacks.append(callback)

        def remove() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return remove

    async def _set_flag(self, value: bool) -> None:
        """Persist the rain flag and notify listeners."""
        if self.rain_disabled == value:
            return
        self.rain_disabled = value
        await self._store.async_save({"rain_disabled": value})
        for callback in list(self._callbacks):
            callback()

    def _schedule_dry(self) -> None:
        """Start the drying timer."""
        self._cancel_dry_timer()
        if self.dry_delay_seconds == 0:
            self.hass.async_create_task(self._enable_if_still_dry())
        else:
            self._cancel_timer = async_call_later(
                self.hass, self.dry_delay_seconds, self._dry_timer_finished
            )

    def _cancel_dry_timer(self) -> None:
        """Cancel a pending drying timer."""
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None

    async def _state_changed(self, event: Event) -> None:
        """React to the rain sensor changing state."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        if new_state.state == STATE_ON:
            await self._handle_wet()
        elif new_state.state == STATE_OFF and self.rain_disabled:
            self._schedule_dry()

    async def _handle_wet(self) -> None:
        """It started raining: send the mower home and suspend the schedule.

        The command is sent unconditionally. 0 is a valid value for "schedule
        off" whether or not the schedule was running, and making the command
        depend on a state reading has silently skipped it in the past -- the
        bridge reports the schedule state in /once key "56", and a stale or
        missing value must never stop the mower from being parked.
        """
        self._cancel_dry_timer()
        try:
            if self.go_home:
                await self.coordinator.async_command(
                    CMD_GO_HOME, 1, require_ble=True, refresh=False
                )
            await self.coordinator.async_command(CMD_SCHEDULE, 0, require_ble=True)
        except RobomowApiError as err:
            _LOGGER.error("Could not react to rain: %s", err)
            return
        await self._set_flag(True)

    async def _dry_timer_finished(self, _now: Any) -> None:
        """The drying delay elapsed."""
        self._cancel_timer = None
        await self._enable_if_still_dry()

    async def _enable_if_still_dry(self) -> None:
        """Re-enable the schedule, but only if it is still dry."""
        if not self.rain_disabled:
            return
        if not self.hass.states.is_state(self.entity_id, STATE_OFF):
            return
        try:
            await self.coordinator.async_command(CMD_SCHEDULE, 1, require_ble=True)
        except RobomowApiError as err:
            _LOGGER.error("Could not re-enable the schedule: %s", err)
            return
        await self._set_flag(False)
