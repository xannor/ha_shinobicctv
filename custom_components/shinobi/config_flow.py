"""Config flow to configure Shinobi Integration."""
import logging
from typing import Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_ID,
    CONF_HOST, CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
)

from homeassistant.helpers import aiohttp_client
from homeassistant import config_entries, core
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from voluptuous.schema_builder import Exclusive

from .const import (
    CONF_GROUP, CONF_TOKEN, DEFAULT_USERNAME, DOMAIN,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

class ShinobiFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Shinobi config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        if user_input is None:
            return await self._show_setup_form(user_input)

        errors = {}

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""

        msg = "Please either provide the api_key and group or an email/password login."

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT): int,
                    vol.Exclusive('token', 'auth', msg=msg): {
                        vol.Required(CONF_TOKEN): str,
                        vol.Required(CONF_GROUP): str
                    },
                    vol.Exclusive('login', 'auth', msg=msg): {
                        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                        vol.Required(CONF_PASSWORD): str
                    },
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
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
                    #vol.Optional(
                    #    CONF_LANGUAGE,
                    #    default=self.config_entry.options.get(
                    #        CONF_LANGUAGE, DEFAULT_LANGUAGE
                    #    ),
                    #): vol.In(SUPPORTED_LANGUAGES),
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                }
            ),
        )        