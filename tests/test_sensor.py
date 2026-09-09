"""Tests for Home Stock Tracker sensor entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def test_sensors_publish_records_and_stable_unique_ids(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """A successful shared refresh publishes all service-owned records."""
    base_url = config_entry.data["base_url"]
    grocery = [{"id": "grocery-1", "name": "Milk", "quantity": 2, "unit": "carton"}]
    current = [{"productId": "milk", "quantity": 2, "unit": "carton", "state": "current"}]
    uncertain = [{"productId": "eggs", "confidence": 0.5, "state": "uncertain"}]
    recommendations = [{"productId": "milk", "reason": "Running low"}]
    aioclient_mock.get(f"{base_url}/api/v1/grocery/items", json=grocery)
    aioclient_mock.get(f"{base_url}/api/v1/inventory", json={"current": current, "uncertain": uncertain})
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory/predictions/low-stock",
        json={"recommendations": recommendations},
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    pending_groceries = hass.states.get("sensor.pending_groceries")
    tracked_inventory = hass.states.get("sensor.tracked_inventory")
    low_stock = hass.states.get("sensor.low_stock_recommendations")

    assert pending_groceries is not None
    assert pending_groceries.state == "1"
    assert pending_groceries.attributes["items"] == grocery
    assert tracked_inventory is not None
    assert tracked_inventory.state == "2"
    assert tracked_inventory.attributes["current"] == current
    assert tracked_inventory.attributes["uncertain"] == uncertain
    assert low_stock is not None
    assert low_stock.state == "1"
    assert low_stock.attributes["recommendations"] == recommendations

    registry = er.async_get(hass)
    assert registry.async_get("sensor.pending_groceries").unique_id == f"{config_entry.entry_id}_grocery"
    assert registry.async_get("sensor.tracked_inventory").unique_id == f"{config_entry.entry_id}_inventory"
    assert registry.async_get("sensor.low_stock_recommendations").unique_id == f"{config_entry.entry_id}_low_stock"


async def test_sensors_show_zero_for_empty_data_and_unavailable_after_failed_refresh(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """Empty successful data is distinct from an unavailable coordinator."""
    base_url = config_entry.data["base_url"]
    aioclient_mock.get(f"{base_url}/api/v1/grocery/items", json=[])
    aioclient_mock.get(f"{base_url}/api/v1/inventory", json={"current": [], "uncertain": []})
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory/predictions/low-stock", json={"recommendations": []}
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.pending_groceries").state == "0"
    assert hass.states.get("sensor.tracked_inventory").state == "0"
    assert hass.states.get("sensor.low_stock_recommendations").state == "0"

    coordinator = hass.data[config_entry.domain][config_entry.entry_id]
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    assert hass.states.get("sensor.pending_groceries").state == "unavailable"
    assert hass.states.get("sensor.tracked_inventory").state == "unavailable"
    assert hass.states.get("sensor.low_stock_recommendations").state == "unavailable"
