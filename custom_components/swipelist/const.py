"""Constants for SwipeList integration."""

DOMAIN = "swipelist"

# Configuration keys
CONF_API_URL = "api_url"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_REFRESH_TOKEN = "refresh_token"

# Default values
DEFAULT_API_URL = "https://swipelist.corsch.net/api"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# API Endpoints
ENDPOINT_LOGIN = "/auth/login"
ENDPOINT_REFRESH = "/auth/refresh"
ENDPOINT_LISTS = "/lists"
ENDPOINT_LIST_ITEMS = "/lists/{list_id}/items"
ENDPOINT_ITEM = "/lists/{list_id}/items/{item_id}"

# Attributes
ATTR_LIST_ID = "list_id"
ATTR_LIST_NAME = "list_name"
ATTR_ITEM_COUNT = "item_count"
ATTR_CHECKED_COUNT = "checked_count"
ATTR_SHARED_WITH = "shared_with"
