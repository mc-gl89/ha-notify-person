"""Constants for the Notify Person integration."""

DOMAIN = "notify_person"

# Config keys
CONF_PERSONS = "persons"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_DEFAULT_CHANNEL = "default_channel"
CONF_DEFAULT_CRITICALITY = "default_criticality"
CONF_DEFAULT_IMPORTANCE = "default_importance"

# Default values
DEFAULT_CHANNEL = "general"
DEFAULT_CRITICALITY = "normal"  # normal, high, critical
DEFAULT_IMPORTANCE = "default"   # default, low, high

# Services
SERVICE_NOTIFY_GROUP = "notify_group"
SERVICE_NOTIFY_PERSON = "notify_person"

# Attributes
ATTR_MESSAGE = "message"
ATTR_TITLE = "title"
ATTR_DATA = "data"
ATTR_TARGETS = "targets"
ATTR_CHANNEL = "channel"
ATTR_CRITICALITY = "criticality"
ATTR_IMPORTANCE = "importance"

# Storage
STORAGE_KEY = f"{DOMAIN}_storage"
STORAGE_VERSION = 1
