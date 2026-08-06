"""The Notify Person integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .storage import NotifyPersonStorage
from .notify import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize storage
    storage = NotifyPersonStorage(hass)
    await storage.async_load()
    
    # Migrate config entry data to storage if needed
    entry_data = entry.data or {}
    if "persons" in entry_data and not storage.get_persons():
        for person_id, config in entry_data["persons"].items():
            storage.add_person(person_id, config)
        await storage.async_save()
    
    # Store in hass data
    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "config": entry_data,
    }
    
    # Set up services
    await async_setup_services(hass, storage, entry.entry_id)
    
    _LOGGER.info("Notify Person integration loaded for entry %s", entry.entry_id)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove services when last entry is unloaded
        entries = hass.config_entries.async_entries(DOMAIN)
        if len(entries) <= 1:
            await async_unload_services(hass)
        
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok
