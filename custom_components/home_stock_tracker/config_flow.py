"""Config flow for Home Stock Tracker."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from yarl import URL

from .const import (
    API_VERSION_PATH,
    CONF_API_TOKEN,
    CONF_BASE_URL,
    DEFAULT_TITLE,
    DOMAIN,
    GROCERY_ITEMS_PATH,
)


class CannotConnectError(Exception):
    """Raised when the configured service is unreachable."""


class InvalidAuthError(Exception):
    """Raised when the configured service rejects the token."""


class InvalidBaseUrlError(ValueError):
    """Raised when a base URL cannot address the service."""


def normalize_base_url(value: str) -> str:
    """Return an HTTP(S) origin without a trailing slash or path."""
    url = URL(value.strip())
    if url.scheme not in {"http", "https"} or not url.host:
        raise InvalidBaseUrlError
    if url.path not in {"", "/"} or url.query_string or url.fragment:
        raise InvalidBaseUrlError
    return str(url.with_path("").with_query(None).with_fragment(None)).rstrip("/")


async def async_validate_connection(
    hass: HomeAssistant, base_url: str, api_token: str
) -> None:
    """Validate credentials against an authenticated read endpoint."""
    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {api_token}"}
    try:
        async with session.get(
            f"{base_url}{API_VERSION_PATH}{GROCERY_ITEMS_PATH}",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status == 401:
                raise InvalidAuthError
            if response.status < 200 or response.status >= 300:
                raise CannotConnectError
            payload = await response.json()
    except aiohttp.ClientError as error:
        raise CannotConnectError from error
    except TimeoutError as error:
        raise CannotConnectError from error

    if not isinstance(payload, list):
        raise CannotConnectError


class HomeStockTrackerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Stock Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_BASE_URL])
                await async_validate_connection(
                    self.hass, base_url, user_input[CONF_API_TOKEN]
                )
            except InvalidBaseUrlError:
                errors[CONF_BASE_URL] = "invalid_url"
            except InvalidAuthError:
                errors["base"] = "invalid_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(base_url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={CONF_BASE_URL: base_url, CONF_API_TOKEN: user_input[CONF_API_TOKEN]},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BASE_URL): str,
                    vol.Required(CONF_API_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start reauthentication for an existing config entry."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace a rejected API token."""
        errors: dict[str, str] = {}

        if user_input is not None and self._reauth_entry is not None:
            try:
                await async_validate_connection(
                    self.hass,
                    self._reauth_entry.data[CONF_BASE_URL],
                    user_input[CONF_API_TOKEN],
                )
            except InvalidAuthError:
                errors["base"] = "invalid_auth"
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={
                        CONF_BASE_URL: self._reauth_entry.data[CONF_BASE_URL],
                        CONF_API_TOKEN: user_input[CONF_API_TOKEN],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): str}),
            errors=errors,
        )
