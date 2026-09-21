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
    """Describe one command button."""

    command: int
    value: int
    refresh: bool = True


BUTTONS: tuple[RobomowButtonDescription, ...] = (
    RobomowButtonDescription(
        key="mow_edge",
        name="Mow edge",
        icon="mdi:shape-rectangle-plus",
        command=CMD_MOW_EDGE,
        value=1,
    ),
    RobomowButtonDescription(
        key="mow_area",
        name="Mow area",
        icon="mdi:texture-box",
        command=CMD_MOW_AREA,
        value=1,
    ),
    RobomowButtonDescription(
        key="go_home",
        name="Go home",
        icon="mdi:home-variant-outline",
        command=CMD_GO_HOME,
        value=1,
    ),
    RobomowButtonDescription(
        key="stop",
        name="Stop",
        icon="mdi:stop-circle-outline",
        command=CMD_STOP,
        value=1,
    ),
    RobomowButtonDescription(
        key="start",
        name="Start",
        icon="mdi:play-circle-outline",
        command=CMD_STOP,
        value=0,
    ),
    RobomowButtonDescription(
        key="change_zone",
        name="Change zone",
        icon="mdi:checkbox-intermediate-variant",
        command=CMD_STOP,
        value=1,
    ),
    # Manual driving -- no refresh after every press, they are used repeatedly.
    RobomowButtonDescription(
        key="forward",
        name="Forward",
        icon="mdi:arrow-up-bold-box",
        command=CMD_FORWARD,
        value=1,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="backward",
        name="Backward",
        icon="mdi:arrow-down-bold-box",
        command=CMD_BACKWARD,
        value=90,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="left",
        name="Left",
        icon="mdi:arrow-left-bold-box",
        command=CMD_LEFT,
        value=-120,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
    ),
    RobomowButtonDescription(
        key="right",
        name="Right",
        icon="mdi:arrow-right-bold-box",
        command=CMD_RIGHT,
        value=35,
        refresh=False,
        entity_category=EntityCategory.CONFIG,
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
        """Send the command, dropping presses while one is in flight."""
        if self._lock.locked():
            return
        async with self._lock:
            await self.coordinator.async_command(
                self.entity_description.command,
                self.entity_description.value,
                refresh=self.entity_description.refresh,
            )
