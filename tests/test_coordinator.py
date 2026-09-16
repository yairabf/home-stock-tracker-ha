"""Tests for Home Stock Tracker read coordination."""

from unittest.mock import ANY, AsyncMock, MagicMock, patch
from typing import Literal

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


def _get_session(response: MagicMock) -> MagicMock:
    """Create a session mock that yields one response from GET."""
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = response
    session = MagicMock()
    session.get.return_value = context_manager
    return session


def _catalog_result(outcome: str = "created") -> dict[str, object]:
    """Return the minimal valid source result for a catalog confirmation."""
    return {
        "outcome": outcome,
        "createdItem": {"id": "grocery-1"} if outcome == "created" else None,
        "existingItems": [] if outcome == "created" else [{"id": "grocery-1"}],
        "requestedAddition": {"requestedQuantity": 2},
    }


PRODUCT_ID = "01234567-89ab-4cde-8f01-23456789abcd"
GROCERY_ITEM_ID = "11111111-1111-4111-8111-111111111111"


def _purchase_receipt(
    *,
    product_id: str = PRODUCT_ID,
    grocery_item_ids: list[str] | None = None,
    event_type: str = "PURCHASED",
) -> dict[str, object]:
    """Return a minimal valid receipt for one confirmed grocery purchase."""
    event_id = "22222222-2222-4222-8222-222222222222"
    return {
        "event": {"id": event_id, "productId": product_id, "eventType": event_type},
        "groceryItems": [
            {
                "id": grocery_item_id,
                "status": "purchased",
                "relatedInventoryEventId": event_id,
            }
            for grocery_item_id in grocery_item_ids or [GROCERY_ITEM_ID]
        ],
    }


def _stock_adjustment_receipt(
    *,
    product_id: str = PRODUCT_ID,
    event_type: str = "STOCK_SET",
    event_id: str = "33333333-3333-4333-8333-333333333333",
    stock_product_id: str | None = None,
    recorded_event_id: str | None = None,
) -> dict[str, object]:
    """Return a minimal valid source receipt for one stock adjustment."""
    return {
        "event": {"id": event_id, "productId": product_id, "eventType": event_type},
        "stock": {
            "productId": stock_product_id or product_id,
            "recordedEventId": recorded_event_id or event_id,
        },
    }


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


async def test_search_products_projects_a_valid_source_response(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Catalog search sends one bounded GET and returns only its safe projection."""
    response = MagicMock(status=200)
    response.json = AsyncMock(
        return_value={
            "exactMatch": None,
            "candidates": [
                {
                    "id": "product-1",
                    "canonicalName": "Milk",
                    "aliases": ["Whole milk"],
                    "category": "dairy",
                    "typicalUnit": "carton",
                    "productType": "fast_consumable",
                    "isPerishable": True,
                    "predictionEnabled": True,
                }
            ],
        }
    )
    session = _get_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        result = await coordinator.async_search_products(query="Milk", limit=5)

    assert result == {
        "exact_match": None,
        "candidates": [
            {
                "id": "product-1",
                "canonical_name": "Milk",
                "aliases": ["Whole milk"],
                "category": "dairy",
                "typical_unit": "carton",
                "product_type": "fast_consumable",
                "is_perishable": True,
                "prediction_enabled": True,
            }
        ],
    }
    session.get.assert_called_once_with(
        "http://inventory.local/api/v1/products/search",
        params={"query": "Milk", "limit": 5},
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )


async def test_search_products_rejects_malformed_results(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Untrusted search records cannot reach a Home Assistant service response."""
    response = MagicMock(status=200)
    response.json = AsyncMock(
        return_value={"exactMatch": None, "candidates": ["not-a-candidate"]}
    )
    session = _get_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="invalid response"):
            await coordinator.async_search_products(query="Milk", limit=None)

    assert not coordinator.last_update_success
    assert session.get.call_count == 1


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


async def test_duplicate_decision_posts_the_forced_separate_line_policy(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A duplicate decision has one fixed create-separate POST contract."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"outcome": "created"})
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        outcome = await coordinator.async_confirm_grocery_duplicate_as_separate(
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
                "ifPendingExists": "create_separate",
                "requestedQuantity": 2,
                "unit": "carton",
                "note": "weekly shop",
            },
        },
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )


async def test_duplicate_decision_omits_absent_optional_fields(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Omitted line facts never become an implicit quantity or other field."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value={"outcome": "created"})
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await coordinator.async_confirm_grocery_duplicate_as_separate(
            product_name="Milk",
            requested_quantity=None,
            unit=None,
            note=None,
        )

    assert session.post.call_args.kwargs["json"] == {
        "unknownProductPolicy": "propose_if_missing",
        "productName": "Milk",
        "groceryItem": {"ifPendingExists": "create_separate"},
    }


async def test_complete_grocery_purchase_posts_one_exact_request(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A completed purchase sends no local-only or generic inventory fields."""
    response = MagicMock(status=201)
    response.json = AsyncMock(return_value=_purchase_receipt())
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await coordinator.async_complete_grocery_purchase(
            product_id=PRODUCT_ID,
            grocery_item_ids=[GROCERY_ITEM_ID],
            quantity=2,
            unit="cartons",
        )

    session.post.assert_called_once_with(
        "http://inventory.local/api/v1/inventory/purchases/complete",
        json={
            "productId": PRODUCT_ID,
            "groceryItemIds": [GROCERY_ITEM_ID],
            "quantity": 2,
            "unit": "cartons",
        },
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )


async def test_complete_grocery_purchase_omits_absent_measurements(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Omitted measurement fields are never replaced with inferred values."""
    response = MagicMock(status=201)
    response.json = AsyncMock(return_value=_purchase_receipt())
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await coordinator.async_complete_grocery_purchase(
            product_id=PRODUCT_ID,
            grocery_item_ids=[GROCERY_ITEM_ID],
            quantity=None,
            unit=None,
        )

    assert session.post.call_args.kwargs["json"] == {
        "productId": PRODUCT_ID,
        "groceryItemIds": [GROCERY_ITEM_ID],
    }


@pytest.mark.parametrize(
    "receipt",
    [
        {},
        _purchase_receipt(product_id="unexpected-product"),
        _purchase_receipt(event_type="RESTOCKED"),
        {"event": {"id": "event", "productId": PRODUCT_ID, "eventType": "PURCHASED"}, "groceryItems": []},
        {"event": {"id": "event", "productId": PRODUCT_ID, "eventType": "PURCHASED"}, "groceryItems": [{"id": GROCERY_ITEM_ID, "status": "pending", "relatedInventoryEventId": "event"}]},
        {"event": {"id": "event", "productId": PRODUCT_ID, "eventType": "PURCHASED"}, "groceryItems": [{"id": "unrequested", "status": "purchased", "relatedInventoryEventId": "event"}]},
    ],
)
async def test_complete_grocery_purchase_rejects_mismatched_receipts(
    hass: HomeAssistant, config_entry: ConfigEntry, receipt: dict[str, object]
) -> None:
    """A receipt must prove the exact requested purchase before it is accepted."""
    response = MagicMock(status=201)
    response.json = AsyncMock(return_value=receipt)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="invalid response"):
            await coordinator.async_complete_grocery_purchase(
                product_id=PRODUCT_ID,
                grocery_item_ids=[GROCERY_ITEM_ID],
                quantity=None,
                unit=None,
            )

    assert session.post.call_count == 1
    assert not coordinator.last_update_success


@pytest.mark.parametrize("status", [401, 409])
async def test_complete_grocery_purchase_fails_closed_for_source_errors(
    hass: HomeAssistant, config_entry: ConfigEntry, status: int
) -> None:
    """Authentication and source conflicts make data unavailable without retry."""
    response = MagicMock(status=status)
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        MagicMock(), (), status=status
    )
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError):
            await coordinator.async_complete_grocery_purchase(
                product_id=PRODUCT_ID,
                grocery_item_ids=[GROCERY_ITEM_ID],
                quantity=None,
                unit=None,
            )

    assert session.post.call_count == 1
    assert not coordinator.last_update_success


@pytest.mark.parametrize(
    ("operation", "quantity", "unit", "event_type", "expected_json"),
    [
        ("set", 2, "cartons", "STOCK_SET", {"operation": "set", "quantity": 2, "unit": "cartons"}),
        ("decrement", 1, None, "STOCK_CONSUMED", {"operation": "decrement", "quantity": 1}),
        ("mark_out", None, None, "STOCK_OUT", {"operation": "mark_out"}),
    ],
)
async def test_adjust_inventory_stock_posts_one_exact_request(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    operation: Literal["set", "decrement", "mark_out"],
    quantity: int | None,
    unit: str | None,
    event_type: str,
    expected_json: dict[str, object],
) -> None:
    """Each supported stock operation sends exactly its source contract."""
    response = MagicMock(status=201)
    response.json = AsyncMock(return_value=_stock_adjustment_receipt(event_type=event_type))
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        await coordinator.async_adjust_inventory_stock(
            product_id=PRODUCT_ID,
            operation=operation,
            quantity=quantity,
            unit=unit,
        )

    session.post.assert_called_once_with(
        f"http://inventory.local/api/v1/inventory/stock/{PRODUCT_ID}",
        json=expected_json,
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )


