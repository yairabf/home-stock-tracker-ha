"""Tests for Home Stock Tracker read coordination."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.home_stock_tracker.const import CONF_API_TOKEN
from custom_components.home_stock_tracker.coordinator import HomeStockTrackerCoordinator


def _post_session(response: MagicMock) -> MagicMock:
    """Create a session mock that yields one response from POST."""
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = response
    session = MagicMock()
    session.post.return_value = context_manager
    return session


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


async def test_add_grocery_item_posts_the_fixed_safe_policy(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A grocery-add invocation makes exactly one constrained POST request."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"outcome": "created"})
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        outcome = await coordinator.async_add_grocery_item(
            product_name="Milk",
            requested_quantity=2,
            unit="carton",
            note="weekly shop",
        )

    assert outcome == "created"
    session.post.assert_called_once_with(
        "http://inventory.local/api/v1/grocery/items",
        json={
            "unknownProductPolicy": "propose_if_missing",
            "productName": "Milk",
            "groceryItem": {
                "ifPendingExists": "return_existing",
                "requestedQuantity": 2,
                "unit": "carton",
                "note": "weekly shop",
            },
        },
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )
    assert session.post.call_args.kwargs["timeout"].total == 10


@pytest.mark.parametrize(
    ("response_status", "response_body"),
    [
        (200, {"outcome": "unexpected"}),
        (200, {"missing": "outcome"}),
        (401, {"outcome": "created"}),
    ],
)
async def test_add_grocery_item_fails_closed_for_invalid_or_unauthorized_responses(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    response_status: int,
    response_body: dict[str, str],
) -> None:
    """Invalid and unauthorized responses make the coordinator unavailable."""
    response = MagicMock(status=response_status)
    response.json = AsyncMock(return_value=response_body)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError):
            await coordinator.async_add_grocery_item(
                product_name="Milk",
                requested_quantity=None,
                unit=None,
                note=None,
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1


async def test_add_grocery_item_does_not_retry_connection_failures(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A failed POST remains uncertain and is never retried."""
    context_manager = AsyncMock()
    context_manager.__aenter__.side_effect = aiohttp.ClientConnectionError()
    session = MagicMock()
    session.post.return_value = context_manager
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="grocery addition failed"):
            await coordinator.async_add_grocery_item(
                product_name="Milk",
                requested_quantity=None,
                unit=None,
                note=None,
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1
