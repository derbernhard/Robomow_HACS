"""Binary sensor platform for the Robomow HTTP Bridge."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_RAIN_MANAGERS
from .coordinator import RobomowCoordinator
from .entity import RobomowEntity
from .rain import RobomowRainManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the rain binary sensor if a rain sensor was configured."""
    manager = hass.data.get(DATA_RAIN_MANAGERS, {}).get(entry.entry_id)
    if manager:
        async_add_entities([RobomowRainDisabled(entry.runtime_data, entry, manager)])


class RobomowRainDisabled(RobomowEntity, BinarySensorEntity):
    """True while the schedule is suspended because of rain."""

    _attr_name = "Schedule disabled by rain"
    _attr_icon = "mdi:weather-pouring"

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        entry: ConfigEntry,
        manager: RobomowRainManager,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, entry, "schedule_disabled_by_rain")
        self._manager = manager
        self._unsub = None

    @property
    def is_on(self) -> bool:
        """Return True while rain suspended the schedule."""
        return self._manager.rain_disabled

    async def async_added_to_hass(self) -> None:
        """Subscribe to the rain manager."""
        await super().async_added_to_hass()
        self._unsub = self._manager.add_listener(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the rain manager."""
        if self._unsub:
            self._unsub()
            self._unsub = None
        await super().async_will_remove_from_hass()
