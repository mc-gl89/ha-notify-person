"""Storage handler for Notify Person configuration."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


class NotifyPersonStorage:
    """Class to handle storage of person notification configs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {}

    async def async_load(self) -> dict[str, Any]:
        """Load stored data."""
        self._data = await self._store.async_load() or {}
        _LOGGER.debug("Loaded storage data: %s", self._data)
        return self._data

    async def async_save(self) -> None:
        """Save current data to storage."""
        await self._store.async_save(self._data)
        _LOGGER.debug("Saved storage data")

    def get_persons(self) -> dict[str, Any]:
        """Get all configured persons."""
        return self._data.get("persons", {})

    def get_person(self, person_id: str) -> dict[str, Any] | None:
        """Get a specific person config."""
        return self._data.get("persons", {}).get(person_id)

    def add_person(self, person_id: str, config: dict[str, Any]) -> None:
        """Add or update a person config."""
        if "persons" not in self._data:
            self._data["persons"] = {}
        self._data["persons"][person_id] = config

    def remove_person(self, person_id: str) -> None:
        """Remove a person config."""
        if "persons" in self._data and person_id in self._data["persons"]:
            del self._data["persons"][person_id]

    def get_groups(self) -> dict[str, Any]:
        """Get all notification groups."""
        return self._data.get("groups", {})

    def add_group(self, group_id: str, config: dict[str, Any]) -> None:
        """Add or update a notification group."""
        if "groups" not in self._data:
            self._data["groups"] = {}
        self._data["groups"][group_id] = config

    def remove_group(self, group_id: str) -> None:
        """Remove a notification group."""
        if "groups" in self._data and group_id in self._data["groups"]:
            del self._data["groups"][group_id]

    def get_defaults(self) -> dict[str, Any]:
        """Get global default settings."""
        return self._data.get("defaults", {})

    def set_defaults(self, defaults: dict[str, Any]) -> None:
        """Set global default settings."""
        self._data["defaults"] = defaults
