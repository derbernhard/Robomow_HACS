"""Constants for the Robomow HTTP Bridge integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "robomow_bridge"

CONF_SCAN_INTERVAL = "scan_interval"
CONF_RAIN_SENSOR = "rain_sensor"
CONF_DRY_DELAY_MINUTES = "dry_delay_minutes"
CONF_RAIN_GO_HOME = "rain_go_home"

DEFAULT_SCAN_INTERVAL = 300
DEFAULT_DRY_DELAY_MINUTES = 120
DEFAULT_RAIN_GO_HOME = True

# /once changes rarely -- only poll it every Nth coordinator cycle.
ONCE_EVERY_N_CYCLES = 10

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]

DATA_RAIN_MANAGERS = "robomow_bridge_rain_managers"

# Bridge command keys (verified against the rest_command setup they replace).
CMD_MOW_EDGE = 1
CMD_GO_HOME = 2
CMD_MOW_AREA = 3
CMD_STOP = 4
CMD_SCHEDULE = 50
CMD_FORWARD = 200
CMD_LEFT = 201
CMD_RIGHT = 202
CMD_BACKWARD = 203
CMD_BLE = 250

KEY_BLE_STATE = "cBLEsw"
KEY_SCHEDULE = "50"

# How long to wait for the BLE link before sending a command that needs it.
BLE_WAIT_SECONDS = 15
