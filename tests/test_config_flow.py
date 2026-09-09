"""Tests for Home Stock Tracker configuration."""

from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.home_stock_tracker.const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    DOMAIN,
)


async def test_user_flow_creates_a_normalized_entry(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """A valid authenticated service creates one normalized config entry."""
    aioclient_mock.get(
        "http://inventory.local/api/v1/grocery/items",
        json=[],
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: "http://inventory.local/",
            CONF_API_TOKEN: "secret-token",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Home Stock Tracker"
    assert result["data"] == {
        CONF_BASE_URL: "http://inventory.local",
        CONF_API_TOKEN: "secret-token",
    }


async def test_user_flow_rejects_a_path_in_the_service_url(hass: HomeAssistant) -> None:
    """The integration only accepts a service origin, not an API route."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: "http://inventory.local/api/v1",
            CONF_API_TOKEN: "secret-token",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE_URL: "invalid_url"}


async def test_user_flow_rejects_duplicate_configuration(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """A service origin can only be configured once."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get("http://inventory.local/api/v1/grocery/items", json=[])

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: "http://inventory.local",
            CONF_API_TOKEN: "secret-token",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_reports_invalid_authentication(
    hass: HomeAssistant, aioclient_mock
) -> None:
    """An unauthorized token is never saved as a config entry."""
    aioclient_mock.get("http://inventory.local/api/v1/grocery/items", status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: "http://inventory.local",
            CONF_API_TOKEN: "rejected-token",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_replaces_a_rejected_token(
    hass: HomeAssistant, config_entry: ConfigEntry, aioclient_mock
) -> None:
    """Reauthentication validates and replaces only the token."""
    config_entry.add_to_hass(hass)
    aioclient_mock.get("http://inventory.local/api/v1/grocery/items", json=[])

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": config_entry.entry_id},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_TOKEN: "replacement-token"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data == {
        CONF_BASE_URL: "http://inventory.local",
        CONF_API_TOKEN: "replacement-token",
    }
