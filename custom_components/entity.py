from typing import Any

from homeassistant.const import ATTR_ID
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import TankilleDataUpdateCoordinator


class TankilleCoordinatorEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(
            self, coordinator: TankilleDataUpdateCoordinator, station: Any
    ) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(ATTR_ID, station["_id"])},
            name=station["name"],
            model=station["brand"],
            manufacturer=station["chain"],
            configuration_url="https://www.tankille.fi",
            entry_type=DeviceEntryType.SERVICE,
        )
