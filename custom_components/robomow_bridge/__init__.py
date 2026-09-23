"""The Robomow HTTP Bridge integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RobomowApi
from .const import (
    CONF_DRY_DELAY_MINUTES,
    CONF_RAIN_GO_HOME,
    CONF_RAIN_SENSOR,
    CONF_SCAN_INTERVAL,
    DATA_RAIN_MANAGERS,
    DEFAULT_DRY_DELAY_MINUTES,
    DEFAULT_RAIN_GO_HOME,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import RobomowCoordinator
from .rain import RobomowRainManager

_LOGGER = logging.getLogger(__name__)


def option(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Return an option, falling back to the value stored at setup time."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Robomow HTTP Bridge from a config entry."""
    api = RobomowApi(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = RobomowCoordinator(
        hass, entry, api, option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    rain_entity = option(entry, CONF_RAIN_SENSOR, None)
    if rain_entity:
        manager = RobomowRainManager(
            hass,
            coordinator,
            entry.entry_id,
            rain_entity,
            option(entry, CONF_DRY_DELAY_MINUTES, DEFAULT_DRY_DELAY_MINUTES),
            option(entry, CONF_RAIN_GO_HOME, DEFAULT_RAIN_GO_HOME),
        )
        await manager.async_start()
        hass.data.setdefault(DATA_RAIN_MANAGERS, {})[entry.entry_id] = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    manager = hass.data.get(DATA_RAIN_MANAGERS, {}).pop(entry.entry_id, None)
    if manager:
        await manager.async_stop()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after the options were changed."""
    await hass.config_entries.async_reload(entry.entry_id)
