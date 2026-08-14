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
    CONF_PERSISTENT,
    CONF_COLOR,
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
    schema_dict = {}
    schema_dict[vol.Required(ATTR_PERSON)] = vol.Any(cv.string, [cv.string])
    schema_dict[vol.Required(ATTR_MESSAGE)] = cv.string
    schema_dict[vol.Optional(ATTR_TITLE, default="")] = cv.string
    return vol.Schema(schema_dict)


def _build_advanced_schema(person_names: list[str]):
    """Build advanced_notify schema — accepts entity IDs or names."""
    schema_dict = {}
    schema_dict[vol.Required(ATTR_PERSON)] = vol.Any(cv.string, [cv.string])
    schema_dict[vol.Required(ATTR_MESSAGE)] = cv.string
    schema_dict[vol.Optional(ATTR_TITLE, default="")] = cv.string
    schema_dict[vol.Optional(CONF_CHANNEL)] = cv.string
    schema_dict[vol.Optional(CONF_PRIORITY, default="normal")] = vol.In(["normal", "high", "low"])
    schema_dict[vol.Optional(CONF_CRITICAL, default=False)] = cv.boolean
    schema_dict[vol.Optional(CONF_TAG)] = cv.string
    schema_dict[vol.Optional(CONF_PERSISTENT, default=False)] = cv.boolean
    schema_dict[vol.Optional(CONF_COLOR)] = cv.string
    # Actions: UI-friendly list from services.yaml
    schema_dict[vol.Optional("actions")] = vol.Any(list, dict, cv.string)
    # Legacy button slots (backward compat — not shown in UI)
    schema_dict[vol.Optional("action_1_id")] = cv.string
    schema_dict[vol.Optional("action_1_title")] = cv.string
    schema_dict[vol.Optional("action_2_id")] = cv.string
    schema_dict[vol.Optional("action_2_title")] = cv.string
    schema_dict[vol.Optional("action_3_id")] = cv.string
    schema_dict[vol.Optional("action_3_title")] = cv.string
    schema_dict[vol.Optional("action_4_id")] = cv.string
    schema_dict[vol.Optional("action_4_title")] = cv.string
    schema_dict[vol.Optional("action_5_id")] = cv.string
    schema_dict[vol.Optional("action_5_title")] = cv.string
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
    if call.data.get(CONF_COLOR):
        notify_data["color"] = call.data[CONF_COLOR]
    
    # Build actions array from list of objects (UI-friendly)
    actions_list = call.data.get("actions", [])
    if actions_list and isinstance(actions_list, list):
        actions = []
        for action_item in actions_list:
            if isinstance(action_item, dict):
                action_id = action_item.get("action")
                action_title = action_item.get("title")
                if action_id and action_title:
                    actions.append({"action": action_id, "title": action_title})
        if actions:
            notify_data["actions"] = actions
    
    # Legacy button slots (backward compat)
    legacy_actions = []
    for i in range(1, 6):
        action_id = call.data.get(f"action_{i}_id")
        action_title = call.data.get(f"action_{i}_title")
        if action_id and action_title:
            legacy_actions.append({"action": action_id, "title": action_title})
    if legacy_actions:
        notify_data["actions"] = legacy_actions
    
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
        title = call.data.get(ATTR_TITLE, "")
        
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
    
    # Advanced notify handler
    async def async_advanced_notify(call: ServiceCall) -> None:
        selected_persons = call.data[ATTR_PERSON]
        # Handle single string (legacy / empty list fallback)
        if isinstance(selected_persons, str):
            selected_persons = [selected_persons]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "")
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
        
        # Deduplicate targets
        unique_targets = list(dict.fromkeys(all_targets))
        
        if not unique_targets:
            _LOGGER.warning("No targets found for persons: %s", selected_persons)
            return
        
        await _send_notification(hass, unique_targets, message, title, notify_data)
    
    # Register with current person list for schema
    hass.services.async_register(
        DOMAIN,
        SERVICE_SIMPLE_NOTIFY,
        async_simple_notify,
        schema=_build_simple_schema(person_names),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADVANCED_NOTIFY,
        async_advanced_notify,
        schema=_build_advanced_schema(person_names),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up notify_person from a config entry."""
    _LOGGER.debug("Setting up notify_person entry: %s", entry.title)
    
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "data": entry.data,
        "options": entry.options,
    }
    
    # Register services with current person list
    await _register_services(hass)
    
    # Mark services as registered
    hass.data[DOMAIN]["services_registered"] = True
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading notify_person entry: %s", entry.title)
    
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    # Re-register services with remaining persons
    await _register_services(hass)
    
    return True
