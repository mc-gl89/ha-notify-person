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
CONF_ACTIONS = "actions"
CONF_PERSISTENT = "persistent"

# Individual action button fields (UI-friendly, no YAML)
CONF_ACTION_1_ID = "action_1_id"
CONF_ACTION_1_TITLE = "action_1_title"
CONF_ACTION_2_ID = "action_2_id"
CONF_ACTION_2_TITLE = "action_2_title"
CONF_ACTION_3_ID = "action_3_id"
CONF_ACTION_3_TITLE = "action_3_title"
CONF_ACTION_4_ID = "action_4_id"
CONF_ACTION_4_TITLE = "action_4_title"
CONF_ACTION_5_ID = "action_5_id"
CONF_ACTION_5_TITLE = "action_5_title"

CONF_TTL = "ttl"
CONF_COLOR = "color"
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
