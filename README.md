# Robomow HTTP Bridge for Home Assistant

Local custom integration for a Robomow HTTP/BLE bridge exposing `/renew`, `/once`, and `/setcmds`.

## Installation
Copy `custom_components/robomow_bridge` into `/config/custom_components/`, restart Home Assistant, then add **Robomow HTTP Bridge** under Settings > Devices & services.

Do not commit credentials. They are entered in the config flow and stored by Home Assistant.
