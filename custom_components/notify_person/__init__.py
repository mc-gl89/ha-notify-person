"""The Notify Person integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN, ATTR_MESSAGE, ATTR_TITLE, ATTR_DATA, ATTR_PERSON, ATTR_GROUP
from .storage import NotifyPersonStorage

_LOGGER = logging.getLogger(__name__)

NOTIFY_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_DATA): dict,
})


class NotifyPersonManager:
    """Manages dynamic notify services for persons and groups."""
    
    def __init__(self, hass: HomeAssistant, storage: NotifyPersonStorage) -> None:
        self.hass = hass
        self.storage = storage
        self._registered: set[str] = set()
    
    async def async_setup(self) -> None:
        """Register notify services from storage."""
        await self._register_persons()
        await self._register_groups()
    
    async def _register_persons(self) -> None:
        """Create notify.person_* services."""
        persons = self.storage.get_persons()
        
        for person_id, config in persons.items():
            safe_name = person_id.replace("person.", "").replace("-", "_").replace(" ", "_").lower()
            service_name = f"person_{safe_name}"
            
            async def _send(call: ServiceCall, person_id=person_id, config=config) -> None:
                message = call.data[ATTR_MESSAGE]
                title = call.data.get(ATTR_TITLE, "Home Assistant")
                data = call.data.get(ATTR_DATA, {})
                
                targets = config.get("notify_targets", [])
                if not targets:
                    _LOGGER.warning("No targets for %s", config.get("name", person_id))
                    return
                
                for target in targets:
                    try:
                        await self.hass.services.async_call(
                            "notify",
                            target.replace("notify.", ""),
                            {"message": message, "title": title, "data": data},
                        )
                    except Exception as err:
                        _LOGGER.error("Failed to notify %s: %s", target, err)
            
            self.hass.services.async_register("notify", service_name, _send, schema=NOTIFY_SCHEMA)
            self._registered.add(f"notify.{service_name}")
            _LOGGER.debug("Registered notify.%s", service_name)
    
    async def _register_groups(self) -> None:
        """Create notify.group_* services."""
        groups = self.storage.get_groups()
        
        for group_id, config in groups.items():
            safe_name = group_id.replace("-", "_").replace(" ", "_").lower()
            service_name = f"group_{safe_name}"
            
            async def _send(call: ServiceCall, group_config=config) -> None:
                message = call.data[ATTR_MESSAGE]
                title = call.data.get(ATTR_TITLE, "Home Assistant")
                data = call.data.get(ATTR_DATA, {})
                
                member_names = group_config.get("persons", [])
                if not member_names:
                    return
                
                persons = self.storage.get_persons()
                
                for member_name in member_names:
                    for pid, pconfig in persons.items():
                        if pconfig.get("name") == member_name or pid == member_name:
                            safe = pid.replace("person.", "").replace("-", "_").replace(" ", "_").lower()
                            try:
                                await self.hass.services.async_call(
                                    "notify", f"person_{safe}",
                                    {"message": message, "title": title, "data": data},
                                )
                            except Exception as err:
                                _LOGGER.error("Group notify failed for %s: %s", member_name, err)
                            break
            
            self.hass.services.async_register("notify", service_name, _send, schema=NOTIFY_SCHEMA)
            self._registered.add(f"notify.{service_name}")
            _LOGGER.debug("Registered notify.%s", service_name)
    
    async def async_reload(self) -> None:
        """Reload all services."""
        for service in self._registered:
            _, name = service.split(".", 1)
            self.hass.services.async_remove("notify", name)
        self._registered.clear()
        await self.async_setup()
    
    async def async_cleanup(self) -> None:
        """Remove all services."""
        for service in self._registered:
            _, name = service.split(".", 1)
            self.hass.services.async_remove("notify", name)
        self._registered.clear()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    storage = NotifyPersonStorage(hass)
    await storage.async_load()
    
    # Migrate config entry data
    entry_data = entry.data or {}
    if entry_data.get("persons") and not storage.get_persons():
        for pid, config in entry_data["persons"].items():
            storage.add_person(pid, config)
        if entry_data.get("groups"):
            for gid, config in entry_data["groups"].items():
                storage.add_group(gid, config)
        await storage.async_save()
    
    manager = NotifyPersonManager(hass, storage)
    await manager.async_setup()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "manager": manager,
    }
    
    _LOGGER.info("Notify Person loaded")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if entry_data and (manager := entry_data.get("manager")):
        await manager.async_cleanup()
    return True
