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
    # Platform notify service is not used directly in this integration.
    # Services are registered dynamically in __init__.py
    return None
