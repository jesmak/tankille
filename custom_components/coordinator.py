from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_USERNAME, CONF_PASSWORD, CONF_LATITUDE, CONF_LONGITUDE, \
    CONF_DISTANCE, CONF_DEVICE, CONF_LANGUAGE
from .session import TankilleSession

_LOGGER = logging.getLogger(__name__)


class TankilleDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(
            self,
            hass: HomeAssistant,
            entry: ConfigEntry,
            logger: logging.Logger,
            name: str,
            update_interval: int,
    ) -> None:
        super().__init__(
            hass=hass,
            logger=logger,
            name=name,
            update_interval=timedelta(minutes=update_interval),
        )

        self._username: str = entry.data[CONF_USERNAME]
        self._password: str = entry.data[CONF_PASSWORD]
        self._latitude: float = entry.data[CONF_LATITUDE]
        self._longitude: float = entry.data[CONF_LONGITUDE]
        self._language: str = entry.data[CONF_LANGUAGE]
        self._distance: int = entry.data[CONF_DISTANCE]
        self._device: str = entry.data[CONF_DEVICE]
        self.stations: dict[str, dict] = {}
        self.session = None

    def setup(self) -> bool:
        self.session = TankilleSession(self._language, self._device, self._username, self._password, self._latitude,
                                       self._longitude, self._distance)
        self.session.authenticate()
        data = self.session.call_api()
        for station in data:
            self.stations[station["_id"]] = station

        return True

    async def _async_update_data(self) -> dict:
        stations = {}
        data = await self.hass.async_add_executor_job(self.session.call_api)
        for station in data:
            stations[station["_id"]] = station

        return stations

