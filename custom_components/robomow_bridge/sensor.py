"""Sensor platform for the Robomow HTTP Bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .alarms import stop_reason_code, stop_reason_key
from .coordinator import RobomowCoordinator, parse_number
from .entity import RobomowEntity


@dataclass(frozen=True, kw_only=True)
class RobomowSensorDescription(SensorEntityDescription):
    """Describe one value read from the bridge."""

    source: str
    api_key: str
    numeric: bool = False
    virtual: bool = False


SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="battery",
        translation_key="battery",
        source="renew",
        api_key="0",
        numeric=True,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RobomowSensorDescription(
        key="status",
        translation_key="status",
        source="renew",
        api_key="6",
        icon="mdi:mower",
    ),
    RobomowSensorDescription(
        key="current_zone",
        translation_key="current_zone",
        source="renew",
        api_key="7",
        icon="mdi:texture",
    ),
    RobomowSensorDescription(
        key="next_zone",
        translation_key="next_zone",
        source="renew",
        api_key="8",
        icon="mdi:map-marker-path",
    ),
    RobomowSensorDescription(
        key="dock_proximity",
        translation_key="dock_proximity",
        source="renew",
        api_key="cDSnear",
        icon="mdi:home-import-outline",
    ),
    RobomowSensorDescription(
        key="next_start",
        translation_key="next_start",
        source="renew",
        api_key="5",
        icon="mdi:skip-next-circle-outline",
    ),
    RobomowSensorDescription(
        key="time_left",
        translation_key="time_left",
        source="renew",
        api_key="11",
        icon="mdi:timer-outline",
    ),
    RobomowSensorDescription(
        key="percentage_cut",
        translation_key="percentage_cut",
        source="renew",
        api_key="12",
        numeric=True,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:grass",
    ),
    RobomowSensorDescription(
        key="moisture",
        translation_key="moisture",
        source="renew",
        api_key="13",
        icon="mdi:water-outline",
    ),
    RobomowSensorDescription(
        key="schedule_mode",
        translation_key="schedule_mode",
        source="once",
        api_key="",
        virtual=True,
        icon="mdi:calendar",
    ),
    RobomowSensorDescription(
        key="last_stop_reason",
        translation_key="last_stop_reason",
        source="renew",
        api_key="6",
        icon="mdi:stop-circle-outline",
    ),
    RobomowSensorDescription(
        key="rssi",
        translation_key="rssi",
        source="renew",
        api_key="rssi",
        numeric=True,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    RobomowSensorDescription(
        key="serial_number",
        translation_key="serial_number",
        source="renew",
        api_key="sernr",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator: RobomowCoordinator = entry.runtime_data
    async_add_entities(
        RobomowSensor(coordinator, entry, description) for description in SENSORS
    )


class RobomowSensor(RobomowEntity, SensorEntity):
    """A single value read from the bridge."""

    entity_description: RobomowSensorDescription

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        entry: ConfigEntry,
        description: RobomowSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        description = self.entity_description

        if description.virtual:
            return self.coordinator.schedule_mode

        raw = (self.coordinator.data or {}).get(description.source, {}).get(
            description.api_key
        )
        if raw is None or raw == "":
            return None

        if description.numeric:
            return parse_number(raw)

        if description.key == "last_stop_reason":
            key = stop_reason_key(raw)
            if key is not None:
                return key
            code = stop_reason_code(raw)
            return f"code_{code}" if code is not None else str(raw)

        return str(raw).replace("\\xa0", " ").strip()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the raw text and a parsed duration where useful."""
        if self.entity_description.key != "time_left":
            return None
        raw = (self.coordinator.data or {}).get("renew", {}).get("11")
        if not raw:
            return None
        self._attr_extra_state_attributes = {
            "raw": str(raw).replace("\\xa0", " ").strip(),
            "minutes": _duration_to_minutes(raw),
        }
        return self._attr_extra_state_attributes


def _duration_to_minutes(raw: object) -> int | None:
    """Turn the bridge's '1 Std.  5 Minuten' into a number of minutes."""
    import re

    text = str(raw).replace("\\xa0", " ")
    hours = re.search(r"(\\d+)\\s*Std", text)
    minutes = re.search(r"(\\d+)\\s*Min", text)
    if not hours and not minutes:
        return None
    return int(hours.group(1) if hours else 0) * 60 + int(
        minutes.group(1) if minutes else 0
    )
