from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import CONF_RAIN_SENSOR,DATA_RAIN_MANAGERS
from .entity import RobomowEntity
async def async_setup_entry(hass,entry,add):
    m=hass.data.get(DATA_RAIN_MANAGERS,{}).get(entry.entry_id)
    if m:add([RainDisabled(entry.runtime_data,entry,m)])
class RainDisabled(RobomowEntity,BinarySensorEntity):
    _attr_name='Schedule disabled by rain'
    _attr_icon='mdi:weather-pouring'
    def __init__(self,c,e,m):super().__init__(c,e,'schedule_disabled_by_rain');self.m=m;self._unsub=None
    @property
    def is_on(self):return self.m.rain_disabled
    async def async_added_to_hass(self):
        await super().async_added_to_hass();self._unsub=self.m.add_listener(self.async_write_ha_state)
    async def async_will_remove_from_hass(self):
        if self._unsub:self._unsub()
        await super().async_will_remove_from_hass()
