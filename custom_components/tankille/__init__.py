import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_LATITUDE, CONF_LONGITUDE, \
    CONF_LANGUAGE, CONF_DISTANCE, CONF_DEVICE
from .session import TankilleSession

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    latitude: float = entry.data[CONF_LATITUDE]
    longitude: float = entry.data[CONF_LONGITUDE]
    language: str = entry.data[CONF_LANGUAGE]
    distance: int = entry.data[CONF_DISTANCE]
    device: str = entry.data[CONF_DEVICE]

    async def async_update_data():
        api = TankilleSession(language, device, username, password, latitude, longitude, distance)
        return await hass.async_add_executor_job(api.call_api)

    coord = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=entry.unique_id or DOMAIN,
        update_method=async_update_data,
        update_interval=datetime.timedelta(minutes=DEFAULT_SCAN_INTERVAL),
    )

    await coord.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coord

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_forward_entry_unload(entry, "sensor"):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
