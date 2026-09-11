import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST,CONF_USERNAME,CONF_PASSWORD
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import RobomowApi,RobomowApiError
from .const import *
class RobomowConfigFlow(config_entries.ConfigFlow,domain=DOMAIN):
    VERSION=1
    async def async_step_user(self,user_input=None):
        errors={}
        if user_input:
            try: await RobomowApi(async_get_clientsession(self.hass),user_input[CONF_HOST],user_input[CONF_USERNAME],user_input[CONF_PASSWORD]).renew()
            except RobomowApiError: errors['base']='cannot_connect'
            else:
                await self.async_set_unique_id(user_input[CONF_HOST].lower()); self._abort_if_unique_id_configured(); return self.async_create_entry(title=f"Robomow ({user_input[CONF_HOST]})",data=user_input)
        return self.async_show_form(step_id='user',data_schema=vol.Schema({vol.Required(CONF_HOST):str,vol.Required(CONF_USERNAME):str,vol.Required(CONF_PASSWORD):str,vol.Optional(CONF_SCAN_INTERVAL,default=DEFAULT_SCAN_INTERVAL):vol.All(vol.Coerce(int),vol.Range(min=5,max=3600)),vol.Optional(CONF_RAIN_SENSOR):selector.EntitySelector(selector.EntitySelectorConfig(domain='binary_sensor')),vol.Optional(CONF_DRY_DELAY_MINUTES,default=DEFAULT_DRY_DELAY_MINUTES):vol.All(vol.Coerce(int),vol.Range(min=0,max=1440))}),errors=errors)
