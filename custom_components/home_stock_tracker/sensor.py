"""Sensors for Home Stock Tracker."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomeStockTrackerCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Home Stock Tracker sensors."""
    coordinator: HomeStockTrackerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HomeStockTrackerSensor(
                coordinator, entry, "grocery", "Pending groceries", "items", lambda data: data["grocery"]
            ),
            HomeStockTrackerSensor(
                coordinator,
                entry,
                "inventory",
                "Tracked inventory",
                None,
                lambda data: data["inventory"]["current"] + data["inventory"]["uncertain"],
            ),
            HomeStockTrackerSensor(
                coordinator,
                entry,
                "low_stock",
                "Low-stock recommendations",
                "recommendations",
                lambda data: data["recommendations"],
            ),
        ]
    )


class HomeStockTrackerSensor(
    CoordinatorEntity[HomeStockTrackerCoordinator], SensorEntity
):
    """Expose one read-only Home Stock Tracker collection."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomeStockTrackerCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        attribute_key: str | None,
        items: Callable[[dict[str, Any]], list[dict[str, Any]]],
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attribute_key = attribute_key
        self._items = items

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return len(self._items(self.coordinator.data))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data is None:
            return None
        if self._attribute_key is None:
            return self.coordinator.data["inventory"]
        return {self._attribute_key: self._items(self.coordinator.data)}
