"""Notify services for Notify Person integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    ATTR_MESSAGE,
    ATTR_TITLE,
    ATTR_DATA,
    ATTR_TARGETS,
    ATTR_CHANNEL,
    ATTR_CRITICALITY,
    ATTR_IMPORTANCE,
    CONF_DEFAULT_CHANNEL,
    CONF_DEFAULT_CRITICALITY,
    CONF_DEFAULT_IMPORTANCE,
    DEFAULT_CHANNEL,
    DEFAULT_CRITICALITY,
    DEFAULT_IMPORTANCE,
)
from .storage import NotifyPersonStorage

_LOGGER = logging.getLogger(__name__)

# Service schemas
NOTIFY_PERSON_SCHEMA = vol.Schema({
    vol.Required("person"): cv.string,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_DATA): dict,
    vol.Optional(ATTR_CHANNEL): cv.string,
    vol.Optional(ATTR_CRITICALITY): vol.In(["normal", "high", "critical"]),
    vol.Optional(ATTR_IMPORTANCE): vol.In(["default", "low", "high"]),
})

NOTIFY_GROUP_SCHEMA = vol.Schema({
    vol.Required("group"): cv.string,
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_DATA): dict,
    vol.Optional(ATTR_CHANNEL): cv.string,
    vol.Optional(ATTR_CRITICALITY): vol.In(["normal", "high", "critical"]),
    vol.Optional(ATTR_IMPORTANCE): vol.In(["default", "low", "high"]),
})


class NotifyPersonService:
    """Handle notify services."""

    def __init__(self, hass: HomeAssistant, storage: NotifyPersonStorage, entry_id: str) -> None:
        """Initialize the service handler."""
        self.hass = hass
        self.storage = storage
        self.entry_id = entry_id

    async def async_notify_person(self, call: ServiceCall) -> None:
        """Send notification to a specific person."""
        person_name = call.data["person"]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        data = call.data.get(ATTR_DATA, {})
        
        # Get person config from storage
        persons = self.storage.get_persons()
        person_config = None
        person_id = None
        
        # Find person by name or entity_id
        for pid, config in persons.items():
            if config.get("name") == person_name or pid == person_name or pid.replace("person.", "") == person_name:
                person_config = config
                person_id = pid
                break
        
        if not person_config:
            _LOGGER.error("Person '%s' not found in Notify Person configuration", person_name)
            return
        
        # Get default settings
        defaults = person_config.get("defaults", {})
        global_defaults = self.storage.get_defaults()
        
        # Build notification data
        notify_data = dict(data)
        
        # Set channel
        channel = call.data.get(ATTR_CHANNEL) or defaults.get(CONF_DEFAULT_CHANNEL) or global_defaults.get(CONF_DEFAULT_CHANNEL) or DEFAULT_CHANNEL
        if channel:
            notify_data["channel"] = channel
        
        # Set criticality (for iOS/Android)
        criticality = call.data.get(ATTR_CRITICALITY) or defaults.get(CONF_DEFAULT_CRITICALITY) or global_defaults.get(CONF_DEFAULT_CRITICALITY) or DEFAULT_CRITICALITY
        if criticality == "critical":
            notify_data["priority"] = "high"
            notify_data["ttl"] = 0
            if "push" not in notify_data:
                notify_data["push"] = {}
            notify_data["push"]["sound"] = {
                "name": "default",
                "critical": 1,
                "volume": 1.0,
            }
        elif criticality == "high":
            notify_data["priority"] = "high"
        
        # Set importance (Android specific)
        importance = call.data.get(ATTR_IMPORTANCE) or defaults.get(CONF_DEFAULT_IMPORTANCE) or global_defaults.get(CONF_DEFAULT_IMPORTANCE) or DEFAULT_IMPORTANCE
        if importance != "default":
            notify_data["importance"] = importance
        
        # Send to all devices assigned to this person
        targets = person_config.get("notify_targets", [])
        if not targets:
            _LOGGER.warning("No notification targets configured for person '%s'", person_name)
            return
        
        _LOGGER.info("Sending notification to %s via %d target(s)", person_name, len(targets))
        
        for target in targets:
            try:
                service_name = target if target.startswith("notify.") else f"notify.{target}"
                await self.hass.services.async_call(
                    "notify",
                    target.replace("notify.", ""),
                    {
                        "message": message,
                        "title": title,
                        "data": notify_data,
                    },
                )
                _LOGGER.debug("Sent notification to %s", target)
            except Exception as err:
                _LOGGER.error("Failed to send notification to %s: %s", target, err)

    async def async_notify_group(self, call: ServiceCall) -> None:
        """Send notification to a group."""
        group_name = call.data["group"]
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE, "Home Assistant")
        data = call.data.get(ATTR_DATA, {})
        
        # Get group config from storage
        groups = self.storage.get_groups()
        group_config = groups.get(group_name)
        
        if not group_config:
            _LOGGER.error("Group '%s' not found in Notify Person configuration", group_name)
            return
        
        # Get group members
        member_persons = group_config.get("persons", [])
        if not member_persons:
            _LOGGER.warning("No persons in group '%s'", group_name)
            return
        
        _LOGGER.info("Sending notification to group '%s' (%d members)", group_name, len(member_persons))
        
        # Send to each person in the group
        for person_name in member_persons:
            await self.hass.services.async_call(
                DOMAIN,
                "notify_person",
                {
                    "person": person_name,
                    ATTR_MESSAGE: message,
                    ATTR_TITLE: title,
                    ATTR_DATA: data,
                    ATTR_CHANNEL: call.data.get(ATTR_CHANNEL),
                    ATTR_CRITICALITY: call.data.get(ATTR_CRITICALITY),
                    ATTR_IMPORTANCE: call.data.get(ATTR_IMPORTANCE),
                },
            )


async def async_setup_services(hass: HomeAssistant, storage: NotifyPersonStorage, entry_id: str) -> None:
    """Set up Notify Person services."""
    service = NotifyPersonService(hass, storage, entry_id)
    
    hass.services.async_register(
        DOMAIN,
        "notify_person",
        service.async_notify_person,
        schema=NOTIFY_PERSON_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "notify_group",
        service.async_notify_group,
        schema=NOTIFY_GROUP_SCHEMA,
    )
    
    _LOGGER.info("Notify Person services registered")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Notify Person services."""
    hass.services.async_remove(DOMAIN, "notify_person")
    hass.services.async_remove(DOMAIN, "notify_group")
    _LOGGER.info("Notify Person services removed")
