"""Config and options flow for the Robomow HTTP Bridge."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RobomowApi, RobomowApiError, RobomowAuthError
from .const import (
    CONF_DRY_DELAY_MINUTES,
    CONF_RAIN_GO_HOME,
    CONF_RAIN_SENSOR,
    CONF_SCAN_INTERVAL,
    DEFAULT_DRY_DELAY_MINUTES,
    DEFAULT_RAIN_GO_HOME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

def build_options_schema(current: dict[str, Any]) -> vol.Schema:
    """Build the schema for the options shared by both flows."""
    fields: dict[Any, Any] = {
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
    }

    rain_sensor = current.get(CONF_RAIN_SENSOR)
    rain_key = (
        vol.Optional(CONF_RAIN_SENSOR, default=rain_sensor)
        if rain_sensor
        else vol.Optional(CONF_RAIN_SENSOR)
    )
    fields[rain_key] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="binary_sensor")
    )

    fields[
        vol.Optional(
            CONF_DRY_DELAY_MINUTES,
            default=current.get(CONF_DRY_DELAY_MINUTES, DEFAULT_DRY_DELAY_MINUTES),
        )
    ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=1440))

    fields[
        vol.Optional(
            CONF_RAIN_GO_HOME,
            default=current.get(CONF_RAIN_GO_HOME, DEFAULT_RAIN_GO_HOME),
        )
    ] = selector.BooleanSelector()

    return vol.Schema(fields)

class RobomowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the bridge connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = RobomowApi(
                async_get_clientsession(self.hass),
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await api.renew()
            except RobomowAuthError:
                errors["base"] = "invalid_auth"
            except RobomowApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST].strip().lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Robomow ({user_input[CONF_HOST]})", data=user_input
                )

        base = vol.Schema(
            {
                vol.Required(CONF_HOST): selector.TextSelector(),
                vol.Required(CONF_USERNAME): selector.TextSelector(),
                vol.Required(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
            }
        )
        schema = base.extend(build_options_schema(user_input or {}).schema)
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RobomowOptionsFlow:
        """Return the options flow handler."""
        return RobomowOptionsFlow()

class RobomowOptionsFlow(OptionsFlow):
    """Allow changing the polling and rain settings after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=build_options_schema(current)
        )
