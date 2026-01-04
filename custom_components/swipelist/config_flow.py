"""Config flow for SwipeList integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SwipeListApi, SwipeListApiError, SwipeListAuthError
from .const import DOMAIN, CONF_API_URL, CONF_TOKEN, CONF_REFRESH_TOKEN, DEFAULT_API_URL

_LOGGER = logging.getLogger(__name__)


class SwipeListConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SwipeList."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                api = SwipeListApi(
                    session=session,
                    api_url=user_input.get(CONF_API_URL, DEFAULT_API_URL),
                )

                # Try to authenticate
                auth_result = await api.authenticate(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )

                # Get user info for unique ID
                user_info = auth_result.get("user", {})
                user_id = user_info.get("id")
                user_email = user_info.get("email", user_input[CONF_EMAIL])

                # Set unique ID to prevent duplicate entries
                await self.async_set_unique_id(f"swipelist_{user_id or user_email}")
                self._abort_if_unique_id_configured()

                # Create entry with tokens (not password)
                return self.async_create_entry(
                    title=f"SwipeList ({user_email})",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_API_URL: user_input.get(CONF_API_URL, DEFAULT_API_URL),
                        CONF_TOKEN: api.token,
                        CONF_REFRESH_TOKEN: api.refresh_token,
                    },
                )

            except SwipeListAuthError:
                errors["base"] = "invalid_auth"
            except SwipeListApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle re-authentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)

                # Get existing entry
                existing_entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )

                api = SwipeListApi(
                    session=session,
                    api_url=existing_entry.data.get(CONF_API_URL, DEFAULT_API_URL),
                )

                await api.authenticate(
                    user_input[CONF_EMAIL],
                    user_input[CONF_PASSWORD],
                )

                # Update entry with new tokens
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={
                        **existing_entry.data,
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_TOKEN: api.token,
                        CONF_REFRESH_TOKEN: api.refresh_token,
                    },
                )

                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            except SwipeListAuthError:
                errors["base"] = "invalid_auth"
            except SwipeListApiError:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
