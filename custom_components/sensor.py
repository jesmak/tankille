import datetime
import logging
from datetime import datetime

from homeassistant.components.sensor import SensorStateClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, ATTR_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from .const import DOMAIN, FUEL_TYPES, CONF_IGNORED_CHAINS, CONF_DEVICE, CONF_LABEL, CONF_FUELS, CONF_CHEAPEST_LIMIT

_LOGGER = logging.getLogger(__name__)
ATTRIBUTION = "Data provided by tankille.fi"

ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_FUEL_TYPE = "fuel"
ATTR_PRICE = "price"
ATTR_UPDATED = "updated"
ATTR_STATION = "station"

ATTR_STATION_ = "station_"
ATTR_PRICE_ = "price_"
ATTR_UPDATED_ = "updated_"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    ignored_chains = str(entry.data.get(CONF_IGNORED_CHAINS) if not None else '').lower().split(",")
    fuels = str(entry.data.get(CONF_FUELS) if not None else '').lower().split(",")
    cheapest_limit = entry.data.get(CONF_CHEAPEST_LIMIT) if not None else 0

    cheapest = {}

    for fuel in FUEL_TYPES:
        cheapest[fuel] = []

    for station in coordinator.data:
        if str(station["chain"]).lower() in ignored_chains:
            continue

        device = DeviceInfo(
            identifiers={(ATTR_ID, f"{station['_id']}")},
            name=station["name"],
            model=station["brand"],
            manufacturer=station["chain"],
            configuration_url="https://www.tankille.fi",
            entry_type=DeviceEntryType.SERVICE,
        )

        for fuel_type in station["fuels"]:
            if len(fuels) == 0 or fuel_type in fuels:
                price = next((x for x in station["price"] if x["tag"] == fuel_type), None)
                entities.append(TankilleSensor(coordinator, station, fuel_type, price, device))
                if price is not None:
                    updated = datetime.fromisoformat(str(price["updated"]).removesuffix('Z')).replace(
                        tzinfo=datetime.now().astimezone().tzinfo)
                    if cheapest_limit == 0 or (datetime.now(updated.tzinfo) - updated).total_seconds() < (
                            cheapest_limit * 60):
                        cheapest[fuel_type].append({ATTR_PRICE: price["price"], ATTR_STATION: station["name"],
                                                    ATTR_UPDATED: updated})

    def sort_price(val: dict):
        return val[ATTR_PRICE]

    for fuel_type in FUEL_TYPES:
        if len(fuels) == 0 or fuel_type in fuels:
            cheapest[fuel_type].sort(key=sort_price)
            entities.append(
                CheapestSensor(coordinator, fuel_type,
                               cheapest[fuel_type] if len(cheapest[fuel_type]) < 5 else cheapest[fuel_type][:5],
                               ignored_chains, cheapest_limit))

    async_add_entities(entities)


class TankilleSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, station: dict, fuel_type: str, price: dict,
                 device: DeviceInfo):
        super().__init__(coordinator)
        self._station_id = station["_id"]
        self._fuel_type = fuel_type
        self._attr_attribution = ATTRIBUTION
        self._attr_icon = "mdi:gas-station"
        self._attr_native_unit_of_measurement = CURRENCY_EURO
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 3
        self._attr_unique_id = f"{station['_id']}_{fuel_type}"
        self._attr_translation_key = fuel_type
        self._attr_device_info = device
        self._attr_name = f"{station['name']} {FUEL_TYPES[fuel_type]}"
        self._attr_extra_state_attributes = {
            ATTR_LATITUDE: f"{station['location']['coordinates'][1]:.4f}",
            ATTR_LONGITUDE: f"{station['location']['coordinates'][0]:.4f}",
            ATTR_UPDATED: datetime.fromisoformat(str(price["updated"]).removesuffix('Z')).replace(
                tzinfo=datetime.now().astimezone().tzinfo) if price is not None else None,
            ATTR_PRICE: str(price["price"]) if price is not None else None,
            ATTR_FUEL_TYPE: fuel_type
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        station = next((x for x in self.coordinator.data if x["_id"] == self._station_id), None)
        if station is not None:
            price = next((x for x in station["price"] if x["tag"] == self._fuel_type), None)
            if price is not None:
                self._attr_extra_state_attributes[ATTR_UPDATED] = datetime.fromisoformat(
                    str(price["updated"]).removesuffix('Z')).replace(
                    tzinfo=datetime.now().astimezone().tzinfo)
                self._attr_extra_state_attributes[ATTR_PRICE] = str(price["price"])
            else:
                self._attr_extra_state_attributes[ATTR_UPDATED] = None
                self._attr_extra_state_attributes[ATTR_PRICE] = None
        else:
            self._attr_extra_state_attributes[ATTR_UPDATED] = None
            self._attr_extra_state_attributes[ATTR_PRICE] = None

        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._attr_extra_state_attributes[ATTR_PRICE]


class CheapestSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, fuel_type: str, data: list, ignored_chains: list[str],
                 cheapest_limit: int):
        super().__init__(coordinator)
        self._attr_attribution = ATTRIBUTION
        self._attr_icon = "mdi:currency-eur"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_unique_id = f"{coordinator.config_entry.data[CONF_DEVICE]}_{fuel_type}"
        self._attr_translation_key = fuel_type
        self._attr_name = f"{coordinator.config_entry.data[CONF_LABEL]} {FUEL_TYPES[fuel_type]}"
        self._fuel_type = fuel_type
        self._ignored_chains = ignored_chains
        self._cheapest_limit = cheapest_limit

        attrs = {
            ATTR_FUEL_TYPE: fuel_type
        }

        latest_update = None

        for i in range(5):
            attrs[f"{ATTR_PRICE_}{(i + 1)}"] = str(data[i][ATTR_PRICE]) if len(data) > i and data[i][
                ATTR_PRICE] is not None else None
            attrs[f"{ATTR_UPDATED_}{(i + 1)}"] = data[i][ATTR_UPDATED] if len(data) > i else None
            attrs[f"{ATTR_STATION_}{(i + 1)}"] = data[i][ATTR_STATION] if len(data) > i else None

            if len(data) > i and (latest_update is None or data[i][ATTR_UPDATED] < latest_update):
                latest_update = data[i][ATTR_UPDATED]

        self._latest_update = latest_update.strftime("%s") if latest_update is not None else None
        self._attr_extra_state_attributes = attrs

    @callback
    def _handle_coordinator_update(self) -> None:

        data = []

        for station in self.coordinator.data:
            if str(station["chain"]).lower() in self._ignored_chains:
                continue
            elif self._fuel_type in station["fuels"]:
                price = next((x for x in station["price"] if x["tag"] == self._fuel_type), None)
                if price is not None:
                    updated = datetime.fromisoformat(str(price["updated"]).removesuffix('Z')).replace(
                        tzinfo=datetime.now().astimezone().tzinfo)
                    if self._cheapest_limit == 0 or (datetime.now(updated.tzinfo) - updated).total_seconds() < (
                            self._cheapest_limit * 60):
                        data.append({ATTR_PRICE: str(price["price"]) if price["price"] is not None else None,
                                     ATTR_STATION: station["name"],
                                     ATTR_UPDATED: updated})

        latest_update = None

        def sort_price(val: dict):
            return val[ATTR_PRICE]

        data.sort(key=sort_price)
        for i in range(1, 5):
            if len(data) >= i:
                self._attr_extra_state_attributes[f"{ATTR_PRICE_}{i}"] = data[i - 1][ATTR_PRICE]
                self._attr_extra_state_attributes[f"{ATTR_UPDATED_}{i}"] = data[i - 1][ATTR_UPDATED]
                self._attr_extra_state_attributes[f"{ATTR_STATION_}{i}"] = data[i - 1][ATTR_STATION]

                if latest_update is None or data[i - 1][ATTR_UPDATED] < latest_update:
                    latest_update = data[i - 1][ATTR_UPDATED]
            else:
                self._attr_extra_state_attributes[f"{ATTR_PRICE_}{i}"] = None
                self._attr_extra_state_attributes[f"{ATTR_UPDATED_}{i}"] = None
                self._attr_extra_state_attributes[f"{ATTR_STATION_}{i}"] = None

        self._latest_update = latest_update.strftime("%s") if latest_update is not None else None
        self.async_write_ha_state()

    @property
    def native_value(self):
        return self._latest_update
