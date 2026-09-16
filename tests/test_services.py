"""Tests for Home Stock Tracker write-service validation and routing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.home_stock_tracker.const import (
    ATTR_ALIAS,
    ATTR_ALIASES,
    ATTR_CANONICAL_NAME,
    ATTR_CATEGORY,
    ATTR_CONFIRM,
    ATTR_GROCERY_ITEM,
    ATTR_IS_PERISHABLE,
    ATTR_LIMIT,
    ATTR_NOTE,
    ATTR_PRODUCT,
    ATTR_PRODUCT_NAME,
    ATTR_PRODUCT_TYPE,
    ATTR_QUERY,
    ATTR_REQUESTED_QUANTITY,
    ATTR_TARGET_PRODUCT_ID,
    ATTR_TYPICAL_UNIT,
    ATTR_UNIT,
    DOMAIN,
)
from custom_components.home_stock_tracker.services import (
    ADD_GROCERY_ITEM_SCHEMA,
    CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA,
    CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA,
    SEARCH_PRODUCTS_SCHEMA,
    async_handle_add_grocery_item,
    async_handle_confirm_grocery_new_product,
    async_handle_confirm_grocery_product_alias,
    async_handle_search_products,
)


def _product() -> dict[str, object]:
    """Return a complete confirmed product payload."""
    return {
        ATTR_CANONICAL_NAME: "  3% Milk ",
        ATTR_ALIASES: [" Three Percent Milk "],
        ATTR_CATEGORY: " dairy ",
        ATTR_TYPICAL_UNIT: " carton ",
        ATTR_PRODUCT_TYPE: "fast_consumable",
        ATTR_IS_PERISHABLE: True,
    }


@pytest.mark.parametrize(
    ("data"),
    [
        {ATTR_PRODUCT_NAME: "Milk", ATTR_CONFIRM: False},
        {ATTR_PRODUCT_NAME: "   ", ATTR_CONFIRM: True},
        {ATTR_PRODUCT_NAME: "Milk", ATTR_CONFIRM: True, ATTR_UNIT: ""},
        {ATTR_PRODUCT_NAME: "Milk", ATTR_CONFIRM: True, ATTR_NOTE: "  "},
        {
            ATTR_PRODUCT_NAME: "Milk",
            ATTR_CONFIRM: True,
            ATTR_REQUESTED_QUANTITY: 0,
        },
        {
            ATTR_PRODUCT_NAME: "Milk",
            ATTR_CONFIRM: True,
            ATTR_REQUESTED_QUANTITY: float("inf"),
        },
    ],
)
def test_add_grocery_item_schema_rejects_unconfirmed_or_invalid_data(data) -> None:
    """Invalid service data cannot reach the write transport."""
    with pytest.raises(vol.Invalid):
        ADD_GROCERY_ITEM_SCHEMA(data)


@pytest.mark.parametrize(
    "data",
    [
        {ATTR_QUERY: "   "},
        {ATTR_QUERY: "Milk", ATTR_LIMIT: 0},
        {ATTR_QUERY: "Milk", ATTR_LIMIT: 21},
        {ATTR_QUERY: "Milk", ATTR_LIMIT: True},
    ],
)
def test_search_products_schema_rejects_invalid_data(data) -> None:
    """Search data must be meaningful before the read transport is called."""
    with pytest.raises(vol.Invalid):
        SEARCH_PRODUCTS_SCHEMA(data)


@pytest.mark.parametrize(
    "data",
    [
        {ATTR_CONFIRM: False, ATTR_PRODUCT: _product(), ATTR_GROCERY_ITEM: {}},
        {
            ATTR_CONFIRM: True,
            ATTR_PRODUCT: {**_product(), ATTR_CATEGORY: "  "},
            ATTR_GROCERY_ITEM: {},
        },
        {
            ATTR_CONFIRM: True,
            ATTR_PRODUCT: {**_product(), ATTR_PRODUCT_TYPE: "unknown"},
            ATTR_GROCERY_ITEM: {},
        },
        {
            ATTR_CONFIRM: True,
            ATTR_PRODUCT: _product(),
            ATTR_GROCERY_ITEM: {ATTR_REQUESTED_QUANTITY: 0},
        },
        {
            ATTR_CONFIRM: True,
            ATTR_TARGET_PRODUCT_ID: "not-a-uuid",
            ATTR_ALIAS: "Milk",
            ATTR_GROCERY_ITEM: {},
        },
        {
            ATTR_CONFIRM: True,
            ATTR_TARGET_PRODUCT_ID: "00000000-0000-0000-0000-000000000001",
            ATTR_ALIAS: "   ",
            ATTR_GROCERY_ITEM: {},
        },
    ],
)
def test_catalog_confirmation_schemas_reject_invalid_data(data) -> None:
    """Catalog writes require full, explicit, local confirmation."""
    schema = (
        CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA
        if ATTR_PRODUCT in data
        else CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA
    )
    with pytest.raises(vol.Invalid):
        schema(data)


async def test_add_grocery_item_routes_validated_data_to_coordinator(hass) -> None:
    """A created item refreshes after validated data reaches the coordinator."""
    coordinator = AsyncMock()
    coordinator.async_add_grocery_item.return_value = "created"
    hass.data[DOMAIN] = {"entry-id": coordinator}
    call = ServiceCall(
        hass,
        DOMAIN,
        "add_grocery_item",
        ADD_GROCERY_ITEM_SCHEMA(
            {
                ATTR_PRODUCT_NAME: "  Milk ",
                ATTR_CONFIRM: True,
                ATTR_REQUESTED_QUANTITY: 2,
                ATTR_UNIT: " carton ",
                ATTR_NOTE: " weekly shop ",
            }
        ),
    )

    await async_handle_add_grocery_item(hass, call)

    coordinator.async_add_grocery_item.assert_awaited_once_with(
        product_name="Milk",
        requested_quantity=2,
        unit="carton",
        note="weekly shop",
    )
    coordinator.async_request_refresh.assert_awaited_once_with()


async def test_catalog_services_route_validated_data_to_coordinator(hass) -> None:
    """The search and confirmation services are thin coordinator routes."""
    coordinator = AsyncMock()
    coordinator.async_search_products.return_value = {
        "exact_match": None,
        "candidates": [],
    }
    coordinator.async_confirm_grocery_new_product.return_value = "created"
    coordinator.async_confirm_grocery_product_alias.return_value = "created"
    hass.data[DOMAIN] = {"entry-id": coordinator}

    search_call = ServiceCall(
        hass,
        DOMAIN,
        "search_products",
        SEARCH_PRODUCTS_SCHEMA({ATTR_QUERY: "  Milk ", ATTR_LIMIT: 5}),
    )
    search_response = await async_handle_search_products(hass, search_call)

    new_product_call = ServiceCall(
        hass,
        DOMAIN,
        "confirm_grocery_new_product",
        CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA(
            {
                ATTR_CONFIRM: True,
                ATTR_PRODUCT: _product(),
                ATTR_GROCERY_ITEM: {ATTR_UNIT: " carton "},
            }
        ),
    )
    await async_handle_confirm_grocery_new_product(hass, new_product_call)

    alias_call = ServiceCall(
        hass,
        DOMAIN,
        "confirm_grocery_product_alias",
        CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA(
            {
                ATTR_CONFIRM: True,
                ATTR_TARGET_PRODUCT_ID: "00000000-0000-0000-0000-000000000001",
                ATTR_ALIAS: " Three Percent Milk ",
                ATTR_GROCERY_ITEM: {},
            }
        ),
    )
    await async_handle_confirm_grocery_product_alias(hass, alias_call)

    assert search_response == {"exact_match": None, "candidates": []}
    coordinator.async_search_products.assert_awaited_once_with(query="Milk", limit=5)
    coordinator.async_confirm_grocery_new_product.assert_awaited_once_with(
        product={
            ATTR_CANONICAL_NAME: "3% Milk",
            ATTR_ALIASES: ["Three Percent Milk"],
            ATTR_CATEGORY: "dairy",
            ATTR_TYPICAL_UNIT: "carton",
            ATTR_PRODUCT_TYPE: "fast_consumable",
            ATTR_IS_PERISHABLE: True,
        },
        grocery_item={ATTR_UNIT: "carton"},
    )
    coordinator.async_confirm_grocery_product_alias.assert_awaited_once_with(
        target_product_id="00000000-0000-0000-0000-000000000001",
        alias="Three Percent Milk",
        grocery_item={},
    )
    assert coordinator.async_request_refresh.await_count == 2


@pytest.mark.parametrize("service", ["new_product", "product_alias"])
async def test_catalog_confirmation_does_not_refresh_pending_duplicates(
    hass, service: str
) -> None:
    """A duplicate result cannot cause a second catalog or grocery mutation."""
    coordinator = AsyncMock()
    coordinator.async_confirm_grocery_new_product.return_value = (
        "confirmation_required"
    )
    coordinator.async_confirm_grocery_product_alias.return_value = (
        "confirmation_required"
    )
    hass.data[DOMAIN] = {"entry-id": coordinator}

    if service == "new_product":
        call = ServiceCall(
            hass,
            DOMAIN,
            "confirm_grocery_new_product",
            CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA(
                {
                    ATTR_CONFIRM: True,
                    ATTR_PRODUCT: _product(),
                    ATTR_GROCERY_ITEM: {},
                }
            ),
        )
        handler = async_handle_confirm_grocery_new_product
    else:
        call = ServiceCall(
            hass,
            DOMAIN,
            "confirm_grocery_product_alias",
            CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA(
                {
                    ATTR_CONFIRM: True,
                    ATTR_TARGET_PRODUCT_ID: "00000000-0000-0000-0000-000000000001",
                    ATTR_ALIAS: "Whole milk",
                    ATTR_GROCERY_ITEM: {},
                }
            ),
        )
        handler = async_handle_confirm_grocery_product_alias

    with pytest.raises(HomeAssistantError, match="needs a separate decision"):
        await handler(hass, call)

    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        ("confirmation_required", "already exists"),
        ("product_resolution_required", "needs product resolution"),
    ],
)
async def test_add_grocery_item_does_not_refresh_non_created_outcomes(
    hass, outcome: str, message: str
) -> None:
    """Duplicate and unresolved outcomes cannot cause a follow-up mutation."""
    coordinator = AsyncMock()
    coordinator.async_add_grocery_item.return_value = outcome
    hass.data[DOMAIN] = {"entry-id": coordinator}
    call = ServiceCall(
        hass,
        DOMAIN,
        "add_grocery_item",
        ADD_GROCERY_ITEM_SCHEMA({ATTR_PRODUCT_NAME: "Milk", ATTR_CONFIRM: True}),
    )

    with pytest.raises(HomeAssistantError, match=message):
        await async_handle_add_grocery_item(hass, call)

    coordinator.async_request_refresh.assert_not_awaited()
