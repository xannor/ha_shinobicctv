"""Shinobi Cameras for Home Assistant"""

import logging

from homeassistant.components.camera import CameraEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType
from .const import (
    DOMAIN
)

from pyshinobicctvapi import Client as ShinobiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry, async_add_entities) -> None:
    """Add cameras for Shinobi"""

    client: ShinobiClient = hass.data[DOMAIN][entry.entry_id]["client"]



class ShinobiCamera(CameraEntity):