@pytest.mark.parametrize(
    "receipt",
    [
        {},
        {"event": {"id": "event", "productId": PRODUCT_ID, "eventType": "STOCK_SET"}},
        _stock_adjustment_receipt(product_id="unexpected-product"),
        _stock_adjustment_receipt(event_type="STOCK_CONSUMED"),
        _stock_adjustment_receipt(event_id=""),
        _stock_adjustment_receipt(stock_product_id="unexpected-product"),
        _stock_adjustment_receipt(recorded_event_id="other-event"),
    ],
)
async def test_adjust_inventory_stock_rejects_mismatched_receipts(
    hass: HomeAssistant, config_entry: ConfigEntry, receipt: dict[str, object]
) -> None:
    """A receipt must prove the exact requested stock operation before acceptance."""
    response = MagicMock(status=201)
    response.json = AsyncMock(return_value=receipt)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="invalid response"):
            await coordinator.async_adjust_inventory_stock(
                product_id=PRODUCT_ID,
                operation="set",
                quantity=2,
                unit=None,
            )

    assert session.post.call_count == 1
    assert not coordinator.last_update_success


@pytest.mark.parametrize("status", [401, 409])
async def test_adjust_inventory_stock_fails_closed_for_source_errors(
    hass: HomeAssistant, config_entry: ConfigEntry, status: int
) -> None:
    """Authentication and source conflicts are final and leave data unavailable."""
    response = MagicMock(status=status)
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        MagicMock(), (), status=status
    )
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError):
            await coordinator.async_adjust_inventory_stock(
                product_id=PRODUCT_ID,
                operation="set",
                quantity=2,
                unit=None,
            )

    assert session.post.call_count == 1
    assert not coordinator.last_update_success


async def test_adjust_inventory_stock_does_not_retry_connection_failure(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """An uncertain connection failure cannot be retried automatically."""
    session = MagicMock()
    session.post.side_effect = aiohttp.ClientConnectionError
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="inventory adjustment failed"):
            await coordinator.async_adjust_inventory_stock(
                product_id=PRODUCT_ID,
                operation="set",
                quantity=2,
                unit=None,
            )

    assert session.post.call_count == 1
    assert not coordinator.last_update_success


@pytest.mark.parametrize(
    "response_body",
    [
        {"outcome": "confirmation_required"},
        {"outcome": "product_resolution_required"},
    ],
)
async def test_duplicate_decision_returns_known_non_created_outcomes(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    response_body: dict[str, str],
) -> None:
    """Known outcomes remain final decisions without a retry or update error."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value=response_body)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        outcome = await coordinator.async_confirm_grocery_duplicate_as_separate(
            product_name="Milk",
            requested_quantity=None,
            unit=None,
            note=None,
        )

    assert outcome == response_body["outcome"]
    assert coordinator.last_update_success
    assert session.post.call_count == 1


@pytest.mark.parametrize(
    ("method", "kwargs", "path", "payload"),
    [
        (
            "async_confirm_grocery_new_product",
            {
                "product": {
                    "canonical_name": "Milk",
                    "aliases": ["Whole milk"],
                    "category": "dairy",
                    "typical_unit": "carton",
                    "product_type": "fast_consumable",
                    "is_perishable": True,
                },
                "grocery_item": {"requested_quantity": 2, "unit": "carton"},
            },
            "/api/v1/grocery/items/confirm-new-product",
            {
                "product": {
                    "canonicalName": "Milk",
                    "aliases": ["Whole milk"],
                    "category": "dairy",
                    "typicalUnit": "carton",
                    "productType": "fast_consumable",
                    "isPerishable": True,
                },
                "groceryItem": {"requestedQuantity": 2, "unit": "carton"},
            },
        ),
        (
            "async_confirm_grocery_product_alias",
            {
                "target_product_id": "00000000-0000-0000-0000-000000000001",
                "alias": "Whole milk",
                "grocery_item": {"note": "weekly shop"},
            },
            "/api/v1/grocery/items/confirm-product-alias",
            {
                "targetProductId": "00000000-0000-0000-0000-000000000001",
                "alias": "Whole milk",
                "groceryItem": {"note": "weekly shop"},
            },
        ),
    ],
)
async def test_catalog_confirmation_posts_only_final_user_data(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    method: str,
    kwargs: dict[str, object],
    path: str,
    payload: dict[str, object],
) -> None:
    """Each catalog choice sends one exact request with no proposal fields."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value=_catalog_result())
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        outcome = await getattr(coordinator, method)(**kwargs)

    assert outcome == "created"
    session.post.assert_called_once_with(
        f"http://inventory.local{path}",
        json=payload,
        headers={"Authorization": "Bearer secret-token"},
        timeout=ANY,
    )


