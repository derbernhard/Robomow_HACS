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

from .coordinator import RobomowCoordinator
from .entity import RobomowEntity


@dataclass(frozen=True, kw_only=True)
class RobomowSensorDescription(SensorEntityDescription):
    """Describe one value read from the bridge."""

    source: str
    api_key: str
    numeric: bool = False


SENSORS: tuple[RobomowSensorDescription, ...] = (
    RobomowSensorDescription(
        key="battery",
        name="Battery",
        source="renew",
        api_key="0",
        numeric=True,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    RobomowSensorDescription(
        key="status",
        name="Status",
        source="renew",
        api_key="cDSnear",
        icon="mdi:mower",
    ),
    RobomowSensorDescription(
        key="current_zone",
        name="Current zone",
        source="renew",
        api_key="7",
        icon="mdi:texture",
    ),
    RobomowSensorDescription(
        key="stop_reason",
        name="Stop reason",
        source="renew",
        api_key="6",
        icon="mdi:stop-circle-outline",
    ),
    RobomowSensorDescription(
        key="next_activity",
        name="Next activity",
        source="renew",
        api_key="8",
        icon="mdi:calendar-arrow-right",
    ),
    RobomowSensorDescription(
        key="next_start",
        name="Next start",
        source="renew",
        api_key="5",
        icon="mdi:skip-next-circle-outline",
    ),
    RobomowSensorDescription(
        key="time_left",
        name="Time left",
        source="renew",
        api_key="11",
        icon="mdi:timer-outline",
    ),
    RobomowSensorDescription(
        key="percentage_cut",
        name="Percentage cut",
        source="renew",
        api_key="12",
        numeric=True,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:grass",
    ),
    RobomowSensorDescription(
        key="moisture",
        name="Moisture",
        source="renew",
        api_key="13",
        icon="mdi:water-outline",
    ),
    RobomowSensorDescription(
        key="rssi",
        name="RSSI",
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
        key="ble_state",
        name="BLE state",
        source="renew",
        api_key="blesw",
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
        """Return the current value, coerced to a number where required."""
        raw = (
            (self.coordinator.data or {})
            .get(self.entity_description.source, {})
            .get(self.entity_description.api_key)
        )

        if raw is None or raw == "":
            return None

        if not self.entity_description.numeric:
            return raw

        try:
            return float(str(raw).strip().replace("%", "").replace(",", "."))
        except (TypeError, ValueError):
            return None
