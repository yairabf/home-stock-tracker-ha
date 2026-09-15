"""Tests for Home Stock Tracker write-service validation and routing."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.home_stock_tracker.const import (
    ATTR_CONFIRM,
    ATTR_NOTE,
    ATTR_PRODUCT_NAME,
    ATTR_REQUESTED_QUANTITY,
    ATTR_UNIT,
    DOMAIN,
)
from custom_components.home_stock_tracker.services import (
    ADD_GROCERY_ITEM_SCHEMA,
    async_handle_add_grocery_item,
)


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
