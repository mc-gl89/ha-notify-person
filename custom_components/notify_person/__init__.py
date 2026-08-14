"""The Notify Person integration."""

import logging
import re

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

# Schema for simple_notify (generic - person required)
SIMPLE_NOTIFY_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON): cv.string,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
})

# Schema for advanced_notify (generic - person required)
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

# Schema for person-specific notify (no person field)
PERSON_SIMPLE_NOTIFY_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE, default="Home Assistant"): cv.string,
})

PERSON_ADVANCED_NOTIFY_SCHEMA = vol.Schema({
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


def _sanitize_service_name(name: str) -> str:
    """Sanitize a name for use as HA service suffix."""
    # Lowercase, replace spaces/special chars with underscore
    sanitized = re.sub(r'[^a-z0-9_]', '_', name.lower())
    # Collapse multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Strip leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized or "person"


def _build_notify_data(call: ServiceCall) -> dict:
    """Build notification data dict from service call."""
    notify_data = dict(call.data.get(ATTR_DATA, {}))
    
    if call.data.get(CONF_CHANNEL):
        notify_data["channel"] = call.data[CONF_CHANNEL]
    if call.data.get(CONF_TAG):
        notify_data["tag"] = call.data[CONF_TAG]
    if call.data.get(CONF_ACTIONS):
        notify_data["actions"] = call.data[CONF_ACTIONS]
    if call.data.get(CONF_PERSISTENT):
        notify_data["persistent"] = True
    
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
    
    return notify_data


async def _send_notification(hass: HomeAssistant, targets: list[str], message: str, title: str, notify_data: dict | None = None) -> None:
    """Send notification to all targets."""
    for target in targets:
        try:
            service_data = {"message": message, "title": title}
            if notify_data:
                service_data["data"] = notify_data
            await hass.services.async_call(
                "notify",
                target.replace("notify.", ""),
                service_data,
            )
        except Exception as err:
            _LOGGER.error("Failed to notify %s: %s", target, err)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("person_services", set())
    
    entry_data = entry.data
    entry_options = entry.options or {}
    
    # --- Register generic simple_notify service (if not already registered) ---
    if not hass.services.has_service(DOMAIN, SERVICE_SIMPLE_NOTIFY):
        async def async_simple_notify(call: ServiceCall) -> None:
            """Handle simple notify service call."""
            person_name = call.data[ATTR_PERSON]
            message = call.data[ATTR_MESSAGE]
            title = call.data.get(ATTR_TITLE, "Home Assistant")
            
            # Find the entry that has this person
            targets = []
            for eid, edata in hass.data[DOMAIN].items():
                if eid in ("person_services",):
                    continue
                e = edata.get("entry")
                if e:
                    t = _resolve_targets(e.data, e.options or {}, person_name)
                    if t:
                        targets = t
                        break
            
            if not targets:
                _LOGGER.warning("No targets found for person/group: %s", person_name)
                return
            
            await _send_notification(hass, targets, message, title)
        
        hass.services.async_register(
            DOMAIN, SERVICE_SIMPLE_NOTIFY, async_simple_notify, schema=SIMPLE_NOTIFY_SCHEMA
        )
    
    # --- Register generic advanced_notify service (if not already registered) ---
    if not hass.services.has_service(DOMAIN, SERVICE_ADVANCED_NOTIFY):
        async def async_advanced_notify(call: ServiceCall) -> None:
            """Handle advanced notify service call."""
            person_name = call.data[ATTR_PERSON]
            message = call.data[ATTR_MESSAGE]
            title = call.data.get(ATTR_TITLE, "Home Assistant")
            notify_data = _build_notify_data(call)
            
            # Find the entry that has this person
            targets = []
            for eid, edata in hass.data[DOMAIN].items():
                if eid in ("person_services",):
                    continue
                e = edata.get("entry")
                if e:
                    t = _resolve_targets(e.data, e.options or {}, person_name)
                    if t:
                        targets = t
                        break
            
            if not targets:
                _LOGGER.warning("No targets found for person/group: %s", person_name)
                return
            
            await _send_notification(hass, targets, message, title, notify_data)
        
        hass.services.async_register(
            DOMAIN, SERVICE_ADVANCED_NOTIFY, async_advanced_notify, schema=ADVANCED_NOTIFY_SCHEMA
        )
    
    # --- Register person-specific services ---
    persons = entry_data.get("persons", {})
    entry_person_services = []
    
    for pid, pconfig in persons.items():
        person_name = pconfig.get("name", pid.replace("person.", ""))
        sanitized = _sanitize_service_name(person_name)
        service_name = f"notify_{sanitized}"
        
        # Check for conflicts across all entries
        full_service = f"{DOMAIN}.{service_name}"
        if full_service in hass.data[DOMAIN]["person_services"]:
            _LOGGER.warning(
                "Service %s already registered (another entry has person '%s'). Skipping.",
                service_name, person_name
            )
            continue
        
        hass.data[DOMAIN]["person_services"].add(full_service)
        entry_person_services.append(service_name)
        
        # Simple notify for this person
        async def _make_simple_handler(p_name: str, e_id: str) -> callable:
            async def handler(call: ServiceCall) -> None:
                message = call.data[ATTR_MESSAGE]
                title = call.data.get(ATTR_TITLE, "Home Assistant")
                edata = hass.data[DOMAIN].get(e_id, {})
                e = edata.get("entry")
                if e:
                    targets = _resolve_targets(e.data, e.options or {}, p_name)
                    if targets:
                        await _send_notification(hass, targets, message, title)
                    else:
                        _LOGGER.warning("No targets for person: %s", p_name)
                else:
                    _LOGGER.warning("Entry %s not found for person %s", e_id, p_name)
            return handler
        
        hass.services.async_register(
            DOMAIN,
            service_name,
            _make_simple_handler(person_name, entry.entry_id),
            schema=PERSON_SIMPLE_NOTIFY_SCHEMA,
        )
        
        # Advanced notify for this person
        adv_service_name = f"{service_name}_advanced"
        full_adv_service = f"{DOMAIN}.{adv_service_name}"
        entry_person_services.append(adv_service_name)
        hass.data[DOMAIN]["person_services"].add(full_adv_service)
        
        async def _make_advanced_handler(p_name: str, e_id: str) -> callable:
            async def handler(call: ServiceCall) -> None:
                message = call.data[ATTR_MESSAGE]
                title = call.data.get(ATTR_TITLE, "Home Assistant")
                notify_data = _build_notify_data(call)
                edata = hass.data[DOMAIN].get(e_id, {})
                e = edata.get("entry")
                if e:
                    targets = _resolve_targets(e.data, e.options or {}, p_name)
                    if targets:
                        await _send_notification(hass, targets, message, title, notify_data)
                    else:
                        _LOGGER.warning("No targets for person: %s", p_name)
                else:
                    _LOGGER.warning("Entry %s not found for person %s", e_id, p_name)
            return handler
        
        hass.services.async_register(
            DOMAIN,
            adv_service_name,
            _make_advanced_handler(person_name, entry.entry_id),
            schema=PERSON_ADVANCED_NOTIFY_SCHEMA,
        )
        
        _LOGGER.info(
            "Registered person services: %s and %s for %s",
            service_name, adv_service_name, person_name
        )
    
    # Store entry and its service names for cleanup
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "person_services": entry_person_services,
    }
    
    # Add listener for config entry updates
    @callback
    def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.debug("Config entry updated, services reloaded")
    
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    _LOGGER.info("Notify Person loaded (v0.1.15)")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    edata = hass.data[DOMAIN].pop(entry.entry_id, {})
    person_services = edata.get("person_services", [])
    
    # Remove person-specific services for this entry
    for svc in person_services:
        hass.services.async_remove(DOMAIN, svc)
        full = f"{DOMAIN}.{svc}"
        hass.data[DOMAIN]["person_services"].discard(full)
    
    # Check if any entries remain
    remaining_entries = [
        k for k in hass.data[DOMAIN].keys()
        if k not in ("person_services",)
    ]
    
    if not remaining_entries:
        # No entries left — remove generic services too
        hass.services.async_remove(DOMAIN, SERVICE_SIMPLE_NOTIFY)
        hass.services.async_remove(DOMAIN, SERVICE_ADVANCED_NOTIFY)
        hass.data.pop(DOMAIN, None)
    
    return True
