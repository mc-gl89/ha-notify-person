"""Config flow for Notify Person integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_CHANNEL, DEFAULT_CRITICALITY, DEFAULT_IMPORTANCE

_LOGGER = logging.getLogger(__name__)

# Step IDs
STEP_USER = "user"
STEP_PERSONS = "persons"
STEP_DEVICES = "devices"


class NotifyPersonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notify Person."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

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
                vol.Required("integration_name", default="Notify Person"): str,
            }),
            description_placeholders={},
        )

    async def async_step_persons(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure notification groups and persons."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data.get("integration_name", "Notify Person"),
                data=self._data,
            )

        # Get available persons from HA
        persons = self.hass.states.async_entity_ids("person")
        person_options = {p: p.replace("person.", "") for p in persons}

        return self.async_show_form(
            step_id=STEP_PERSONS,
            data_schema=vol.Schema({
                vol.Optional("selected_persons"): cv.multi_select(person_options),
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "default_channel",
                    default=self.config_entry.options.get("default_channel", DEFAULT_CHANNEL),
                ): str,
                vol.Optional(
                    "default_criticality",
                    default=self.config_entry.options.get("default_criticality", DEFAULT_CRITICALITY),
                ): vol.In(["normal", "high", "critical"]),
            }),
        )
