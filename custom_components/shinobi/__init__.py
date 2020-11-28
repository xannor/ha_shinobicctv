"""Shinobi Integration for Home Assistant"""
import asyncio
import logging
from datetime import timedelta

import homeassistant.helpers.device_registry as dr
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from aiohttp.client_exceptions import ServerDisconnectedError
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from pyshinobicctvapi import Client as ShinobiClient, Connection as ShinobiConnection

from .const import (
    DOMAIN,
    SHINOBI_PLATFORMS,
    DEFAULT_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_GROUP,
    DEFAULT_BRAND,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up configured Shinobi CCTV."""

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up Shinobi platforms as config entry."""

    if not entry.options:
        hass.config_entries.async_update_entry(
            entry,
            options={
                CONF_SCAN_INTERVAL: entry.data.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            },
        )

    session = async_get_clientsession(hass)
    client = ShinobiClient(
        ShinobiConnection(entry.data[CONF_HOST], entry.data[CONF_PORT], session),
        entry.data[CONF_TOKEN],
        entry.data[CONF_GROUP],
    )
    _LOGGER.debug("Connected to Shinobi CCTV Platform")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"client": client}

    await _async_get_or_create_shinobi_device_in_registry(
        hass, entry, client.connection
    )

    for platform in SHINOBI_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    return True


async def _async_get_or_create_shinobi_device_in_registry(
    hass: HomeAssistantType, entry: ConfigEntry, connection: ShinobiConnection
) -> None:
    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, connection.host)},
        identifiers={(DOMAIN, connection.host)},
        manufacturer=DEFAULT_BRAND,
        name=entry.data[CONF_HOST],
        # model=svr["platform_hw"],
        # sw_version=svr["swversion"],
    )


async def async_update_options(hass: HomeAssistantType, entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Unload Shinobi config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in SHINOBI_PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN][entry.entry_id].client.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok