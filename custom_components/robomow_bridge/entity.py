from homeassistant.helpers.update_coordinator import CoordinatorEntity
class RobomowEntity(CoordinatorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {("robomow_bridge", entry.unique_id or entry.entry_id)}, "name": "Robomow", "manufacturer": "Robomow", "model": "HTTP/BLE bridge"}

