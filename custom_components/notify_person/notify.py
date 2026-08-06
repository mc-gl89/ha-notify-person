"""Notify platform for Notify Person integration."""

import logging
from typing import Any

from homeassistant.components.notify import ATTR_DATA, ATTR_TITLE, BaseNotificationService
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .storage import NotifyPersonStorage

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> BaseNotificationService | None:
    """Return the notify service."""
    # This is not used directly — we register entities instead
    return None


class NotifyPersonService(BaseNotificationService):
    """Base notification service for persons and groups."""

    def __init__(self, hass: HomeAssistant, storage: NotifyPersonStorage) -> None:
        """Initialize the service."""
        self.hass = hass
        self.storage = storage

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send a message."""
        raise NotImplementedError


class PersonNotifyService(NotifyPersonService):
    """Notification service for a single person."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: NotifyPersonStorage,
        person_id: str,
        person_config: dict,
    ) -> None:
        """Initialize person notify service."""
        super().__init__(hass, storage)
        self.person_id = person_id
        self.person_config = person_config

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send notification to all devices of this person."""
        title = kwargs.get(ATTR_TITLE, "Home Assistant")
        data = kwargs.get(ATTR_DATA, {})
        
        targets = self.person_config.get("notify_targets", [])
        if not targets:
            _LOGGER.warning("No notify targets for person '%s'", self.person_config.get("name", self.person_id))
            return

        _LOGGER.debug("Sending to person '%s' via %s", self.person_config.get("name"), targets)

        for target in targets:
            try:
                service_name = target.replace("notify.", "")
                await self.hass.services.async_call(
                    "notify",
                    service_name,
                    {
                        "message": message,
                        "title": title,
                        "data": data,
                    },
                )
            except Exception as err:
                _LOGGER.error("Failed to notify %s: %s", target, err)


class GroupNotifyService(NotifyPersonService):
    """Notification service for a group of persons."""

    def __init__(
        self,
        hass: HomeAssistant,
        storage: NotifyPersonStorage,
        group_id: str,
        group_config: dict,
    ) -> None:
        """Initialize group notify service."""
        super().__init__(hass, storage)
        self.group_id = group_id
        self.group_config = group_config

    async def async_send_message(self, message: str = "", **kwargs: Any) -> None:
        """Send notification to all persons in this group."""
        title = kwargs.get(ATTR_TITLE, "Home Assistant")
        data = kwargs.get(ATTR_DATA, {})
        
        member_names = self.group_config.get("persons", [])
        if not member_names:
            _LOGGER.warning("No persons in group '%s'", self.group_config.get("name", self.group_id))
            return

        _LOGGER.debug("Sending to group '%s' (%d members)", self.group_config.get("name"), len(member_names))

        persons = self.storage.get_persons()
        
        for member_name in member_names:
            # Find person config by name
            for pid, pconfig in persons.items():
                if pconfig.get("name") == member_name or pid == member_name:
                    service_name = f"notify.person_{pid.replace('person.', '').replace('-', '_').replace(' ', '_').lower()}"
                    try:
                        await self.hass.services.async_call(
                            "notify",
                            service_name.replace("notify.", ""),
                            {
                                "message": message,
                                "title": title,
                                "data": data,
                            },
                        )
                    except Exception as err:
                        _LOGGER.error("Failed to notify %s in group: %s", member_name, err)
                    break
