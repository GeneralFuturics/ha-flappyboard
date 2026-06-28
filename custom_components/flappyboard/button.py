from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    async_add_entities([FlappyBoardClearButton(coordinator, entry)])


class FlappyBoardClearButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Clear"
    _attr_icon = "mdi:eraser"

    def __init__(self, coordinator: FlappyBoardCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_clear"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="FlappyBoard",
            model="Split-Flap Display",
        )

    async def async_press(self) -> None:
        await self._coordinator.client.async_clear_board()
