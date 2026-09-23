"""Button platform for the Robomow HTTP Bridge."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_BACKWARD,
    CMD_FORWARD,
    CMD_GO_HOME,
    CMD_LEFT,
    CMD_MOW_AREA,
    CMD_MOW_EDGE,
    CMD_RIGHT,
    CMD_STOP,
)
from .coordinator import RobomowCoordinator
from .entity import RobomowEntity

@dataclass(frozen=True, kw_only=True)
class RobomowButtonDescription(ButtonEntityDescription):
    """Describe one button."""

    command: int | None = None
    value: int | None = None
    refresh: bool = True
    on_demand: str | None = None

BUTTONS: tuple[RobomowButtonDescription, ...] = (
    RobomowButtonDescription(
        key="mow_edge",
        translation_key="mow_edge",
        icon="mdi:shape-rectangle-plus",
        command=CMD_MOW_EDGE,
        value=1,
    ),
    RobomowButtonDescription(
        key="mow_area",
        translation_key="mow_area",
        icon="mdi:texture-box",
        command=CMD_MOW_AREA,
        value=1,
    ),
    RobomowButtonDescription(
        key="go_home",
        translation_key="go_home",
        icon="mdi:home-variant-outline",
        command=CMD_GO_HOME,
        value=1,
    ),
    RobomowButtonDescription(
        key="stop",
        translation_key="stop",
        icon="mdi:stop-circle-outline",
        command=CMD_STOP,
        value=1,
    ),
    RobomowButtonDescription(
        key="start",
        translation_key="start",
        icon="mdi:play-circle-outline",
        command=CMD_STOP,
        value=0,
    ),
    RobomowButtonDescription(
        key="change_zone",
        translation_key="change_zone",
        icon="mdi:checkbox-intermediate-variant",
        command=CMD_STOP,
        value=1,
    ),
    # Manual driving -- no refresh after every press, they are used repeatedly.
    RobomowButtonDescription(
        key="forward",
        translation_key="forward",
        icon="mdi:arrow-up-bold-box",
        command=CMD_FORWARD,
        value=1,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="backward",
        translation_key="backward",
        icon="mdi:arrow-down-bold-box",
        command=CMD_BACKWARD,
        value=90,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="left",
        translation_key="left",
        icon="mdi:arrow-left-bold-box",
        command=CMD_LEFT,
        value=-120,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="right",
        translation_key="right",
        icon="mdi:arrow-right-bold-box",
        command=CMD_RIGHT,
        value=35,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    # On-demand payloads -- never fetched by the polling cycle.
    RobomowButtonDescription(
        key="refresh_telemetry",
        translation_key="refresh_telemetry",
        icon="mdi:battery-heart-variant",
        on_demand="telemetry",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    RobomowButtonDescription(
        key="refresh_events",
        translation_key="refresh_events",
        icon="mdi:history",
        on_demand="events",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the buttons."""
    coordinator: RobomowCoordinator = entry.runtime_data
    async_add_entities(
        RobomowButton(coordinator, entry, description) for description in BUTTONS
    )

class RobomowButton(RobomowEntity, ButtonEntity):
    """A single command sent to the bridge."""

    entity_description: RobomowButtonDescription

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        entry: ConfigEntry,
        description: RobomowButtonDescription,
    ) -> None:
        """Initialise the button."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description
        self._lock = asyncio.Lock()

    async def async_press(self) -> None:
        """Run the command, dropping presses while one is in flight."""
        if self._lock.locked():
            return
        async with self._lock:
            description = self.entity_description

            if description.on_demand == "telemetry":
                await self.coordinator.async_fetch_telemetry()
                return
            if description.on_demand == "events":
                await self.coordinator.async_fetch_events()
                return

            if description.command is None or description.value is None:
                return
            await self.coordinator.async_command(
                description.command,
                description.value,
                refresh=description.refresh,
            )
