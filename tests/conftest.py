"""Shared fixtures for Home Stock Tracker integration tests."""

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.home_stock_tracker.const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> Generator[None]:
    """Enable the repository custom component for every integration test."""
    yield


@pytest.fixture
def config_entry() -> Generator[MockConfigEntry]:
    """Create the configured Home Stock Tracker entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_BASE_URL: "http://inventory.local",
            CONF_API_TOKEN: "secret-token",
        },
        unique_id="http://inventory.local",
    )
    yield entry