async def test_catalog_confirmation_accepts_a_pending_duplicate_outcome(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A source duplicate is a known result for the next service-layer step."""
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value=_catalog_result("confirmation_required"))
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        outcome = await coordinator.async_confirm_grocery_product_alias(
            target_product_id="00000000-0000-0000-0000-000000000001",
            alias="Whole milk",
            grocery_item={},
        )

    assert outcome == "confirmation_required"
    assert session.post.call_count == 1


@pytest.mark.parametrize(
    ("response_status", "response_body", "expected_message"),
    [
        (401, _catalog_result(), "authentication failed"),
        (200, {"outcome": "unexpected"}, "invalid response"),
    ],
)
async def test_catalog_confirmation_fails_closed_for_invalid_or_unauthorized_responses(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    response_status: int,
    response_body: dict[str, object],
    expected_message: str,
) -> None:
    """Unknown outcomes and authorization failures are unavailable, not retried."""
    response = MagicMock(status=response_status)
    response.json = AsyncMock(return_value=response_body)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match=expected_message):
            await coordinator.async_confirm_grocery_product_alias(
                target_product_id="00000000-0000-0000-0000-000000000001",
                alias="Whole milk",
                grocery_item={},
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1


async def test_catalog_confirmation_does_not_retry_connection_failures(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A failed catalog POST remains uncertain and is never retried."""
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
        with pytest.raises(HomeAssistantError, match="catalog confirmation failed"):
            await coordinator.async_confirm_grocery_product_alias(
                target_product_id="00000000-0000-0000-0000-000000000001",
                alias="Whole milk",
                grocery_item={},
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1


async def test_catalog_confirmation_fails_closed_for_source_conflicts(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """A stale catalog conflict cannot reveal source details or trigger a retry."""
    response = MagicMock(status=409)
    response.raise_for_status.side_effect = aiohttp.ClientResponseError(
        MagicMock(), (), status=409, message="PRODUCT_NAME_CONFLICT"
    )
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="catalog confirmation failed"):
            await coordinator.async_confirm_grocery_product_alias(
                target_product_id="00000000-0000-0000-0000-000000000001",
                alias="Whole milk",
                grocery_item={},
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1


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


@pytest.mark.parametrize(
    ("response_status", "response_body", "message"),
    [
        (401, {"outcome": "created"}, "authentication failed"),
        (200, {"outcome": "unexpected"}, "invalid response"),
    ],
)
async def test_duplicate_decision_fails_closed_for_uncertain_responses(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    response_status: int,
    response_body: dict[str, str],
    message: str,
) -> None:
    """Unauthorized and invalid duplicate decisions leave data unavailable."""
    response = MagicMock(status=response_status)
    response.json = AsyncMock(return_value=response_body)
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match=message):
            await coordinator.async_confirm_grocery_duplicate_as_separate(
                product_name="Milk",
                requested_quantity=None,
                unit=None,
                note=None,
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1


@pytest.mark.parametrize("failure", ["non_success", "malformed_json"])
async def test_duplicate_decision_fails_closed_for_transport_or_payload_failures(
    hass: HomeAssistant, config_entry: ConfigEntry, failure: str
) -> None:
    """HTTP failures and malformed JSON cannot leave stale data available."""
    response = MagicMock(status=503)
    if failure == "non_success":
        response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            MagicMock(), (), status=503, message="service unavailable"
        )
    else:
        response.status = 200
        response.json = AsyncMock(side_effect=ValueError("not JSON"))
    session = _post_session(response)
    coordinator = HomeStockTrackerCoordinator(hass, config_entry)
    coordinator.last_update_success = True

    with patch(
        "custom_components.home_stock_tracker.coordinator.async_get_clientsession",
        return_value=session,
    ):
        with pytest.raises(HomeAssistantError, match="grocery addition failed"):
            await coordinator.async_confirm_grocery_duplicate_as_separate(
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


async def test_duplicate_decision_does_not_retry_connection_failures(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """An uncertain duplicate-decision POST remains a single request."""
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
            await coordinator.async_confirm_grocery_duplicate_as_separate(
                product_name="Milk",
                requested_quantity=None,
                unit=None,
                note=None,
            )

    assert not coordinator.last_update_success
    assert session.post.call_count == 1
