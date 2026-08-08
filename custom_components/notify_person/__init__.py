"""The Notify Person integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    ATTR_MESSAGE,
    ATTR_TITLE,
    ATTR_DATA,
    ATTR_PERSON,
    CONF_CHANNEL,
    CONF_PRIORITY,
    CONF_CRITICAL,
    CONF_TAG,
    CONF_ACTIONS,
    CONF_PERSISTENT,
    SERVICE_SIMPLE_NOTIFY,
    SERVICE_ADVANCED_NOTIFY,
)

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


def _resolve_targets(entry_data: dict, entry_options: dict, name: str) -> list[str]:
    """Resolve a person or group name to list of notify service names."""
    persons = entry_data.get("persons", {})
    groups = entry_data.get("groups", {})
    
    # Merge notify_targets from entry_options if present
    merged_persons = {}
    for pid, pconfig in persons.items():
        merged_persons[pid] = dict(pconfig) if pconfig else {}
        key = f"devices_{pid}"
        if key in entry_options:
            merged_persons[pid]["notify_targets"] = entry_options[key]
    
    # Check if it's a group
    for gid, gconfig in groups.items():
        if gconfig.get("name") == name or gid == name:
            targets = []
            for member_name in gconfig.get("persons", []):
                for pid, pconfig in merged_persons.items():
                    if pconfig.get("name") == member_name or pid == member_name:
                        targets.extend(pconfig.get("notify_targets", []))
                        break
            return targets
    
    # Check if it's a person
    for pid, pconfig in merged_persons.items():
        if pconfig.get("name") == name or pid == name:
            return pconfig.get("notify_targets", [])
    
    _LOGGER.warning("Could not resolve person/group: %s", name)
    return []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    entry_data = entry.data
    entry_options = entry.options or {}
    
    # --- Register simple_notify service ---
    async def async_simple_notify(call: ServiceCall) -> None:
        """Handle simple notify service call."""
        person_name = call.data[ATTR_PERSON]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        
        targets = _resolve_targets(entry.data, entry.options or {}, person_name)
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
        
        targets = _resolve_targets(entry.data, entry.options or {}, person_name)
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
    
    # Add listener for config entry updates (options flow changes)
    @callback
    def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.debug("Config entry updated, services reloaded")
    
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
    }
    
    _LOGGER.info("Notify Person loaded (v0.1.3)")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove simple_notify and advanced_notify services
    hass.services.async_remove(DOMAIN, SERVICE_SIMPLE_NOTIFY)
    hass.services.async_remove(DOMAIN, SERVICE_ADVANCED_NOTIFY)
    
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
