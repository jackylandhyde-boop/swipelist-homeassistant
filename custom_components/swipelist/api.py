"""SwipeList API Client for Home Assistant."""

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    DEFAULT_API_URL,
    ENDPOINT_LOGIN,
    ENDPOINT_REFRESH,
    ENDPOINT_LISTS,
    ENDPOINT_LIST_ITEMS,
    ENDPOINT_ITEM,
)

_LOGGER = logging.getLogger(__name__)


class SwipeListApiError(Exception):
    """Exception for SwipeList API errors."""
    pass


class SwipeListAuthError(SwipeListApiError):
    """Exception for authentication errors."""
    pass


class SwipeListApi:
    """SwipeList API Client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_url: str = DEFAULT_API_URL,
        token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._api_url = api_url.rstrip("/")
        self._token = token
        self._refresh_token = refresh_token
        self._user_id: int | None = None

    @property
    def token(self) -> str | None:
        """Return current access token."""
        return self._token

    @property
    def refresh_token(self) -> str | None:
        """Return current refresh token."""
        return self._refresh_token

    async def authenticate(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate with email and password."""
        try:
            async with self._session.post(
                f"{self._api_url}{ENDPOINT_LOGIN}",
                json={"email": email, "password": password},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 401:
                    raise SwipeListAuthError("Invalid email or password")
                if response.status != 200:
                    raise SwipeListApiError(f"Authentication failed: {response.status}")

                data = await response.json()
                self._token = data.get("token") or data.get("accessToken")
                self._refresh_token = data.get("refreshToken")
                self._user_id = data.get("user", {}).get("id")

                return data
        except aiohttp.ClientError as err:
            raise SwipeListApiError(f"Connection error: {err}") from err

    async def refresh_auth(self) -> bool:
        """Refresh the access token."""
        if not self._refresh_token:
            return False

        try:
            async with self._session.post(
                f"{self._api_url}{ENDPOINT_REFRESH}",
                json={"refreshToken": self._refresh_token},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                self._token = data.get("token") or data.get("accessToken")
                if data.get("refreshToken"):
                    self._refresh_token = data.get("refreshToken")
                return True
        except aiohttp.ClientError:
            return False

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authorization."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        url = f"{self._api_url}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                json=data,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                # Try to refresh token on 401
                if response.status == 401 and retry_auth:
                    if await self.refresh_auth():
                        return await self._request(method, endpoint, data, retry_auth=False)
                    raise SwipeListAuthError("Session expired")

                if response.status >= 400:
                    error_text = await response.text()
                    raise SwipeListApiError(f"API error {response.status}: {error_text}")

                if response.status == 204:
                    return {}

                return await response.json()
        except aiohttp.ClientError as err:
            raise SwipeListApiError(f"Connection error: {err}") from err

    async def get_lists(self) -> list[dict[str, Any]]:
        """Get all shopping lists."""
        result = await self._request("GET", ENDPOINT_LISTS)
        # API might return {"lists": [...]} or just [...]
        if isinstance(result, list):
            return result
        return result.get("lists", result.get("data", []))

    async def get_list(self, list_id: int) -> dict[str, Any]:
        """Get a specific shopping list with items."""
        return await self._request("GET", f"{ENDPOINT_LISTS}/{list_id}")

    async def get_list_items(self, list_id: int) -> list[dict[str, Any]]:
        """Get items for a specific list."""
        endpoint = ENDPOINT_LIST_ITEMS.format(list_id=list_id)
        result = await self._request("GET", endpoint)
        if isinstance(result, list):
            return result
        return result.get("items", result.get("data", []))

    async def add_item(
        self,
        list_id: int,
        name: str,
        quantity: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Add an item to a list."""
        endpoint = ENDPOINT_LIST_ITEMS.format(list_id=list_id)
        data = {"name": name}
        if quantity:
            data["quantity"] = quantity
        if category:
            data["category"] = category
        return await self._request("POST", endpoint, data)

    async def update_item(
        self,
        list_id: int,
        item_id: int,
        checked: bool | None = None,
        name: str | None = None,
        quantity: str | None = None,
    ) -> dict[str, Any]:
        """Update an item."""
        endpoint = ENDPOINT_ITEM.format(list_id=list_id, item_id=item_id)
        data = {}
        if checked is not None:
            data["checked"] = checked
        if name is not None:
            data["name"] = name
        if quantity is not None:
            data["quantity"] = quantity
        return await self._request("PUT", endpoint, data)

    async def delete_item(self, list_id: int, item_id: int) -> None:
        """Delete an item from a list."""
        endpoint = ENDPOINT_ITEM.format(list_id=list_id, item_id=item_id)
        await self._request("DELETE", endpoint)

    async def check_item(self, list_id: int, item_id: int, checked: bool = True) -> dict[str, Any]:
        """Check or uncheck an item."""
        return await self.update_item(list_id, item_id, checked=checked)

    async def create_list(self, name: str) -> dict[str, Any]:
        """Create a new shopping list."""
        return await self._request("POST", ENDPOINT_LISTS, {"name": name})
