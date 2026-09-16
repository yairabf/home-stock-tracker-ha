"""Home Stock Tracker integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, SupportsResponse

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_GROCERY_ITEM,
    SERVICE_CONFIRM_GROCERY_NEW_PRODUCT,
    SERVICE_CONFIRM_GROCERY_PRODUCT_ALIAS,
    SERVICE_CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE,
    SERVICE_SEARCH_PRODUCTS,
    SERVICE_COMPLETE_GROCERY_PURCHASE,
)
from .coordinator import HomeStockTrackerCoordinator
from .services import (
    ADD_GROCERY_ITEM_SCHEMA,
    CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA,
    CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA,
    CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE_SCHEMA,
    COMPLETE_GROCERY_PURCHASE_SCHEMA,
    SEARCH_PRODUCTS_SCHEMA,
    async_handle_add_grocery_item,
    async_handle_confirm_grocery_new_product,
    async_handle_confirm_grocery_product_alias,
    async_handle_confirm_grocery_duplicate_as_separate,
    async_handle_complete_grocery_purchase,
    async_handle_search_products,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Stock Tracker from a config entry."""
    coordinator = HomeStockTrackerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    if not hass.services.has_service(DOMAIN, SERVICE_ADD_GROCERY_ITEM):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_GROCERY_ITEM,
            lambda call: async_handle_add_grocery_item(hass, call),
            schema=ADD_GROCERY_ITEM_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEARCH_PRODUCTS,
            lambda call: async_handle_search_products(hass, call),
            schema=SEARCH_PRODUCTS_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_CONFIRM_GROCERY_NEW_PRODUCT,
            lambda call: async_handle_confirm_grocery_new_product(hass, call),
            schema=CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_CONFIRM_GROCERY_PRODUCT_ALIAS,
            lambda call: async_handle_confirm_grocery_product_alias(hass, call),
            schema=CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE,
            lambda call: async_handle_confirm_grocery_duplicate_as_separate(hass, call),
            schema=CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE_SCHEMA,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_COMPLETE_GROCERY_PURCHASE,
            lambda call: async_handle_complete_grocery_purchase(hass, call),
            schema=COMPLETE_GROCERY_PURCHASE_SCHEMA,
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Home Stock Tracker config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_ADD_GROCERY_ITEM)
            hass.services.async_remove(DOMAIN, SERVICE_SEARCH_PRODUCTS)
            hass.services.async_remove(DOMAIN, SERVICE_CONFIRM_GROCERY_NEW_PRODUCT)
            hass.services.async_remove(DOMAIN, SERVICE_CONFIRM_GROCERY_PRODUCT_ALIAS)
            hass.services.async_remove(
                DOMAIN, SERVICE_CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE
            )
            hass.services.async_remove(DOMAIN, SERVICE_COMPLETE_GROCERY_PURCHASE)
    return unloaded
