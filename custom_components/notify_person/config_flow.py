"""Config flow for Notify Person integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_PERSONS = "persons"
STEP_DEVICES = "devices"
STEP_GROUPS = "groups"


class NotifyPersonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Person."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._persons_data: dict[str, Any] = {}
        self._current_person_idx: int = 0

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Start config flow -- skip to persons selection."""
        return await self.async_step_persons(user_input)

    async def async_step_persons(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select persons from HA."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get("selected_persons", [])
            if not selected:
                errors["base"] = "no_persons_selected"
            else:
                self._data["selected_persons"] = selected
                self._persons_data = {}
                for pid in selected:
                    entity = self.hass.states.get(pid)
                    name = pid.replace("person.", "")
                    if entity and entity.attributes.get("friendly_name"):
                        name = entity.attributes["friendly_name"]
                    self._persons_data[pid] = {"name": name, "notify_targets": []}
                
                self._current_person_idx = 0
                return await self.async_step_devices()

        person_entities = self.hass.states.async_entity_ids("person")
        person_options = {}
        for pid in person_entities:
            entity = self.hass.states.get(pid)
            name = pid.replace("person.", "")
            if entity and entity.attributes.get("friendly_name"):
                name = entity.attributes["friendly_name"]
            person_options[pid] = f"{name} ({pid})"

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
        """Assign devices to current person."""
        errors: dict[str, str] = {}
        selected = self._data.get("selected_persons", [])
        
        if self._current_person_idx >= len(selected):
            # All persons configured -- skip groups step for now and create entry
            self._data["persons"] = self._persons_data
            self._data.pop("selected_persons", None)
            return self.async_create_entry(
                title="Notify Person",
                data=self._data,
            )

        current_pid = selected[self._current_person_idx]
        current_person = self._persons_data[current_pid]

        if user_input is not None:
            current_person["notify_targets"] = user_input.get("notify_targets", [])
            self._current_person_idx += 1
            return await self.async_step_devices()

        # Get available notify services (mobile_app, etc.)
        notify_services = self.hass.services.async_services().get("notify", {})
        device_options = {}
        for svc in notify_services:
            # Skip our own services
            if svc.startswith("person_") or svc.startswith("group_"):
                continue
            friendly = svc.replace("mobile_app_", "").replace("_", " ").title()
            device_options[svc] = friendly

        return self.async_show_form(
            step_id=STEP_DEVICES,
            data_schema=vol.Schema({
                vol.Optional("notify_targets", default=[]): cv.multi_select(device_options),
            }),
            description_placeholders={
                "person_name": current_person["name"],
            },
            errors=errors,
        )

    async def async_step_groups(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Create notification groups."""
        if user_input is not None:
            groups = {}
            raw_groups = user_input.get("groups", {})
            if isinstance(raw_groups, dict):
                for group_name, members in raw_groups.items():
                    if group_name and members:
                        safe_id = group_name.lower().replace(" ", "_").replace("-", "_")
                        groups[safe_id] = {"name": group_name, "persons": members}
            
            self._data["persons"] = self._persons_data
            self._data["groups"] = groups
            
            # Clean up temp data
            self._data.pop("selected_persons", None)
            
            return self.async_create_entry(
                title="Notify Person",
                data=self._data,
            )

        # Person options for group selection
        person_options = {}
        for pid, config in self._persons_data.items():
            person_options[config["name"]] = config["name"]

        return self.async_show_form(
            step_id=STEP_GROUPS,
            data_schema=vol.Schema({
                vol.Optional("groups"): dict,
            }),
            description_placeholders={},
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
        """Manage options -- show all persons with device assignment on one page."""
        try:
            persons = self.config_entry.data.get("persons", {})
            
            if user_input is not None:
                # Build options dict with device assignments
                options = {}
                for pid in persons:
                    key = f"devices_{pid}"
                    if key in user_input:
                        options[key] = user_input[key]
                
                # Return options to be saved in entry.options
                return self.async_create_entry(title="", data=options)
            
            # Build schema with all persons and their device options
            notify_services = self.hass.services.async_services().get("notify", {})
            device_options = {}
            for svc in notify_services:
                if svc.startswith("person_") or svc.startswith("group_"):
                    continue
                friendly = svc.replace("mobile_app_", "").replace("_", " ").title()
                device_options[svc] = friendly
            
            # Current saved options (may be empty on first run)
            current_options = self.config_entry.options or {}
            
            schema_fields = {}
            if persons:
                for pid, config in persons.items():
                    if not isinstance(config, dict):
                        config = {}
                    
                    name = config.get("name", pid.replace("person.", ""))
                    
                    # Start with notify_targets from config data
                    current_targets = config.get("notify_targets", [])
                    if not isinstance(current_targets, list):
                        current_targets = []
                    
                    # Override with options if present
                    key = f"devices_{pid}"
                    if key in current_options:
                        current_targets = current_options[key]
                    
                    schema_fields[vol.Optional(key, default=current_targets)] = cv.multi_select(device_options)
            else:
                _LOGGER.warning("No persons found in config entry data for options flow")
            
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(schema_fields),
                description_placeholders={"count": str(len(persons))},
            )
        except Exception as err:
            _LOGGER.exception("Error in options flow: %s", err)
            return self.async_abort(reason="unknown_error")
