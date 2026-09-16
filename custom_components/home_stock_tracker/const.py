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
PRODUCT_SEARCH_PATH: Final = "/products/search"
CONFIRM_NEW_PRODUCT_PATH: Final = "/grocery/items/confirm-new-product"
CONFIRM_PRODUCT_ALIAS_PATH: Final = "/grocery/items/confirm-product-alias"
COMPLETE_GROCERY_PURCHASE_PATH: Final = "/inventory/purchases/complete"
INVENTORY_STOCK_PATH: Final = "/inventory/stock"
SERVICE_ADD_GROCERY_ITEM: Final = "add_grocery_item"
SERVICE_SEARCH_PRODUCTS: Final = "search_products"
SERVICE_CONFIRM_GROCERY_NEW_PRODUCT: Final = "confirm_grocery_new_product"
SERVICE_CONFIRM_GROCERY_PRODUCT_ALIAS: Final = "confirm_grocery_product_alias"
SERVICE_CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE: Final = (
    "confirm_grocery_duplicate_as_separate"
)
SERVICE_COMPLETE_GROCERY_PURCHASE: Final = "complete_grocery_purchase"
SERVICE_ADJUST_INVENTORY_STOCK: Final = "adjust_inventory_stock"
ATTR_PRODUCT_NAME: Final = "product_name"
ATTR_CONFIRM: Final = "confirm"
ATTR_REQUESTED_QUANTITY: Final = "requested_quantity"
ATTR_UNIT: Final = "unit"
ATTR_NOTE: Final = "note"
ATTR_QUERY: Final = "query"
ATTR_LIMIT: Final = "limit"
ATTR_PRODUCT: Final = "product"
ATTR_GROCERY_ITEM: Final = "grocery_item"
ATTR_CANONICAL_NAME: Final = "canonical_name"
ATTR_ALIASES: Final = "aliases"
ATTR_CATEGORY: Final = "category"
ATTR_TYPICAL_UNIT: Final = "typical_unit"
ATTR_PRODUCT_TYPE: Final = "product_type"
ATTR_IS_PERISHABLE: Final = "is_perishable"
ATTR_TARGET_PRODUCT_ID: Final = "target_product_id"
ATTR_ALIAS: Final = "alias"
ATTR_PRODUCT_ID: Final = "product_id"
ATTR_GROCERY_ITEM_IDS: Final = "grocery_item_ids"
ATTR_QUANTITY: Final = "quantity"
ATTR_OPERATION: Final = "operation"
PLATFORMS: Final = [Platform.SENSOR]
UPDATE_INTERVAL: Final = timedelta(minutes=5)
