"""Switch platform for the Robomow HTTP Bridge."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_BLE, CMD_SCHEDULE
from .coordinator import RobomowCoordinator
from .entity import RobomowEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator: RobomowCoordinator = entry.runtime_data
    async_add_entities(
        [
            RobomowBleSwitch(coordinator, entry),
            RobomowScheduleSwitch(coordinator, entry),
        ]
    )


class RobomowBleSwitch(RobomowEntity, SwitchEntity):
    """Control the BLE link between bridge and mower."""

    _attr_name = "BLE"
    _attr_icon = "mdi:bluetooth"

    def __init__(self, coordinator: RobomowCoordinator, entry: ConfigEntry) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, entry, "ble")

    @property
    def is_on(self) -> bool:
        """Return True when the BLE link is up."""
        return self.coordinator.ble_connected

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Bring the BLE link up."""
        await self.coordinator.async_command(CMD_BLE, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Tear the BLE link down."""
        await self.coordinator.async_command(CMD_BLE, 0)


class RobomowScheduleSwitch(RobomowEntity, SwitchEntity):
    """Enable or disable the mower's weekly schedule."""

    _attr_name = "Weekly schedule"
    _attr_icon = "mdi:calendar"

    def __init__(self, coordinator: RobomowCoordinator, entry: ConfigEntry) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, entry, "weekly_schedule")

    @property
    def is_on(self) -> bool:
        """Return True when the weekly schedule is enabled."""
        return self.coordinator.schedule_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the weekly schedule."""
        await self.coordinator.async_command(CMD_SCHEDULE, 1, require_ble=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the weekly schedule."""
        await self.coordinator.async_command(CMD_SCHEDULE, 0, require_ble=True)
