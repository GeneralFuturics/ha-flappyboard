from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FlappyBoardCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: FlappyBoardCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FlappyBoardNotifyEntity(coordinator, entry)])


class FlappyBoardNotifyEntity(NotifyEntity):
    """Notify entity that sends messages to a Flappy Board display.

    Use notify.send_message in automations:

        action: notify.send_message
        target:
          entity_id: notify.living_room_board
        data:
          title: "GATE 12"      # first row (optional)
          message: "BOARDING"   # remaining rows; \\n splits into multiple rows
    """

    _attr_has_entity_name = True
    _attr_name = None  # Entity takes the device name

    def __init__(self, coordinator: FlappyBoardCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_notify"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Flappy Board",
            model="Split-Flap Display",
        )

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        rows: list[str] = []
        if title:
            rows.append(title)
        rows.extend(message.splitlines())
        if not rows:
            rows = [" "]
        await self._coordinator.client.async_send_message(rows)
