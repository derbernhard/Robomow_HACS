# Robomow Mähspitzel HTTP Bridge for Home Assistant

Local Home Assistant integration for a Robomow HTTP/BLE bridge exposing
\`/renew\`, \`/once\` and \`/setcmds\`.

Tested with a Robomow MC500.

## Installation

### HACS (custom repository)

1. HACS -> Integrations -> three-dot menu -> **Custom repositories**
2. Add \`https://github.com/derbernhard/Robomow_HACS\` with category **Integration**
3. Install **Robomow HTTP Bridge**, then restart Home Assistant

### Manual

Copy \`custom_components/robomow_bridge\` into \`/config/custom_components/\` and
restart Home Assistant.

## Setup

**Settings -> Devices & services -> Add integration -> Robomow HTTP Bridge**

| Option | Default | Meaning |
| --- | --- | --- |
| Host or IP address | -- | Address of the bridge, e.g. \`192.168.1.160\` |
| Username / Password | -- | Basic-auth credentials of the bridge |
| Polling interval | 300 s | How often \`/renew\` is read |
| Rain sensor | -- | A \`binary_sensor\` that is \`on\` while it rains |
| Drying delay | 120 min | How long it must stay dry before the schedule resumes |
| Send the mower home | on | Also send "go home" when the rain starts |

All settings can be changed later via **Configure** on the integration card.
Credentials are stored by Home Assistant and never written to this repository.

## Entities

| Entity | Source |
| --- | --- |
| \`sensor.robomow_battery\` | \`/renew\` key \`0\` |
| \`sensor.robomow_status\` | \`/renew\` key \`cDSnear\` |
| \`sensor.robomow_current_zone\` | \`/renew\` key \`7\` |
| \`sensor.robomow_stop_reason\` | \`/renew\` key \`6\` |
| \`sensor.robomow_next_activity\` | \`/renew\` key \`8\` |
| \`sensor.robomow_next_start\` | \`/renew\` key \`5\` |
| \`sensor.robomow_time_left\` | \`/renew\` key \`11\` |
| \`sensor.robomow_percentage_cut\` | \`/renew\` key \`12\` |
| \`sensor.robomow_moisture\` | \`/renew\` key \`13\` |
| \`sensor.robomow_rssi\` | \`/renew\` key \`rssi\` (diagnostic, disabled by default) |
| \`sensor.robomow_ble_state\` | \`/renew\` key \`blesw\` (diagnostic, disabled by default) |
| \`switch.robomow_ble\` | \`250=1\` / \`250=0\` |
| \`switch.robomow_weekly_schedule\` | \`50=1\` / \`50=0\` |
| \`binary_sensor.robomow_schedule_disabled_by_rain\` | internal rain state |
| \`button.robomow_mow_edge\` | \`1=1\` |
| \`button.robomow_go_home\` | \`2=1\` |
| \`button.robomow_mow_area\` | \`3=1\` |
| \`button.robomow_stop\` / \`button.robomow_change_zone\` | \`4=1\` |
| \`button.robomow_start\` | \`4=0\` |
| \`button.robomow_forward\` | \`200=1\` |
| \`button.robomow_left\` | \`201=-120\` |
| \`button.robomow_right\` | \`202=35\` |
| \`button.robomow_backward\` | \`203=90\` |

## Rain handling

When the configured rain sensor turns \`on\` the integration brings up the BLE
link, sends the mower home and disables the weekly schedule. Once the sensor has
been \`off\` for the configured drying delay, the schedule is enabled again --
but only if it is still dry at that moment. The suspended state survives a
Home Assistant restart.

## Dashboard card

A ready-made card is in [\`lovelace/robomow-card.yaml\`](lovelace/robomow-card.yaml).
The four driving buttons use [button-card](https://github.com/custom-cards/button-card)
for their hold action; everything else works with built-in cards only.

## Notes

- BLE commands are serialised and the integration waits for the link to come up
  before sending, which avoids commands being silently dropped.
- \`/once\` is only read every tenth polling cycle -- it rarely changes and the
  bridge only has one BLE channel.
