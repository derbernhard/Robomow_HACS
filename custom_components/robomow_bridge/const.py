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

# Bridge command keys.
#
# Every entry below is verified against the bridge web UI, not against an old
# rest_command setup -- the two disagree. CMD_SCHEDULE is 56: the UI writes
# /setcmds?56=0 and /setcmds?56=1, while 50 is only a counter that /once
# happens to report under the same number.
CMD_MOW_EDGE = 1
CMD_GO_HOME = 2
CMD_MOW_AREA = 3
CMD_STOP = 4
CMD_SCHEDULE = 56
CMD_FORWARD = 200
CMD_LEFT = 201
CMD_RIGHT = 202
CMD_BACKWARD = 203
CMD_BLE = 250

# /renew keys the integration reads.
KEY_BLE_STATE = "cBLEsw"

# /once key that carries the weekly schedule state, verified on the device:
# "1" while the schedule runs, "0" while it is switched off.
#
# Do NOT read this from /once keys "43" or "50". Both carry the same counter
# value, which is "0", "95", "96", "126" or "127" depending on the last edit
# made in the bridge web UI -- it does not describe the on/off state, and
# "0" occurs both with the schedule running and with it switched off.
KEY_SCHEDULE_STATE = "56"
SCHEDULE_ON_VALUE = "1"

# The bridge needs a moment before a value written via /setcmds shows up in
# /once. Reading too early caches the previous state for a whole /once cycle.
SCHEDULE_SETTLE_SECONDS = 5.0

# /renew key "cBLEsw" reports this value while the BLE link is up.
BLE_ON_VALUE = "lightgreen"

# How long to wait for the BLE link before sending a command that needs it.
BLE_WAIT_SECONDS = 15
