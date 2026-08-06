"""Config flow for Notify Person integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_PERSONS,
    CONF_NOTIFY_TARGETS,
    CONF_DEFAULT_CHANNEL,
    CONF_DEFAULT_CRITICALITY,
    CONF_DEFAULT_IMPORTANCE,
    DEFAULT_CHANNEL,
    DEFAULT_CRITICALITY,
    DEFAULT_IMPORTANCE,
)

_LOGGER = logging.getLogger(__name__)

# Step IDs
STEP_USER = "user"
STEP_PERSONS = "persons"
STEP_DEVICES = "devices"
STEP_DEFAULTS = "defaults"


class NotifyPersonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Person."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._persons_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_persons()

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default="Notify Person"): str,
            }),
            description_placeholders={},
        )

    async def async_step_persons(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select persons from HA and assign devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data["selected_persons"] = user_input.get("selected_persons", [])
            
            if not self._data["selected_persons"]:
                errors["base"] = "no_persons_selected"
            else:
                # Initialize person configs
                for person_id in self._data["selected_persons"]:
                    entity = self.hass.states.get(person_id)
                    friendly_name = person_id.replace("person.", "")
                    if entity and entity.attributes.get("friendly_name"):
                        friendly_name = entity.attributes["friendly_name"]
                    
                    self._persons_data[person_id] = {
                        "name": friendly_name,
                        "notify_targets": [],
                        "defaults": {
                            CONF_DEFAULT_CHANNEL: DEFAULT_CHANNEL,
                            CONF_DEFAULT_CRITICALITY: DEFAULT_CRITICALITY,
                            CONF_DEFAULT_IMPORTANCE: DEFAULT_IMPORTANCE,
                        },
                    }
                
                return await self.async_step_devices()

        # Get available persons from HA
        person_entities = self.hass.states.async_entity_ids("person")
        person_options = {}
        for person_id in person_entities:
            entity = self.hass.states.get(person_id)
            name = person_id.replace("person.", "")
            if entity and entity.attributes.get("friendly_name"):
                name = entity.attributes["friendly_name"]
            person_options[person_id] = f"{name} ({person_id})"

        if not person_options:
            errors["base"] = "no_persons_found"

        return self.async_show_form(
            step_id=STEP_PERSONS,
            data_schema=vol.Schema({
                vol.Required("selected_persons"): cv.multi_select(person_options),
            }),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Assign mobile devices to persons."""
        errors: dict[str, str] = {}

        # Get current person being configured
        current_person_idx = self._data.get("_current_person_idx", 0)
        selected_persons = self._data.get("selected_persons", [])
        
        if current_person_idx >= len(selected_persons):
            # All persons configured, go to defaults
            return await self.async_step_defaults()

        current_person_id = selected_persons[current_person_idx]
        current_person = self._persons_data[current_person_id]

        if user_input is not None:
            # Save devices for current person
            current_person["notify_targets"] = user_input.get("notify_targets", [])
            
            # Move to next person
            self._data["_current_person_idx"] = current_person_idx + 1
            return await self.async_step_devices()

        # Get available notify services (mobile_app devices)
        notify_services = []
        for service in self.hass.services.async_services().get("notify", {}):
            if service.startswith("mobile_app_"):
                friendly_name = service.replace("mobile_app_", "").replace("_", " ").title()
                notify_services.append(service)
        
        # Also get device_tracker entities as fallback
        device_trackers = self.hass.states.async_entity_ids("device_tracker")
        
        device_options = {}
        for service in notify_services:
            device_options[service] = f"Notify: {service.replace('mobile_app_', '').replace('_', ' ').title()}"

        return self.async_show_form(
            step_id=STEP_DEVICES,
            data_schema=vol.Schema({
                vol.Optional("notify_targets", default=[]): cv.multi_select(device_options),
            }),
            description_placeholders={
                "person_name": current_person["name"],
                "person_id": current_person_id,
            },
            errors=errors,
        )

    async def async_step_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Set global default notification settings."""
        if user_input is not None:
            self._data["defaults"] = user_input
            self._data["persons"] = self._persons_data
            
            # Clean up temp data
            self._data.pop("_current_person_idx", None)
            self._data.pop("selected_persons", None)
            
            return self.async_create_entry(
                title=self._data.get(CONF_NAME, "Notify Person"),
                data=self._data,
            )

        return self.async_show_form(
            step_id=STEP_DEFAULTS,
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEFAULT_CHANNEL,
                    default=DEFAULT_CHANNEL,
                ): str,
                vol.Optional(
                    CONF_DEFAULT_CRITICALITY,
                    default=DEFAULT_CRITICALITY,
                ): vol.In(["normal", "high", "critical"]),
                vol.Optional(
                    CONF_DEFAULT_IMPORTANCE,
                    default=DEFAULT_IMPORTANCE,
                ): vol.In(["default", "low", "high"]),
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return NotifyPersonOptionsFlow(config_entry)


class NotifyPersonOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Notify Person."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = self.config_entry.data.get("defaults", {})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_DEFAULT_CHANNEL,
                    default=defaults.get(CONF_DEFAULT_CHANNEL, DEFAULT_CHANNEL),
                ): str,
                vol.Optional(
                    CONF_DEFAULT_CRITICALITY,
                    default=defaults.get(CONF_DEFAULT_CRITICALITY, DEFAULT_CRITICALITY),
                ): vol.In(["normal", "high", "critical"]),
                vol.Optional(
                    CONF_DEFAULT_IMPORTANCE,
                    default=defaults.get(CONF_DEFAULT_IMPORTANCE, DEFAULT_IMPORTANCE),
                ): vol.In(["default", "low", "high"]),
            }),
        )
