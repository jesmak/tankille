import datetime
import logging
from datetime import (timedelta, datetime)
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.sensor import SensorStateClass, SensorEntity
from homeassistant.const import CURRENCY_EURO
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TankilleDataUpdateCoordinator
from .entity import TankilleCoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)
ATTRIBUTION = "Data provided by tankille.fi"

ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_FUEL_TYPE = "fuel"
ATTR_PRICE = "price"
ATTR_UPDATED = "updated"


async def async_setup_entry(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry,
                            async_add_entities: AddEntitiesCallback):
    coordinator: TankilleDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for station in coordinator.stations.values():
        for price in station["price"]:
            entities.append(TankilleSensor(station, price["tag"], coordinator))

    async_add_entities(entities, update_before_add=True)


class TankilleSensor(TankilleCoordinatorEntity, SensorEntity):
    _attr_attribution = ATTRIBUTION
    _attr_icon = "mdi:gas-station"
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 3

    def __init__(self, station: Any, fuel: str, coordinator: TankilleDataUpdateCoordinator):
        super().__init__(coordinator, station)
        self._station_id = station["_id"]
        self._attr_unique_id = f"tankille_{self._station_id}_{fuel}"
        self._attr_translation_key = fuel

        updated = None
        fuel_price = None
        fuel_type = None

        for price in station["price"]:
            if price["tag"] is fuel:
                updated = datetime.fromisoformat(str(price["updated"])).replace(tzinfo=datetime.now().astimezone().tzinfo)
                fuel_price = f"{price['price']:.3f}"
                fuel_type = fuel
                break

        self._attr_extra_state_attributes = {
            ATTR_LATITUDE: f"{station['location']['coordinates'][1]:.4f}",
            ATTR_LONGITUDE: f"{station['location']['coordinates'][0]:.4f}",
            ATTR_UPDATED: updated,
            ATTR_PRICE: fuel_price,
            ATTR_FUEL_TYPE: fuel_type
        }

    @property
    def native_value(self):
        return self._attr_extra_state_attributes[ATTR_PRICE]
