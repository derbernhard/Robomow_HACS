from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from .entity import RobomowEntity

@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    source: str
    api_key: str

DESCS = (
    Desc(key="battery", name="Battery", source="renew", api_key="0", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY),
    Desc(key="next_start", name="Next start", source="renew", api_key="5"),
    Desc(key="status", name="Status", source="renew", api_key="6"),
    Desc(key="actual", name="Current activity", source="renew", api_key="7"),
    Desc(key="next", name="Next activity", source="renew", api_key="8"),
    Desc(key="time_left", name="Time left", source="renew", api_key="11"),
    Desc(key="percentage_cut", name="Percentage cut", source="renew", api_key="12", native_unit_of_measurement=PERCENTAGE),
    Desc(key="moisture", name="Moisture", source="renew", api_key="13"),
    Desc(key="dock_near", name="Dock proximity", source="renew", api_key="cDSnear"),
    Desc(key="rssi", name="RSSI", source="renew", api_key="rssi", native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT, device_class=SensorDeviceClass.SIGNAL_STRENGTH),
)
async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([RobomowSensor(entry.runtime_data, entry, d) for d in DESCS])
class RobomowSensor(RobomowEntity, SensorEntity):
    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator, entry, description.key); self.entity_description=description
    @property
    def native_value(self):
        value=self.coordinator.data.get(self.entity_description.source, {}).get(self.entity_description.api_key)
        return value

