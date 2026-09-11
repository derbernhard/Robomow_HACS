from homeassistant.components.switch import SwitchEntity
from .entity import RobomowEntity

async def async_setup_entry(hass, entry, async_add_entities):
    c=entry.runtime_data
    async_add_entities([RobomowBleSwitch(c,entry), RobomowScheduleSwitch(c,entry)])

class RobomowBleSwitch(RobomowEntity, SwitchEntity):
    _attr_name="BLE"
    def __init__(self,c,e): super().__init__(c,e,"ble")
    @property
    def is_on(self): return str(self.coordinator.data.get("renew",{}).get("cBLEsw","")).lower() == "lightgreen"
    async def async_turn_on(self, **kwargs): await self.coordinator.async_command(250,1)
    async def async_turn_off(self, **kwargs): await self.coordinator.async_command(250,0)

class RobomowScheduleSwitch(RobomowEntity, SwitchEntity):
    _attr_name="Weekly schedule"
    def __init__(self,c,e): super().__init__(c,e,"weekly_schedule")
    @property
    def is_on(self): return str(self.coordinator.data.get("once",{}).get("50", "0")) == "1"
    async def _ensure_ble(self):
        if str(self.coordinator.data.get("renew",{}).get("cBLEsw","")).lower() != "lightgreen":
            await self.coordinator.api.command(250,1)
    async def async_turn_on(self, **kwargs):
        await self._ensure_ble(); await self.coordinator.async_command(50,1)
    async def async_turn_off(self, **kwargs):
        await self._ensure_ble(); await self.coordinator.async_command(50,0)

