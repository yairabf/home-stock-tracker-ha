"""Constants for the Home Stock Tracker integration."""

from typing import Final

from datetime import timedelta
from homeassistant.const import Platform

DOMAIN: Final = "home_stock_tracker"
CONF_BASE_URL: Final = "base_url"
CONF_API_TOKEN: Final = "api_token"
DEFAULT_TITLE: Final = "Home Stock Tracker"
API_VERSION_PATH: Final = "/api/v1"
GROCERY_ITEMS_PATH: Final = "/grocery/items"
INVENTORY_PATH: Final = "/inventory"
LOW_STOCK_PATH: Final = "/inventory/predictions/low-stock"
PLATFORMS: Final = [Platform.SENSOR]
UPDATE_INTERVAL: Final = timedelta(minutes=5)
