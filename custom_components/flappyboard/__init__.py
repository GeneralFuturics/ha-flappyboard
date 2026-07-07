from __future__ import annotations

import logging
import ssl
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import CONF_FINGERPRINT, CONF_TOKEN, DOMAIN
from .coordinator import FlappyBoardCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NOTIFY]

SERVICE_SEND_MESSAGE = "send_message"

TRANSITION_ANIMATIONS = [
    "none", "staggered_start", "top_to_bottom", "bottom_to_top",
    "left_to_right", "right_to_left", "row_by_row", "dissolve",
    "diagonal", "middle_out", "outside_in", "spiral", "hatch",
    "snake_up", "matrix", "random",
]

SERVICE_SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("message"): cv.string,
        vol.Optional("flip_speed"): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Optional("transition_animation"): vol.In(TRANSITION_ANIMATIONS),
        vol.Optional("center_h", default=False): cv.boolean,
        vol.Optional("center_v", default=False): cv.boolean,
    }
)

_LOGGER = logging.getLogger(__name__)


def _make_ssl_param(fingerprint: str | None) -> aiohttp.Fingerprint | ssl.SSLContext:
    """Return an aiohttp SSL parameter for a self-signed Flappy Board certificate.

    When a SHA-256 fingerprint is provided (hex, with or without colons) we use
    aiohttp.Fingerprint, which pins to that exact certificate — the right security
    model for a self-signed local device cert.

    Without a fingerprint we fall back to ssl=False and log a prominent warning.
    Users should provide the fingerprint shown in the Flappy Board Settings screen.
    """
    if fingerprint:
        hex_only = fingerprint.replace(":", "").lower()
        try:
            return aiohttp.Fingerprint(bytes.fromhex(hex_only))
        except ValueError as err:
            raise ValueError(f"Invalid TLS fingerprint '{fingerprint}': {err}") from err

    _LOGGER.warning(
        "Flappy Board: no TLS fingerprint configured — certificate authenticity is "
        "not verified. Enter the SHA-256 fingerprint from the Flappy Board Settings "
        "screen to enable certificate pinning."
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class FlappyBoardClient:
    """HTTPS client for the Flappy Board REST API."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        fingerprint: str | None = None,
    ) -> None:
        self._base_url = f"https://{host}:{port}/v1"
        self._token = token
        self._ssl = _make_ssl_param(fingerprint)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def async_get_status(self) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/status",
                ssl=self._ssl,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def async_send_message(
        self,
        rows: list[str],
        *,
        center_h: bool = False,
        center_v: bool = False,
        flip_speed: float | None = None,
        transition_animation: str | None = None,
    ) -> None:
        alignment = "center" if center_h else None
        items: list[list[dict[str, str]]] = []
        for line in rows:
            cell: dict[str, str] = {"text": line}
            if alignment:
                cell["alignment"] = alignment
            items.append([cell])

        rows_obj: dict[str, Any] = {"items": items}
        if center_v:
            rows_obj["vertical_alignment"] = "center"

        payload: dict[str, Any] = {"message": {"rows": rows_obj}}
        if flip_speed is not None:
            payload["flip_speed"] = flip_speed
        if transition_animation is not None:
            payload["transition_animation"] = transition_animation

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/message",
                headers=self._headers(),
                json=payload,
                ssl=self._ssl,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()

    async def async_clear_board(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self._base_url}/board",
                headers=self._headers(),
                ssl=self._ssl,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                resp.raise_for_status()


def _coordinator_for_device(hass: HomeAssistant, device_id: str) -> FlappyBoardCoordinator:
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if not device:
        raise ServiceValidationError(f"Device '{device_id}' not found")
    entry_id = next(
        (eid for eid in device.config_entries if eid in hass.data.get(DOMAIN, {})),
        None,
    )
    if entry_id is None:
        raise ServiceValidationError(f"Device '{device_id}' is not a configured Flappy Board")
    return hass.data[DOMAIN][entry_id]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = FlappyBoardClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        token=entry.data[CONF_TOKEN],
        fingerprint=entry.data.get(CONF_FINGERPRINT),
    )
    coordinator = FlappyBoardCoordinator(hass, client, entry.title)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_MESSAGE):
        async def handle_send_message(call: ServiceCall) -> None:
            coordinator = _coordinator_for_device(hass, call.data["device_id"])
            rows = call.data["message"].splitlines() or [" "]
            await coordinator.client.async_send_message(
                rows,
                center_h=call.data.get("center_h", False),
                center_v=call.data.get("center_v", False),
                flip_speed=call.data.get("flip_speed"),
                transition_animation=call.data.get("transition_animation"),
            )

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_MESSAGE,
            handle_send_message,
            schema=SERVICE_SEND_MESSAGE_SCHEMA,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
    return unload_ok
