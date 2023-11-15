import logging

from homeassistant import config_entries, core
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from requests import RequestException

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import TankilleDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coord = TankilleDataUpdateCoordinator(
        hass,
        entry,
        _LOGGER,
        name=entry.unique_id or DOMAIN,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    try:
        setup_ok = await hass.async_add_executor_job(coord.setup)
    except RequestException as err:
        raise ConfigEntryNotReady from err
    if not setup_ok:
        return False

    await coord.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
