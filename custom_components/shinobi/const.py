"""Constants in Shinobi integration."""
import logging

from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN

DOMAIN = "shinobi"

SHINOBI_PLATFORMS = ["camera"]

CONF_TOKEN = "api_key"
CONF_GROUP = "group"

DEFAULT_BRAND = "Shinobi Systems"
DEFAULT_USERNAME = "admin@shinobi.video"
DEFAULT_SCAN_INTERVAL = 10

CAMERA_WEB_SESSION_TIMEOUT = 10

LOGGER = logging.getLogger(__package__)