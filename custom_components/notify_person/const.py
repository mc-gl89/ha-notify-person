"""Constants for the Notify Person integration."""

DOMAIN = "notify_person"

# Config keys
CONF_PERSONS = "persons"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_DEFAULTS = "defaults"

# Notification data keys
CONF_CHANNEL = "channel"
CONF_PRIORITY = "priority"
CONF_CRITICAL = "critical"
CONF_TAG = "tag"
CONF_COLOR = "color"
CONF_PERSISTENT = "persistent"
CONF_TTL = "ttl"
CONF_GROUP = "group"
CONF_IMPORTANCE = "importance"
CONF_STICKY = "sticky"
CONF_IMAGE = "image"
CONF_ACTION_URI = "action_uri"

# Values
DEFAULT_CHANNEL = "General"
DEFAULT_PRIORITY = "normal"
DEFAULT_CRITICAL = False
DEFAULT_PERSISTENT = False
DEFAULT_TTL = None
DEFAULT_STICKY = False

# Services
SERVICE_SIMPLE_NOTIFY = "simple_notify"
SERVICE_ADVANCED_NOTIFY = "advanced_notify"
SERVICE_ADD_GROUP = "add_group"
SERVICE_REMOVE_GROUP = "remove_group"
SERVICE_UPDATE_PERSON = "update_person"
SERVICE_RELOAD = "reload"

# Attributes
ATTR_MESSAGE = "message"
ATTR_TITLE = "title"
ATTR_DATA = "data"
ATTR_TARGETS = "targets"
ATTR_PERSON = "person"
ATTR_GROUP = "group"

# Storage
STORAGE_KEY = f"{DOMAIN}_storage"
STORAGE_VERSION = 1
