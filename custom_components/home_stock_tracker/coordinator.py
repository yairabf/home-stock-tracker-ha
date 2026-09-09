"""Read-only data coordinator for Home Stock Tracker."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_VERSION_PATH, CONF_API_TOKEN, CONF_BASE_URL, DOMAIN, GROCERY_ITEMS_PATH, INVENTORY_PATH, LOW_STOCK_PATH, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HomeStockTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch all Home Stock Tracker read state atomically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self._base_url = entry.data[CONF_BASE_URL]
        self._headers = {"Authorization": f"Bearer {entry.data[CONF_API_TOKEN]}"}

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
