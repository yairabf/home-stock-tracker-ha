"""Home Assistant service validation and routing."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_CONFIRM,
    ATTR_ALIASES,
    ATTR_ALIAS,
    ATTR_CANONICAL_NAME,
    ATTR_CATEGORY,
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


def _positive_integer(value: Any) -> int:
    """Accept an integral search limit within the source-service range."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20:
        raise vol.Invalid("must be an integer from 1 through 20")
    return value


def _boolean(value: Any) -> bool:
    """Require a real boolean instead of coercing service data."""
    if not isinstance(value, bool):
        raise vol.Invalid("must be a boolean")
    return value


def _uuid(value: Any) -> str:
    """Normalize a UUID used to select one exact catalog candidate."""
    if not isinstance(value, str):
        raise vol.Invalid("must be a UUID")
    try:
        return str(UUID(value))
    except ValueError as error:
        raise vol.Invalid("must be a UUID") from error


GROCERY_ITEM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_REQUESTED_QUANTITY): _positive_finite_number,
        vol.Optional(ATTR_UNIT): _nonempty_string,
        vol.Optional(ATTR_NOTE): _nonempty_string,
    }
)

PRODUCT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CANONICAL_NAME): _nonempty_string,
        vol.Required(ATTR_ALIASES): [_nonempty_string],
        vol.Required(ATTR_CATEGORY): _nonempty_string,
        vol.Required(ATTR_TYPICAL_UNIT): vol.Any(None, _nonempty_string),
        vol.Required(ATTR_PRODUCT_TYPE): vol.In(
            {
                "fast_consumable",
                "pantry_staple",
                "household_consumable",
                "discrete_consumable",
            }
        ),
        vol.Required(ATTR_IS_PERISHABLE): _boolean,
    }
)


ADD_GROCERY_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PRODUCT_NAME): _nonempty_string,
        vol.Required(ATTR_CONFIRM): _confirmed,
        vol.Optional(ATTR_REQUESTED_QUANTITY): _positive_finite_number,
        vol.Optional(ATTR_UNIT): _nonempty_string,
        vol.Optional(ATTR_NOTE): _nonempty_string,
    }
)

SEARCH_PRODUCTS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_QUERY): _nonempty_string,
        vol.Optional(ATTR_LIMIT): _positive_integer,
    }
)

CONFIRM_GROCERY_NEW_PRODUCT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIRM): _confirmed,
        vol.Required(ATTR_PRODUCT): PRODUCT_SCHEMA,
        vol.Required(ATTR_GROCERY_ITEM): GROCERY_ITEM_SCHEMA,
    }
)

CONFIRM_GROCERY_PRODUCT_ALIAS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIRM): _confirmed,
        vol.Required(ATTR_TARGET_PRODUCT_ID): _uuid,
        vol.Required(ATTR_ALIAS): _nonempty_string,
        vol.Required(ATTR_GROCERY_ITEM): GROCERY_ITEM_SCHEMA,
    }
)

CONFIRM_GROCERY_DUPLICATE_AS_SEPARATE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PRODUCT_NAME): _nonempty_string,
        vol.Required(ATTR_CONFIRM): _confirmed,
        vol.Optional(ATTR_REQUESTED_QUANTITY): _positive_finite_number,
        vol.Optional(ATTR_UNIT): _nonempty_string,
        vol.Optional(ATTR_NOTE): _nonempty_string,
    }
)


def _coordinator(hass: HomeAssistant) -> HomeStockTrackerCoordinator:
    """Return the sole configured coordinator for an explicit service call."""
    coordinators: dict[str, HomeStockTrackerCoordinator] = hass.data[DOMAIN]
    if len(coordinators) != 1:
        raise HomeAssistantError("Home Stock Tracker is not configured")
    return next(iter(coordinators.values()))


async def async_handle_add_grocery_item(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Route a validated grocery-add request to the configured coordinator."""
    coordinator = _coordinator(hass)
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


async def async_handle_search_products(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Return validated catalog candidates through a response-only service."""
    return await _coordinator(hass).async_search_products(
        query=call.data[ATTR_QUERY], limit=call.data.get(ATTR_LIMIT)
    )


async def async_handle_confirm_grocery_new_product(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Send final user-approved facts for one new grocery product."""
    coordinator = _coordinator(hass)
    outcome = await coordinator.async_confirm_grocery_new_product(
        product=call.data[ATTR_PRODUCT],
        grocery_item=call.data[ATTR_GROCERY_ITEM],
    )
    await _handle_catalog_confirmation_outcome(coordinator, outcome)


async def async_handle_confirm_grocery_product_alias(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Attach a user-approved alias to one exact product before adding it."""
    coordinator = _coordinator(hass)
    outcome = await coordinator.async_confirm_grocery_product_alias(
        target_product_id=call.data[ATTR_TARGET_PRODUCT_ID],
        alias=call.data[ATTR_ALIAS],
        grocery_item=call.data[ATTR_GROCERY_ITEM],
    )
    await _handle_catalog_confirmation_outcome(coordinator, outcome)


async def async_handle_confirm_grocery_duplicate_as_separate(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Create one separately confirmed pending grocery line."""
    coordinator = _coordinator(hass)
    outcome = await coordinator.async_confirm_grocery_duplicate_as_separate(
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


async def _handle_catalog_confirmation_outcome(
    coordinator: HomeStockTrackerCoordinator,
    outcome: str,
) -> None:
    """Refresh only a created grocery line; leave duplicate decisions untouched."""
    if outcome == "created":
        await coordinator.async_request_refresh()
        return
    if outcome == "confirmation_required":
        raise HomeAssistantError(
            "The catalog decision was saved, but the pending grocery item needs a separate decision"
        )
    raise HomeAssistantError("Home Stock Tracker returned an invalid response")
