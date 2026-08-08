"""The Notify Person integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    ATTR_MESSAGE,
    ATTR_TITLE,
    ATTR_DATA,
    ATTR_PERSON,
    ATTR_GROUP,
    CONF_CHANNEL,
    CONF_PRIORITY,
    CONF_CRITICAL,
    CONF_TAG,
    CONF_ACTIONS,
    CONF_PERSISTENT,
    SERVICE_SIMPLE_NOTIFY,
    SERVICE_ADVANCED_NOTIFY,
)
from .storage import NotifyPersonStorage

_LOGGER = logging.getLogger(__name__)

# Schema for simple_notify
SIMPLE_NOTIFY_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON): cv.string,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
})

# Schema for advanced_notify
ADVANCED_NOTIFY_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON): cv.string,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
    vol.Optional(CONF_CHANNEL): cv.string,
    vol.Optional(CONF_PRIORITY, default="normal"): vol.In(["normal", "high", "low"]),
    vol.Optional(CONF_CRITICAL, default=False): cv.boolean,
    vol.Optional(CONF_TAG): cv.string,
    vol.Optional(CONF_ACTIONS): list,
    vol.Optional(CONF_PERSISTENT, default=False): cv.boolean,
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
            
            self.hass.services.async_register("notify", service_name, _send, schema=vol.Schema({
                vol.Required(ATTR_MESSAGE): cv.string,
                vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
                vol.Optional(ATTR_DATA): dict,
            }))
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
            
            self.hass.services.async_register("notify", service_name, _send, schema=vol.Schema({
                vol.Required(ATTR_MESSAGE): cv.string,
                vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
                vol.Optional(ATTR_DATA): dict,
            }))
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


async def _resolve_targets(hass: HomeAssistant, storage: NotifyPersonStorage, name: str) -> list[str]:
    """Resolve a person or group name to list of notify service names."""
    persons = storage.get_persons()
    groups = storage.get_groups()
    
    # Check if it's a group
    for gid, gconfig in groups.items():
        if gconfig.get("name") == name or gid == name:
            targets = []
            for member_name in gconfig.get("persons", []):
                for pid, pconfig in persons.items():
                    if pconfig.get("name") == member_name or pid == member_name:
                        targets.extend(pconfig.get("notify_targets", []))
                        break
            return targets
    
    # Check if it's a person
    for pid, pconfig in persons.items():
        if pconfig.get("name") == name or pid == name:
            return pconfig.get("notify_targets", [])
    
    _LOGGER.warning("Could not resolve person/group: %s", name)
    return []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    storage = NotifyPersonStorage(hass)
    await storage.async_load()
    
    # Migrate config entry data to storage if needed
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
    
    # --- Register simple_notify service ---
    async def async_simple_notify(call: ServiceCall) -> None:
        """Handle simple notify service call."""
        person_name = call.data[ATTR_PERSON]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        
        targets = await _resolve_targets(hass, storage, person_name)
        if not targets:
            _LOGGER.warning("No targets found for person/group: %s", person_name)
            return
        
        for target in targets:
            try:
                await hass.services.async_call(
                    "notify",
                    target.replace("notify.", ""),
                    {"message": message, "title": title},
                )
            except Exception as err:
                _LOGGER.error("Failed to notify %s: %s", target, err)
    
    hass.services.async_register(
        DOMAIN, SERVICE_SIMPLE_NOTIFY, async_simple_notify, schema=SIMPLE_NOTIFY_SCHEMA
    )
    
    # --- Register advanced_notify service ---
    async def async_advanced_notify(call: ServiceCall) -> None:
        """Handle advanced notify service call."""
        person_name = call.data[ATTR_PERSON]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        
        # Build notification data dict
        notify_data = dict(call.data.get(ATTR_DATA, {}))
        
        # Add advanced fields to data block (where mobile app expects them)
        if call.data.get(CONF_CHANNEL):
            notify_data["channel"] = call.data[CONF_CHANNEL]
        if call.data.get(CONF_TAG):
            notify_data["tag"] = call.data[CONF_TAG]
        if call.data.get(CONF_ACTIONS):
            notify_data["actions"] = call.data[CONF_ACTIONS]
        if call.data.get(CONF_PERSISTENT):
            notify_data["persistent"] = True
        
        # Priority / critical handling
        priority = call.data.get(CONF_PRIORITY, "normal")
        critical = call.data.get(CONF_CRITICAL, False)
        
        if critical:
            notify_data["priority"] = "high"
            notify_data["ttl"] = 0
            notify_data.setdefault("push", {})["sound"] = {
                "name": "default", "critical": 1, "volume": 1.0
            }
        elif priority == "high":
            notify_data["priority"] = "high"
        elif priority == "low":
            notify_data["priority"] = "low"
        
        targets = await _resolve_targets(hass, storage, person_name)
        if not targets:
            _LOGGER.warning("No targets found for person/group: %s", person_name)
            return
        
        for target in targets:
            try:
                await hass.services.async_call(
                    "notify",
                    target.replace("notify.", ""),
                    {"message": message, "title": title, "data": notify_data},
                )
            except Exception as err:
                _LOGGER.error("Failed to notify %s: %s", target, err)
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADVANCED_NOTIFY, async_advanced_notify, schema=ADVANCED_NOTIFY_SCHEMA
    )
    
    hass.data[DOMAIN][entry.entry_id] = {
        "storage": storage,
        "manager": manager,
    }
    
    _LOGGER.info("Notify Person loaded (v0.2.0)")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove simple_notify and advanced_notify services
    hass.services.async_remove(DOMAIN, SERVICE_SIMPLE_NOTIFY)
    hass.services.async_remove(DOMAIN, SERVICE_ADVANCED_NOTIFY)
    
    entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if entry_data and (manager := entry_data.get("manager")):
        await manager.async_cleanup()
    return True
