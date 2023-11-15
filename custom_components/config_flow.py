import logging
import random
import string

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_LANGUAGE,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_DISTANCE,
    LANGUAGES, CONF_DEVICE, CONF_LABEL,
)
from .session import TankilleException, TankilleSession

_LOGGER = logging.getLogger(__name__)

CONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LABEL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_LANGUAGE): vol.All(cv.string, vol.In(LANGUAGES)),
        vol.Required(CONF_LATITUDE, default=61.0559): cv.latitude,
        vol.Required(CONF_LONGITUDE, default=28.1830): cv.longitude,
        vol.Required(CONF_DISTANCE, default=10000): cv.positive_int,
    }
)

RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_LANGUAGE): vol.All(cv.string, vol.In(LANGUAGES)),
        vol.Required(CONF_LATITUDE): cv.latitude,
        vol.Required(CONF_LONGITUDE): cv.longitude,
        vol.Required(CONF_DISTANCE): cv.positive_int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, any]) -> str:
    try:
        if data is not None and CONF_DEVICE not in data:
            data[CONF_DEVICE] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

        session = TankilleSession(data[CONF_LANGUAGE], data[CONF_DEVICE], data[CONF_USERNAME], data[CONF_PASSWORD],
                                  data[CONF_LATITUDE], data[CONF_LONGITUDE], data[CONF_DISTANCE])
        await hass.async_add_executor_job(session.authenticate)

    except TankilleException:
        raise InvalidAuth

    return data[CONF_LABEL]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=CONFIGURE_SCHEMA)

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info, data=user_input)

        return self.async_show_form(step_id="user", data_schema=CONFIGURE_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, any] = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="init", data_schema=vol.Schema(
                    {
                        vol.Required(CONF_PASSWORD, default=self._config_entry.data.get(CONF_PASSWORD)): cv.string,
                        vol.Required(CONF_LANGUAGE, default=self._config_entry.data.get(CONF_LANGUAGE)): vol.All(
                            cv.string, vol.In(LANGUAGES)),
                        vol.Optional(CONF_LATITUDE, default=self._config_entry.data.get(CONF_LATITUDE)): cv.latitude,
                        vol.Required(CONF_LONGITUDE,
                                     default=self._config_entry.data.get(CONF_LONGITUDE)): cv.longitude,
                        vol.Optional(CONF_DISTANCE,
                                     default=self._config_entry.data.get(CONF_DISTANCE)): cv.positive_int,
                    })
            )

        errors = {}

        try:
            user_input[CONF_USERNAME] = self._config_entry.data[CONF_USERNAME]
            user_input[CONF_LABEL] = self._config_entry.data[CONF_LABEL]
            user_input[CONF_DEVICE] = self._config_entry.data[CONF_DEVICE]
            await validate_input(self.hass, user_input)
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            self.hass.config_entries.async_update_entry(self._config_entry, data=user_input,
                                                        options=self._config_entry.options)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="init", data_schema=RECONFIGURE_SCHEMA, errors=errors)


class InvalidAuth(HomeAssistantError):
    """Error to indicate authentication credentials where invalid"""
