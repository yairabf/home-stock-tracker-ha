"""Home Assistant service validation and routing."""

from __future__ import annotations

import math
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_CONFIRM,
    ATTR_NOTE,
    ATTR_PRODUCT_NAME,
    ATTR_REQUESTED_QUANTITY,
    ATTR_UNIT,
    DOMAIN,
)
from .coordinator import HomeStockTrackerCoordinator


def _nonempty_string(value: Any) -> str:
    """Normalize a required or optional non-empty string."""
    if not isinstance(value, str):
        raise vol.Invalid("must be a string")
    normalized = value.strip()
    if not normalized:
        raise vol.Invalid("must not be empty")
    return normalized


def _confirmed(value: Any) -> bool:
    """Require an explicit true confirmation value."""
    if value is not True:
        raise vol.Invalid("must be true")
    return True


def _positive_finite_number(value: Any) -> float | int:
    """Reject booleans, non-numbers, and non-positive finite quantities."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise vol.Invalid("must be a positive finite number")
    if not math.isfinite(value) or value <= 0:
        raise vol.Invalid("must be a positive finite number")
    return value


ADD_GROCERY_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PRODUCT_NAME): _nonempty_string,
        vol.Required(ATTR_CONFIRM): _confirmed,
        vol.Optional(ATTR_REQUESTED_QUANTITY): _positive_finite_number,
        vol.Optional(ATTR_UNIT): _nonempty_string,
        vol.Optional(ATTR_NOTE): _nonempty_string,
    }
)


async def async_handle_add_grocery_item(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Route a validated grocery-add request to the configured coordinator."""
    coordinators: dict[str, HomeStockTrackerCoordinator] = hass.data[DOMAIN]
    if len(coordinators) != 1:
        raise HomeAssistantError("Home Stock Tracker is not configured")

    coordinator = next(iter(coordinators.values()))
    outcome = await coordinator.async_add_grocery_item(
        product_name=call.data[ATTR_PRODUCT_NAME],
        requested_quantity=call.data.get(ATTR_REQUESTED_QUANTITY),
        unit=call.data.get(ATTR_UNIT),
        note=call.data.get(ATTR_NOTE),
    )
    if outcome == "created":
        await coordinator.async_request_refresh()
        return
    if outcome == "confirmation_required":
        raise HomeAssistantError("A pending grocery item already exists")
    if outcome == "product_resolution_required":
        raise HomeAssistantError("The grocery item needs product resolution")
    raise HomeAssistantError("Home Stock Tracker returned an invalid response")
