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
    CONF_ACTION_1_ID,
    CONF_ACTION_1_TITLE,
    CONF_ACTION_2_ID,
    CONF_ACTION_2_TITLE,
    CONF_ACTION_3_ID,
    CONF_ACTION_3_TITLE,
    CONF_ACTION_4_ID,
    CONF_ACTION_4_TITLE,
    CONF_ACTION_5_ID,
    CONF_ACTION_5_TITLE,
    SERVICE_SIMPLE_NOTIFY,
    SERVICE_ADVANCED_NOTIFY,
)

_LOGGER = logging.getLogger(__name__)


def _get_all_person_names(hass: HomeAssistant) -> list[str]:
    """Collect all person names from all notify_person config entries."""
    names = []
    domain_data = hass.data.get(DOMAIN, {})
    for key, edata in domain_data.items():
        if key == "services_registered":
            continue
        entry = edata.get("entry") if isinstance(edata, dict) else None
        if entry and hasattr(entry, "data"):
            persons = entry.data.get("persons", {})
            for pid, pconfig in persons.items():
                if isinstance(pconfig, dict):
                    name = pconfig.get("name", pid.replace("person.", ""))
                    if name and name not in names:
                        names.append(name)
    return sorted(names)


def _build_simple_schema(person_names: list[str]):
    """Build simple_notify schema — accepts entity IDs or names."""
    # Entity-IDs are strings, so we accept string or list of strings
    # No validation against person_names — resolver handles unknown persons
    schema_dict = {}
    schema_dict[vol.Required(ATTR_PERSON)] = vol.Any(cv.string, [cv.string])
    schema_dict[vol.Required(ATTR_MESSAGE)] = cv.string
    schema_dict[vol.Optional(ATTR_TITLE, default="Home Assistant")] = cv.string
    return vol.Schema(schema_dict)


def _build_advanced_schema(person_names: list[str]):
    """Build advanced_notify schema — accepts entity IDs or names."""
    schema_dict = {}
    schema_dict[vol.Required(ATTR_PERSON)] = vol.Any(cv.string, [cv.string])
    schema_dict[vol.Required(ATTR_MESSAGE)] = cv.string
    schema_dict[vol.Optional(ATTR_TITLE, default="Home Assistant")] = cv.string
    schema_dict[vol.Optional(CONF_CHANNEL)] = cv.string
    schema_dict[vol.Optional(CONF_PRIORITY, default="normal")] = vol.In(["normal", "high", "low"])
    schema_dict[vol.Optional(CONF_CRITICAL, default=False)] = cv.boolean
    schema_dict[vol.Optional(CONF_TAG)] = cv.string
    schema_dict[vol.Optional(CONF_PERSISTENT, default=False)] = cv.boolean
    # Legacy actions field (backward compat, prefer button slots below)
    schema_dict[vol.Optional(CONF_ACTIONS)] = list
    # UI-friendly action buttons: up to 5 individual button slots
    schema_dict[vol.Optional(CONF_ACTION_1_ID)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_1_TITLE)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_2_ID)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_2_TITLE)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_3_ID)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_3_TITLE)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_4_ID)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_4_TITLE)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_5_ID)] = cv.string
    schema_dict[vol.Optional(CONF_ACTION_5_TITLE)] = cv.string
    schema_dict[vol.Optional(ATTR_DATA)] = dict
    return vol.Schema(schema_dict)


def _resolve_targets(entry_data: dict, entry_options: dict, name: str) -> list[str]:
    """Resolve a person or group name to list of notify service names."""
    persons = entry_data.get("persons", {})
    groups = entry_data.get("groups", {})
    
    merged_persons = {}
    for pid, pconfig in persons.items():
        merged_persons[pid] = dict(pconfig) if pconfig else {}
        key = f"devices_{pid}"
        if key in entry_options:
            merged_persons[pid]["notify_targets"] = entry_options[key]
    
    for gid, gconfig in groups.items():
        if gconfig.get("name") == name or gid == name:
            targets = []
            for member_name in gconfig.get("persons", []):
                for pid, pconfig in merged_persons.items():
                    if pconfig.get("name") == member_name or pid == member_name:
                        targets.extend(pconfig.get("notify_targets", []))
                        break
            return targets
    
    for pid, pconfig in merged_persons.items():
        if pconfig.get("name") == name or pid == name:
            return pconfig.get("notify_targets", [])
    
    _LOGGER.warning("Could not resolve person/group: %s", name)
    return []


