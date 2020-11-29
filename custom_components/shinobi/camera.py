"""Shinobi Cameras for Home Assistant"""

import asyncio
import aiohttp
import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyshinobicctvapi.monitors import Monitor
from . import ATTRIBUTION
from homeassistant.const import ATTR_ATTRIBUTION
from .entity import EntityMixin as ShinobiEntityMixin
import logging

from homeassistant.components.camera import Camera, DEFAULT_CONTENT_TYPE
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from .const import DOMAIN

from pyshinobicctvapi import Client as ShinobiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Add cameras for Shinobi"""

    client: ShinobiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    monitors = await client.monitors.async_started()

    cams = []
    for monitor in monitors:
        cams.append(ShinobiCamera(entry.entry_id, monitor))

    async_add_entities(cams)


class ShinobiCamera(ShinobiEntityMixin[Monitor], Camera):
    """An Implementation of a Shinobi Camera """

    def __init__(self, config_entry_id, monitor: Monitor):
        """ Initialize a Shinobi Camera """
        super(ShinobiCamera, self).__init__(config_entry_id, monitor, "monitors")
        self._name = monitor.name
        self._content_type = monitor.type or DEFAULT_CONTENT_TYPE
        _LOGGER.debug("Initialized: %s" % monitor)

    async def async_added_to_hass(self):
        """ Register callbacks. """
        await super().async_added_to_hass()
        self._still_image_url = self._device.snapshot
        self._stream_source = next(iter(self._device.streams), None)
        self._last_image = None

    async def async_will_remove_from_hass(self):
        """ Disconnect callbacks. """
        await super().async_will_remove_from_hass()

    @property
    def name(self):
        """ return the name of this Camera """
        return self._name

    @property
    def unique_id(self):
        """ Return as unique id. """
        return self._device.id

    def camera_image(self):
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(), self.hass.loop
        ).result()

    async def async_camera_image(self):
        """Return a still image response from the camera."""

        url = self._still_image_url

        try:
            websession = async_get_clientsession(self.hass)
            with async_timeout.timeout(10):
                response = await websession.get(url)
            self._last_image = await response.read()
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout getting camera image from %s", self._name)
            return self._last_image
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting new camera image from %s: %s", self._name, err)
            return self._last_image

        return self._last_image

    async def stream_source(self):
        """Return the source of the stream."""
        if self._stream_source is None:
            return None

        return self._stream_source
