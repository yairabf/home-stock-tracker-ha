"""Home Stock Tracker integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, SERVICE_ADD_GROCERY_ITEM
from .coordinator import HomeStockTrackerCoordinator
from .services import ADD_GROCERY_ITEM_SCHEMA, async_handle_add_grocery_item


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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Home Stock Tracker config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_ADD_GROCERY_ITEM)
    return unloaded
