"""SwipeList integration for Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SwipeListApi, SwipeListApiError, SwipeListAuthError
from .const import (
    DOMAIN,
    CONF_API_URL,
    CONF_TOKEN,
    CONF_REFRESH_TOKEN,
    DEFAULT_API_URL,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SwipeList from a config entry."""
    session = async_get_clientsession(hass)

    api = SwipeListApi(
        session=session,
        api_url=entry.data.get(CONF_API_URL, DEFAULT_API_URL),
        token=entry.data.get(CONF_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    # Store last successful data to preserve on errors
    last_successful_data: dict = {"lists": []}

    async def async_update_data() -> dict:
        """Fetch data from SwipeList API."""
        nonlocal last_successful_data

        try:
            lists = await api.get_lists()

            # Items are already included in the list response from the API
            # No separate API call needed - items are in shopping_list["items"]
            result = {"lists": lists}

            # Store successful result
            last_successful_data = result
            _LOGGER.debug("Successfully fetched %d lists", len(lists))

            return result

        except SwipeListAuthError as err:
            _LOGGER.warning("Authentication failed, triggering re-auth: %s", err)
            # Trigger re-authentication
            entry.async_start_reauth(hass)
            # Return last known data to prevent disappearing
            if last_successful_data.get("lists"):
                _LOGGER.info("Returning cached data while re-authenticating")
                return last_successful_data
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except SwipeListApiError as err:
            _LOGGER.warning("API error: %s", err)
            # Return last known data on temporary errors
            if last_successful_data.get("lists"):
                _LOGGER.info("Returning cached data due to API error")
                return last_successful_data
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error: %s", err)
            # Return last known data on unexpected errors
            if last_successful_data.get("lists"):
                _LOGGER.info("Returning cached data due to unexpected error")
                return last_successful_data
            raise UpdateFailed(f"Unexpected error: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and API for use by platforms
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Update tokens if they changed during refresh
    if api.token != entry.data.get(CONF_TOKEN) or api.refresh_token != entry.data.get(CONF_REFRESH_TOKEN):
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_TOKEN: api.token,
                CONF_REFRESH_TOKEN: api.refresh_token,
            },
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
