"""Tests for Home Stock Tracker read coordination."""

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.home_stock_tracker.const import CONF_API_TOKEN
from custom_components.home_stock_tracker.coordinator import HomeStockTrackerCoordinator


async def test_refresh_publishes_all_read_models_atomically(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """One refresh exposes all three documented read responses."""
    base_url = config_entry.data["base_url"]
    headers = {"Authorization": f"Bearer {config_entry.data[CONF_API_TOKEN]}"}
    aioclient_mock.get(f"{base_url}/api/v1/grocery/items", json=[], headers=headers)
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory", json={"current": [], "uncertain": []}, headers=headers
    )
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory/predictions/low-stock", json={"recommendations": []}, headers=headers
    )

    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data == {"grocery": [], "inventory": {"current": [], "uncertain": []}, "recommendations": []}


async def test_refresh_rejects_unauthorized_reads(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """An authentication rejection starts Home Assistant reauthentication."""
    aioclient_mock.get(
        f"{config_entry.data['base_url']}/api/v1/grocery/items", status=401
    )

    with pytest.raises(ConfigEntryAuthFailed):
        await HomeStockTrackerCoordinator(hass, config_entry)._async_update_data()


async def test_refresh_rejects_malformed_responses_without_partial_data(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """Malformed read models leave the coordinator unavailable."""
    base_url = config_entry.data["base_url"]
    aioclient_mock.get(f"{base_url}/api/v1/grocery/items", json={"items": []})
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory", json={"current": [], "uncertain": []}
    )
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory/predictions/low-stock",
        json={"recommendations": []},
    )

    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with pytest.raises(UpdateFailed, match="invalid response"):
        await coordinator._async_update_data()

    assert coordinator.data is None


async def test_refresh_rejects_service_failures_without_partial_data(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """A non-success response prevents all sensor data from publishing."""
    base_url = config_entry.data["base_url"]
    aioclient_mock.get(f"{base_url}/api/v1/grocery/items", status=503)
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory", json={"current": [], "uncertain": []}
    )
    aioclient_mock.get(
        f"{base_url}/api/v1/inventory/predictions/low-stock",
        json={"recommendations": []},
    )

    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with pytest.raises(UpdateFailed, match="Cannot reach"):
        await coordinator._async_update_data()

    assert coordinator.data is None
