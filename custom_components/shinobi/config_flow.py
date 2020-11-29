"""Config flow to configure Shinobi Integration."""
from enum import unique
import logging
from typing import Dict, Any, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_UNIQUE_ID,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from aiohttp import ClientResponseError

from .const import (
    CONF_GROUP,
    CONF_TOKEN,
    DEFAULT_USERNAME,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
)

from datetime import datetime

from pyshinobicctvapi import Connection as ShinobiConnection
import pyshinobicctvapi.errors as ShinobiErrors

from pyshinobicctvapi.videos import async_all as testConnection
from pyshinobicctvapi.api import (
    async_add as async_create_apiKey,
    DEFAULT as DEFAULT_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistantType, data: dict) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    async with ShinobiConnection(
        data[CONF_HOST],
        data.get(CONF_PORT),
        data.get(CONF_TOKEN),
        data.get(CONF_GROUP),
        async_get_clientsession(hass),
    ) as connection:
        await testConnection(connection, end=datetime(1, 1, 1))
        info = connection.info

    return {
        CONF_HOST: info.host,
        CONF_PORT: info.port,
        CONF_GROUP: info.group,
    }


async def validate_login(hass: HomeAssistantType, data: dict) -> Dict[str, Any]:
    """Validate the login input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    async with ShinobiConnection(
        data[CONF_HOST],
        data.get(CONF_PORT),
        async_get_clientsession(hass),
    ) as connection:
        await connection.login(data[CONF_USERNAME], data.get(CONF_PASSWORD))
        token = await async_create_apiKey(connection, DEFAULT_TOKEN)
        info = connection.info

    return {
        CONF_HOST: info.host,
        CONF_PORT: info.port,
        CONF_TOKEN: token.code,
        CONF_GROUP: info.group,
    }


class ShinobiFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Shinobi config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #    """Get the options flow for this handler."""
    #    return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Optional[ConfigType] = None
    ) -> Dict[str, Any]:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return self._show_user_form()

        if CONF_TOKEN not in user_input or CONF_GROUP not in user_input:
            self._user_input = user_input
            return self._show_login_form()

        try:
            info = await validate_input(self.hass, user_input)
        except ClientResponseError:
            return self._show_user_form({"base": "cannot_connect"})
        except ShinobiErrors.Error:
            return self.async_abort(reason="error")
        except Exception:
            _LOGGER.debug("Exception", exc_info=True)
            return self.async_abort(reason="exception")

        unique_id = user_input.setdefault(
            CONF_UNIQUE_ID,
            f"{info[CONF_HOST]}:{info.get(CONF_PORT, 0)}:{info[CONF_GROUP]}",
        )

        if not CONF_PORT in user_input and CONF_PORT in info:
            user_input[CONF_PORT] = info.get(CONF_PORT)

        if not unique_id:
            _LOGGER.debug("Unable to determine unique id from connection")

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})

        _LOGGER.debug("created: %s " % user_input)
        return self.async_create_entry(title="Shinobi CCTV", data=user_input)

    async def async_step_login(
        self, user_input: Optional[ConfigType] = None
    ) -> Dict[str, Any]:
        """Handle a flow initiated by the login"""
        if user_input is None:
            return self._show_login_form()

        try:
            info = await validate_login(self.hass, {**self._user_input, **user_input})
        except ClientResponseError:
            return self._show_user_form({"base": "cannot_connect"})
        except ShinobiErrors.Unauthorized:
            return self._show_login_form({"base": "invalid_auth"})
        except ShinobiErrors.Error:
            return self.async_abort(reason="error")
        except Exception:
            _LOGGER.debug("Exception", exc_info=True)
            return self.async_abort(reason="exception")

        return await self.async_step_user({**self._user_input, **info})

    async def async_step_2fa(
        self, user_input: Optional[ConfigType] = None
    ) -> Dict[str, Any]:
        """Handle a flow initiated by the 2fa"""

        if user_input is None:
            return self._show_2fa_form()

    def _show_user_form(self, errors: Optional[dict] = None):
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT): int,
                    vol.Optional(CONF_TOKEN): str,
                    vol.Optional(CONF_GROUP): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=60)),
                },
            ),
            errors=errors or {},
        )

    def _show_login_form(self, errors: Optional[dict] = None):
        """" Show the login form to the user. """

        return self.async_show_form(
            step_id="login",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Optional(CONF_PASSWORD): str,
                }
            ),
            errors=errors or {},
        )

    def _show_2fa_form(self, errors: Optional[dict] = None):
        """ Show the two factor prompt to the user. """

        return self.async_show_form(
            step_id="2fa",
            data_schema=vol.Schema({"2fa": str}),
            errors=errors or {},
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    # vol.Optional(
                    #    CONF_LANGUAGE,
                    #    default=self.config_entry.options.get(
                    #        CONF_LANGUAGE, DEFAULT_LANGUAGE
                    #    ),
                    # ): vol.In(SUPPORTED_LANGUAGES),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
        )