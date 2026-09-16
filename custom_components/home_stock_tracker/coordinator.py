"""Read-only data coordinator for Home Stock Tracker."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any, Literal

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_VERSION_PATH,
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONFIRM_NEW_PRODUCT_PATH,
    CONFIRM_PRODUCT_ALIAS_PATH,
    COMPLETE_GROCERY_PURCHASE_PATH,
    DOMAIN,
    GROCERY_ITEMS_PATH,
    INVENTORY_PATH,
    LOW_STOCK_PATH,
    PRODUCT_SEARCH_PATH,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class HomeStockTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch all Home Stock Tracker read state atomically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self._base_url = entry.data[CONF_BASE_URL]
        self._headers = {"Authorization": f"Bearer {entry.data[CONF_API_TOKEN]}"}

    async def async_search_products(
        self, *, query: str, limit: int | None
    ) -> dict[str, Any]:
        """Return a validated, read-only projection of catalog search results."""
        params: dict[str, str | int] = {"query": query}
        if limit is not None:
            params["limit"] = limit

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{self._base_url}{API_VERSION_PATH}{PRODUCT_SEARCH_PATH}",
                params=params,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    self._set_write_failure("Home Stock Tracker authentication failed")
                    raise HomeAssistantError(
                        "Home Stock Tracker authentication failed"
                    )
                response.raise_for_status()
                result = await response.json()
        except HomeAssistantError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            self._set_write_failure("Home Stock Tracker catalog search failed")
            raise HomeAssistantError(
                "Home Stock Tracker catalog search failed"
            ) from None

        try:
            return self._catalog_search_projection(result)
        except ValueError:
            self._set_write_failure("Home Stock Tracker returned an invalid response")
            raise HomeAssistantError(
                "Home Stock Tracker returned an invalid response"
            ) from None

    async def async_confirm_grocery_new_product(
        self, *, product: dict[str, Any], grocery_item: dict[str, Any]
    ) -> Literal["created", "confirmation_required"]:
        """Confirm final product facts and add one grocery item without retries."""
        return await self._confirm_grocery_catalog_decision(
            CONFIRM_NEW_PRODUCT_PATH,
            {
                "product": {
                    "canonicalName": product["canonical_name"],
                    "aliases": product["aliases"],
                    "category": product["category"],
                    "typicalUnit": product["typical_unit"],
                    "productType": product["product_type"],
                    "isPerishable": product["is_perishable"],
                },
                "groceryItem": self._grocery_item_payload(grocery_item),
            },
        )

    async def async_confirm_grocery_product_alias(
        self,
        *,
        target_product_id: str,
        alias: str,
        grocery_item: dict[str, Any],
    ) -> Literal["created", "confirmation_required"]:
        """Confirm an alias for one exact product and add without retries."""
        return await self._confirm_grocery_catalog_decision(
            CONFIRM_PRODUCT_ALIAS_PATH,
            {
                "targetProductId": target_product_id,
                "alias": alias,
                "groceryItem": self._grocery_item_payload(grocery_item),
            },
        )

    async def _confirm_grocery_catalog_decision(
        self, path: str, payload: dict[str, Any]
    ) -> Literal["created", "confirmation_required"]:
        """POST one final catalog decision and validate its safe outcome."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                f"{self._base_url}{API_VERSION_PATH}{path}",
                json=payload,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    self._set_write_failure("Home Stock Tracker authentication failed")
                    raise HomeAssistantError(
                        "Home Stock Tracker authentication failed"
                    )
                response.raise_for_status()
                result = await response.json()
        except HomeAssistantError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            self._set_write_failure("Home Stock Tracker catalog confirmation failed")
            raise HomeAssistantError(
                "Home Stock Tracker catalog confirmation failed"
            ) from None

        if not self._is_catalog_confirmation_result(result):
            self._set_write_failure("Home Stock Tracker returned an invalid response")
            raise HomeAssistantError("Home Stock Tracker returned an invalid response")
        return result["outcome"]

    @staticmethod
    def _grocery_item_payload(grocery_item: Mapping[str, Any]) -> dict[str, Any]:
        """Translate locally validated grocery fields to source-service casing."""
        payload: dict[str, Any] = {}
        if "requested_quantity" in grocery_item:
            payload["requestedQuantity"] = grocery_item["requested_quantity"]
        if "unit" in grocery_item:
            payload["unit"] = grocery_item["unit"]
        if "note" in grocery_item:
            payload["note"] = grocery_item["note"]
        return payload

    @staticmethod
    def _catalog_search_projection(result: Any) -> dict[str, Any]:
        """Validate source candidates before exposing their narrow projection."""
        if not isinstance(result, Mapping) or set(result) != {"exactMatch", "candidates"}:
            raise ValueError
        exact_match = result["exactMatch"]
        candidates = result["candidates"]
        if exact_match is not None and not isinstance(exact_match, Mapping):
            raise ValueError
        if not isinstance(candidates, list):
            raise ValueError
        return {
            "exact_match": (
                None if exact_match is None else HomeStockTrackerCoordinator._candidate_projection(exact_match)
            ),
            "candidates": [
                HomeStockTrackerCoordinator._candidate_projection(candidate)
                for candidate in candidates
            ],
        }

    @staticmethod
    def _candidate_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Project one fully validated catalog candidate without extra fields."""
        expected_fields = {
            "id",
            "canonicalName",
            "aliases",
            "category",
            "typicalUnit",
            "productType",
            "isPerishable",
            "predictionEnabled",
        }
        if not isinstance(candidate, Mapping) or set(candidate) != expected_fields:
            raise ValueError
        if (
            not isinstance(candidate["id"], str)
            or not isinstance(candidate["canonicalName"], str)
            or not isinstance(candidate["aliases"], list)
            or not all(isinstance(alias, str) for alias in candidate["aliases"])
            or candidate["category"] is not None
            and not isinstance(candidate["category"], str)
            or candidate["typicalUnit"] is not None
            and not isinstance(candidate["typicalUnit"], str)
            or candidate["productType"] is not None
            and candidate["productType"]
            not in {
                "fast_consumable",
                "pantry_staple",
                "household_consumable",
                "discrete_consumable",
            }
            or not isinstance(candidate["isPerishable"], bool)
            or not isinstance(candidate["predictionEnabled"], bool)
        ):
            raise ValueError
        return {
            "id": candidate["id"],
            "canonical_name": candidate["canonicalName"],
            "aliases": candidate["aliases"],
            "category": candidate["category"],
            "typical_unit": candidate["typicalUnit"],
            "product_type": candidate["productType"],
            "is_perishable": candidate["isPerishable"],
            "prediction_enabled": candidate["predictionEnabled"],
        }

    @staticmethod
    def _is_catalog_confirmation_result(result: Any) -> bool:
        """Validate the source grocery-result envelope without exposing it."""
        if not isinstance(result, Mapping) or result.get("outcome") not in {
            "created",
            "confirmation_required",
        }:
            return False
        if not isinstance(result.get("existingItems"), list) or not isinstance(
            result.get("requestedAddition"), Mapping
        ):
            return False
        created_item = result.get("createdItem")
        if result["outcome"] == "created":
            return isinstance(created_item, Mapping)
        return created_item is None

    async def async_add_grocery_item(
        self,
        *,
        product_name: str,
        requested_quantity: float | int | None,
        unit: str | None,
        note: str | None,
    ) -> Literal[
        "created", "confirmation_required", "product_resolution_required"
    ]:
        """Add one grocery item without retrying an uncertain write."""
        payload: dict[str, Any] = {
            "unknownProductPolicy": "propose_if_missing",
            "productName": product_name,
            "groceryItem": {"ifPendingExists": "return_existing"},
        }
        grocery_item = payload["groceryItem"]
        if requested_quantity is not None:
            grocery_item["requestedQuantity"] = requested_quantity
        if unit is not None:
            grocery_item["unit"] = unit
        if note is not None:
            grocery_item["note"] = note

        return await self._async_post_grocery_addition(payload)

    async def async_confirm_grocery_duplicate_as_separate(
        self,
        *,
        product_name: str,
        requested_quantity: float | int | None,
        unit: str | None,
        note: str | None,
    ) -> Literal[
        "created", "confirmation_required", "product_resolution_required"
    ]:
        """Create one explicitly confirmed separate pending grocery line."""
        payload: dict[str, Any] = {
            "unknownProductPolicy": "propose_if_missing",
            "productName": product_name,
            "groceryItem": {"ifPendingExists": "create_separate"},
        }
        grocery_item = payload["groceryItem"]
        if requested_quantity is not None:
            grocery_item["requestedQuantity"] = requested_quantity
        if unit is not None:
            grocery_item["unit"] = unit
        if note is not None:
            grocery_item["note"] = note

        return await self._async_post_grocery_addition(payload)

    async def async_complete_grocery_purchase(
        self,
        *,
        product_id: str,
        grocery_item_ids: list[str],
        quantity: float | int | None,
        unit: str | None,
    ) -> None:
        """Complete one explicit grocery purchase without retrying it."""
        payload: dict[str, Any] = {
            "productId": product_id,
            "groceryItemIds": grocery_item_ids,
        }
        if quantity is not None:
            payload["quantity"] = quantity
        if unit is not None:
            payload["unit"] = unit

        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                f"{self._base_url}{API_VERSION_PATH}{COMPLETE_GROCERY_PURCHASE_PATH}",
                json=payload,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    self._set_write_failure("Home Stock Tracker authentication failed")
                    raise HomeAssistantError(
                        "Home Stock Tracker authentication failed"
                    )
                response.raise_for_status()
                result = await response.json()
        except HomeAssistantError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            self._set_write_failure("Home Stock Tracker grocery purchase failed")
            raise HomeAssistantError("Home Stock Tracker grocery purchase failed") from None

        if not self._is_completed_grocery_purchase(result, product_id, grocery_item_ids):
            self._set_write_failure("Home Stock Tracker returned an invalid response")
            raise HomeAssistantError("Home Stock Tracker returned an invalid response")

    @staticmethod
    def _is_completed_grocery_purchase(
        result: Any, product_id: str, grocery_item_ids: list[str]
    ) -> bool:
        """Accept only a receipt for the exact grocery purchase request."""
        if not isinstance(result, Mapping):
            return False
        event = result.get("event")
        grocery_items = result.get("groceryItems")
        if (
            not isinstance(event, Mapping)
            or not isinstance(event.get("id"), str)
            or event.get("productId") != product_id
            or event.get("eventType") != "PURCHASED"
            or not isinstance(grocery_items, list)
        ):
            return False

        returned_ids: set[str] = set()
        for grocery_item in grocery_items:
            if (
                not isinstance(grocery_item, Mapping)
                or not isinstance(grocery_item.get("id"), str)
                or grocery_item.get("status") != "purchased"
                or grocery_item.get("relatedInventoryEventId") != event["id"]
            ):
                return False
            returned_ids.add(grocery_item["id"])

        return (
            len(returned_ids) == len(grocery_items)
            and returned_ids == set(grocery_item_ids)
        )

    async def _async_post_grocery_addition(
        self, payload: dict[str, Any]
    ) -> Literal["created", "confirmation_required", "product_resolution_required"]:
        """POST one policy-aware grocery request without retrying it."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                f"{self._base_url}{API_VERSION_PATH}{GROCERY_ITEMS_PATH}",
                json=payload,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 401:
                    self._set_write_failure("Home Stock Tracker authentication failed")
                    raise HomeAssistantError(
                        "Home Stock Tracker authentication failed"
                    )
                response.raise_for_status()
                result = await response.json()
        except HomeAssistantError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            self._set_write_failure("Home Stock Tracker grocery addition failed")
            raise HomeAssistantError("Home Stock Tracker grocery addition failed") from None

        if not isinstance(result, Mapping) or result.get("outcome") not in {
            "created",
            "confirmation_required",
            "product_resolution_required",
        }:
            self._set_write_failure("Home Stock Tracker returned an invalid response")
            raise HomeAssistantError("Home Stock Tracker returned an invalid response")

        return result["outcome"]

    def _set_write_failure(self, message: str) -> None:
        """Make entity data unavailable after an uncertain write outcome."""
        self.async_set_update_error(UpdateFailed(message))

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        try:
            grocery, inventory, recommendations = await asyncio.gather(
                self._request(session, GROCERY_ITEMS_PATH), self._request(session, INVENTORY_PATH), self._request(session, LOW_STOCK_PATH)
            )
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientError as error:
            raise UpdateFailed("Cannot reach Home Stock Tracker") from error
        if not isinstance(grocery, list) or not isinstance(inventory, Mapping) or not isinstance(inventory.get("current"), list) or not isinstance(inventory.get("uncertain"), list) or not isinstance(recommendations, Mapping) or not isinstance(recommendations.get("recommendations"), list):
            raise UpdateFailed("Home Stock Tracker returned an invalid response")
        return {"grocery": grocery, "inventory": inventory, "recommendations": recommendations["recommendations"]}

    async def _request(self, session: aiohttp.ClientSession, path: str) -> Any:
        async with session.get(f"{self._base_url}{API_VERSION_PATH}{path}", headers=self._headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 401:
                raise ConfigEntryAuthFailed
            response.raise_for_status()
            return await response.json()