def _build_notify_data(call: ServiceCall) -> dict:
    """Build notification data dict from service call."""
    notify_data = dict(call.data.get(ATTR_DATA, {}))
    
    if call.data.get(CONF_CHANNEL):
        notify_data["channel"] = call.data[CONF_CHANNEL]
    if call.data.get(CONF_TAG):
        notify_data["tag"] = call.data[CONF_TAG]
    
    # Build actions array from individual UI button slots (preferred)
    actions = []
    action_pairs = [
        (CONF_ACTION_1_ID, CONF_ACTION_1_TITLE),
        (CONF_ACTION_2_ID, CONF_ACTION_2_TITLE),
        (CONF_ACTION_3_ID, CONF_ACTION_3_TITLE),
        (CONF_ACTION_4_ID, CONF_ACTION_4_TITLE),
        (CONF_ACTION_5_ID, CONF_ACTION_5_TITLE),
    ]
    for id_key, title_key in action_pairs:
        action_id = call.data.get(id_key)
        action_title = call.data.get(title_key)
        if action_id and action_title:
            actions.append({"action": action_id, "title": action_title})
    if actions:
        notify_data["actions"] = actions
    elif call.data.get(CONF_ACTIONS):
        # Legacy: raw actions array from YAML
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


async def _register_services(hass: HomeAssistant) -> None:
    """Register or re-register simple_notify and advanced_notify with current person list."""
    person_names = _get_all_person_names(hass)
    _LOGGER.debug("Registering notify_person services with persons: %s", person_names)
    
    # Remove existing services if present
    if hass.services.has_service(DOMAIN, SERVICE_SIMPLE_NOTIFY):
        hass.services.async_remove(DOMAIN, SERVICE_SIMPLE_NOTIFY)
    if hass.services.has_service(DOMAIN, SERVICE_ADVANCED_NOTIFY):
        hass.services.async_remove(DOMAIN, SERVICE_ADVANCED_NOTIFY)
    
    # Simple notify handler
    async def async_simple_notify(call: ServiceCall) -> None:
        selected_persons = call.data[ATTR_PERSON]
        # Handle single string (legacy / empty list fallback)
        if isinstance(selected_persons, str):
            selected_persons = [selected_persons]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        
        all_targets = []
        for person_name in selected_persons:
            for key, edata in hass.data[DOMAIN].items():
                if key == "services_registered":
                    continue
                entry = edata.get("entry") if isinstance(edata, dict) else None
                if entry and hasattr(entry, "data"):
                    t = _resolve_targets(entry.data, entry.options or {}, person_name)
                    if t:
                        all_targets.extend(t)
        
        # Deduplicate targets
        unique_targets = list(dict.fromkeys(all_targets))
        
        if not unique_targets:
            _LOGGER.warning("No targets found for persons: %s", selected_persons)
            return
        
        await _send_notification(hass, unique_targets, message, title)
    
    hass.services.async_register(
        DOMAIN, SERVICE_SIMPLE_NOTIFY, async_simple_notify,
        schema=_build_simple_schema(person_names)
    )
    
    # Advanced notify handler
    async def async_advanced_notify(call: ServiceCall) -> None:
        selected_persons = call.data[ATTR_PERSON]
        if isinstance(selected_persons, str):
            selected_persons = [selected_persons]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        notify_data = _build_notify_data(call)
        
        all_targets = []
        for person_name in selected_persons:
            for key, edata in hass.data[DOMAIN].items():
                if key == "services_registered":
                    continue
                entry = edata.get("entry") if isinstance(edata, dict) else None
                if entry and hasattr(entry, "data"):
                    t = _resolve_targets(entry.data, entry.options or {}, person_name)
                    if t:
                        all_targets.extend(t)
        
        unique_targets = list(dict.fromkeys(all_targets))
        
        if not unique_targets:
            _LOGGER.warning("No targets found for persons: %s", selected_persons)
            return
        
        await _send_notification(hass, unique_targets, message, title, notify_data)
    
    hass.services.async_register(
        DOMAIN, SERVICE_ADVANCED_NOTIFY, async_advanced_notify,
        schema=_build_advanced_schema(person_names)
    )
    
    hass.data[DOMAIN]["services_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notify Person from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store entry
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
    }
    
    # Register (or re-register) services with updated person list
    await _register_services(hass)
    
    # Add listener for config entry updates (options flow changes)
    @callback
    def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.debug("Config entry updated, re-registering services")
        hass.async_create_task(_register_services(hass))
    
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    _LOGGER.info("Notify Person loaded (v0.1.16)")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    
    # Check if any entries remain
    remaining = [k for k in hass.data.get(DOMAIN, {}).keys() if k not in ("services_registered",)]
    
    if not remaining:
        # Remove services
        if hass.services.has_service(DOMAIN, SERVICE_SIMPLE_NOTIFY):
            hass.services.async_remove(DOMAIN, SERVICE_SIMPLE_NOTIFY)
        if hass.services.has_service(DOMAIN, SERVICE_ADVANCED_NOTIFY):
            hass.services.async_remove(DOMAIN, SERVICE_ADVANCED_NOTIFY)
        hass.data.pop(DOMAIN, None)
    else:
        # Re-register with remaining persons
        hass.async_create_task(_register_services(hass))
    
    return True
