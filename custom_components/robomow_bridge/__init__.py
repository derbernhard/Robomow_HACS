from homeassistant.const import CONF_HOST,CONF_USERNAME,CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import RobomowApi
from .coordinator import RobomowCoordinator
from .rain import RobomowRainManager
from .const import *
async def async_setup_entry(hass,entry):
    api=RobomowApi(async_get_clientsession(hass),entry.data[CONF_HOST],entry.data[CONF_USERNAME],entry.data[CONF_PASSWORD])
    c=RobomowCoordinator(hass,api,entry.data.get(CONF_SCAN_INTERVAL,DEFAULT_SCAN_INTERVAL)); await c.async_config_entry_first_refresh(); entry.runtime_data=c
    rain=entry.data.get(CONF_RAIN_SENSOR)
    if rain:
        m=RobomowRainManager(hass,c,entry.entry_id,rain,entry.data.get(CONF_DRY_DELAY_MINUTES,DEFAULT_DRY_DELAY_MINUTES)); await m.async_start(); hass.data.setdefault(DATA_RAIN_MANAGERS,{})[entry.entry_id]=m
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS); return True
async def async_unload_entry(hass,entry):
    m=hass.data.get(DATA_RAIN_MANAGERS,{}).pop(entry.entry_id,None)
    if m: await m.async_stop()
    return await hass.config_entries.async_unload_platforms(entry,PLATFORMS)
