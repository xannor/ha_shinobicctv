"""Shinobi Cameras for Home Assistant"""

import asyncio
import aiohttp
import async_timeout
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_web,
    async_aiohttp_proxy_stream,
    async_get_clientsession,
)
from pyshinobicctvapi.monitors import Monitor
from . import ATTRIBUTION
from homeassistant.const import ATTR_ATTRIBUTION
from .entity import EntityMixin as ShinobiEntityMixin
import logging

from haffmpeg.camera import CameraMjpeg
from haffmpeg.tools import IMAGE_JPEG, ImageFrame

from homeassistant.components.camera import (
    SUPPORT_ON_OFF,
    SUPPORT_STREAM,
    Camera,
    DEFAULT_CONTENT_TYPE,
)
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS, DATA_FFMPEG
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from .const import DOMAIN, CAMERA_WEB_SESSION_TIMEOUT

from pyshinobicctvapi import Client as ShinobiClient
from pyshinobicctvapi.const import STREAM_MJPEG

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
        self._supported_features = 0
        _LOGGER.debug("Initialized: %s" % monitor)

    async def async_added_to_hass(self):
        """ Register callbacks. """
        await super().async_added_to_hass()
        self._still_image_url = self._device.snapshot
        if STREAM_MJPEG in self._device.streams:
            self._stream_mjpeg_source = next(iter(self._device.streams[STREAM_MJPEG]))
        else:
            self._stream_mjpeg_source = None
        self._stream_source = next(iter(self._device.streams), None)
        self._supported_features = SUPPORT_STREAM if self._stream_source else 0
        self._last_image = None

    async def async_will_remove_from_hass(self):
        """ Disconnect callbacks. """
        await super().async_will_remove_from_hass()

    @property
    def name(self):
        """ return the name of this Camera """
        return self._name

    @property
    def supported_features(self):
        """Return supported features for this camera."""
        return self._supported_features

    @property
    def unique_id(self):
        """ Return as unique id. """
        return self._device.id

    def camera_image(self):
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(), self.hass.loop
        ).result()

    async def async_create_still_from_stream(self):
        """ Generate a still image from camera stream using FFMPEG """

        ffmpeg_manager = self.hass.data[DATA_FFMPEG]

        ffmpeg = ImageFrame(ffmpeg_manager.binary)

        if self._stream_source is None:
            return

        if self._stream_mjpeg_source is not None:
            stream_url = self._stream_mjpeg_source.url
        else:
            stream_url = self._stream_source.url

        image = await asyncio.shield(
            ffmpeg.get_image(stream_url, output_format=IMAGE_JPEG)
        )
        return image

    async def async_camera_image(self):
        """Return a still image response from the camera."""
        _LOGGER.debug("Take snapshot from %s", self._name)

        url = self._still_image_url

        if url is None:
            _LOGGER.debug("JPEG API not available, pulling still from stream")
            return await self.async_create_still_from_stream()

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

        return self._stream_source.url

    async def async_create_mjpeg_from_stream(self, request):
        """ Create MJPEG from string"""

        _LOGGER.debug(
            "converting source stream to mjpeg for replay from %s", self._name
        )
        ffmpeg_manager = self.hass.data[DATA_FFMPEG]

        streaming_url = self._stream_source.url
        stream = CameraMjpeg(ffmpeg_manager.binary)
        await stream.open_camera(streaming_url)  # , extra_cmd=self._ffmpeg_arguments)

        try:
            stream_reader = await stream.get_reader()
            return await async_aiohttp_proxy_stream(
                self.hass,
                request,
                stream_reader,
                ffmpeg_manager.ffmpeg_stream_content_type,
            )
        finally:
            _LOGGER.debug("Closing MJPEG stream from %s" % self._name)
            await stream.close()

    async def handle_async_mjpeg_stream(self, request):
        """Return an MJPEG stream."""
        if self._stream_source is None:
            _LOGGER.debug("No source stream falling back to mjpeg snapshots")
            return await super().handle_async_mjpeg_stream(request)

        if self._stream_mjpeg_source is not None:
            _LOGGER.debug("Sending MJPEG stream provided by monitor")
            websession = async_get_clientsession(self.hass)
            streaming_url = self._stream_mjpeg_source.url
            stream_coro = websession.get(
                streaming_url, timeout=CAMERA_WEB_SESSION_TIMEOUT
            )

            return await async_aiohttp_proxy_web(self.hass, request, stream_coro)

        return await self.async_create_mjpeg_from_stream(request)