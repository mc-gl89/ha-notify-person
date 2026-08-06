"""Constants for the Notify Person integration."""

DOMAIN = "notify_person"

# Config keys
CONF_PERSONS = "persons"
CONF_NOTIFY_TARGETS = "notify_targets"
CONF_DEFAULTS = "defaults"

# Notification default keys
CONF_CHANNEL = "channel"
CONF_CRITICALITY = "criticality"
CONF_IMPORTANCE = "importance"
CONF_PERSISTENT = "persistent"
CONF_COLOR = "color"
CONF_PRIORITY = "priority"
CONF_TAG = "tag"
CONF_ACTIONS = "actions"
CONF_SOUND = "sound"
CONF_VIBRATION = "vibration"
CONF_LED = "led"
CONF_TIMEOUT = "timeout"
CONF_INTERruption_level = "interruption_level"  # iOS
CONF_CATEGORY = "category"  # iOS (for action buttons)

# Values
DEFAULT_CHANNEL = "general"
DEFAULT_CRITICALITY = "normal"  # normal, high, critical
DEFAULT_IMPORTANCE = "default"    # default, low, high
DEFAULT_PERSISTENT = False
DEFAULT_COLOR = ""
DEFAULT_PRIORITY = "normal"       # normal, high, low
DEFAULT_TAG = ""
DEFAULT_TIMEOUT = 300             # seconds
DEFAULT_INTERRUPTION_LEVEL = "active"  # iOS: passive, active, time-sensitive, critical
DEFAULT_CATEGORY = ""
DEFAULT_SOUND = "default"
DEFAULT_VIBRATION = "default"
DEFAULT_LED = True

# Services
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
