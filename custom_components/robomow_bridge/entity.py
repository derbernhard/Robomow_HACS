"""Shared entity base class."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RobomowCoordinator

class RobomowEntity(CoordinatorEntity[RobomowCoordinator]):
    """Base entity tying everything to a single Robomow device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: RobomowCoordinator, entry: ConfigEntry, key: str
    ) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name="Robomow",
            manufacturer="Robomow",
            model="HTTP/BLE bridge",
            configuration_url=f"[{entry.data](http://{entry.data)[CONF_HOST]}",
        )
