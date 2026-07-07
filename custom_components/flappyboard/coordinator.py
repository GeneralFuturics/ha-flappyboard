from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)


class FlappyBoardCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, client: Any, board_name: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Flappy Board {board_name}",
            update_interval=timedelta(seconds=30),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_status()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Flappy Board: {err}") from err
