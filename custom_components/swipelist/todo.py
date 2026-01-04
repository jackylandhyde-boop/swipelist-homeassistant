"""Todo platform for SwipeList integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import SwipeListApi
from .const import DOMAIN, ATTR_LIST_ID, ATTR_SHARED_WITH

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SwipeList todo entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    api: SwipeListApi = data["api"]

    # Create a todo entity for each shopping list
    entities = []
    for shopping_list in coordinator.data.get("lists", []):
        entities.append(
            SwipeListTodoEntity(
                coordinator=coordinator,
                api=api,
                list_data=shopping_list,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)

    # Listen for new lists being added
    @callback
    def async_check_new_lists() -> None:
        """Check for new lists and add entities."""
        current_list_ids = {
            entity.list_id
            for entity in hass.data[DOMAIN].get(f"{entry.entry_id}_entities", [])
        }

        new_entities = []
        for shopping_list in coordinator.data.get("lists", []):
            if shopping_list.get("id") not in current_list_ids:
                new_entities.append(
                    SwipeListTodoEntity(
                        coordinator=coordinator,
                        api=api,
                        list_data=shopping_list,
                        entry_id=entry.entry_id,
                    )
                )

        if new_entities:
            async_add_entities(new_entities)

    coordinator.async_add_listener(async_check_new_lists)


class SwipeListTodoEntity(CoordinatorEntity, TodoListEntity):
    """A SwipeList shopping list as a Home Assistant Todo entity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        api: SwipeListApi,
        list_data: dict[str, Any],
        entry_id: str,
    ) -> None:
        """Initialize the todo entity."""
        super().__init__(coordinator)
        self._api = api
        self._list_id = list_data.get("id")
        self._list_data = list_data
        self._entry_id = entry_id

        # Entity attributes
        self._attr_unique_id = f"swipelist_{self._list_id}"
        self._attr_name = list_data.get("name", f"List {self._list_id}")

    @property
    def list_id(self) -> int:
        """Return the list ID."""
        return self._list_id

    @property
    def _current_list_data(self) -> dict[str, Any]:
        """Get current list data from coordinator."""
        for shopping_list in self.coordinator.data.get("lists", []):
            if shopping_list.get("id") == self._list_id:
                return shopping_list
        return self._list_data

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the todo items for this list."""
        import json

        items = []
        list_data = self._current_list_data
        raw_items = list_data.get("items", [])

        # Handle items being returned as JSON string from API
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except (json.JSONDecodeError, TypeError):
                raw_items = []

        for item in raw_items:
            status = (
                TodoItemStatus.COMPLETED
                if item.get("checked") or item.get("isChecked")
                else TodoItemStatus.NEEDS_ACTION
            )

            # Build description from quantity and category
            description_parts = []
            if item.get("quantity"):
                description_parts.append(f"Menge: {item['quantity']}")
            if item.get("category"):
                description_parts.append(f"Kategorie: {item['category']}")

            items.append(
                TodoItem(
                    uid=str(item.get("id")),
                    summary=item.get("name", ""),
                    status=status,
                    description=", ".join(description_parts) if description_parts else None,
                )
            )
        return items

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        list_data = self._current_list_data
        items = list_data.get("items", [])

        return {
            ATTR_LIST_ID: self._list_id,
            "item_count": len(items),
            "checked_count": sum(
                1 for item in items if item.get("checked") or item.get("isChecked")
            ),
            "unchecked_count": sum(
                1 for item in items if not (item.get("checked") or item.get("isChecked"))
            ),
            ATTR_SHARED_WITH: list_data.get("sharedWith", []),
        }

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new todo item."""
        # Parse quantity from summary if format is "quantity name"
        name = item.summary
        quantity = None

        # Try to extract quantity (e.g., "2 Milch" -> quantity=2, name=Milch)
        parts = name.split(" ", 1)
        if len(parts) == 2 and parts[0].replace(",", "").replace(".", "").isdigit():
            quantity = parts[0]
            name = parts[1]

        await self._api.add_item(
            list_id=self._list_id,
            name=name,
            quantity=quantity,
        )
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        item_id = int(item.uid)
        checked = item.status == TodoItemStatus.COMPLETED

        await self._api.update_item(
            list_id=self._list_id,
            item_id=item_id,
            checked=checked,
            name=item.summary if item.summary else None,
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items."""
        for uid in uids:
            await self._api.delete_item(
                list_id=self._list_id,
                item_id=int(uid),
            )
        await self.coordinator.async_request_refresh()

    async def async_move_todo_item(
        self, uid: str, previous_uid: str | None = None
    ) -> None:
        """Move a todo item (reorder) - not supported yet."""
        # SwipeList API doesn't support reordering yet
        pass
