from typing import Generic, TypeVar

from pyshinobicctvapi import Client as ShinobiClient
from pyshinobicctvapi.manager import Manager as GenericManager
from . import ATTRIBUTION
from homeassistant.const import ATTR_ATTRIBUTION
from .const import DEFAULT_BRAND, DOMAIN
from homeassistant.core import callback
from pyshinobicctvapi.entity import Entity as ShinobiEntity

E = TypeVar("E", bound=ShinobiEntity)
T = TypeVar("T", bound="EntityMixin")


class EntityMixin(Generic[E]):
    """ Base class form Shinobi device. """

    def __init__(self, config_entry_id: str, device: E, managerKey: str):
        """ Initialize an entity for Shinobi device. """
        super().__init__()
        self._config_entry_id = config_entry_id
        self._device = device
        self._managerKey = managerKey

    async def async_added_to_hass(self):
        """ Register callbacks. """

        client: ShinobiClient = self.shinobi_objects.get("client")
        manager: GenericManager[E] = getattr(client, self._managerKey)
        device = await manager.async_get((self._device.id))
        self._device = device

    async def async_will_remove_from_hass(self):
        """ Disconnect callbacks. """

    @callback
    def _update_callback(self):
        """ Call update method. """
        self.async_write_ha_state()

    @property
    def shinobi_objects(self) -> dict:
        """ Return the Shinobi API objects. """
        return self.hass.data[DOMAIN][self._config_entry_id]

    @property
    def should_poll(self):
        return False

    @property
    def device_state_attributes(self):
        """ Return the state attributes. """
        return {ATTR_ATTRIBUTION: ATTRIBUTION}

    @property
    def device_info(self):
        """ Return device info. """
        return {
            "identifiers": {(DOMAIN, self._device.group, self._device.id)},
            "name": self._device.name,
            "model": "IP Camera",
            "manufacturer": DEFAULT_BRAND,
        }