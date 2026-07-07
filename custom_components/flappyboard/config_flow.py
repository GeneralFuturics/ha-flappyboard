from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import CONF_FINGERPRINT, CONF_TOKEN, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_FINGERPRINT, default=""): str,
    }
)


class FlappyBoardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Flappy Board."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            from . import FlappyBoardClient

            fingerprint = user_input.get(CONF_FINGERPRINT) or None
            try:
                client = FlappyBoardClient(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    token=user_input[CONF_TOKEN],
                    fingerprint=fingerprint,
                )
                await client.async_get_status()
            except ValueError:
                errors[CONF_FINGERPRINT] = "invalid_fingerprint"
            except aiohttp.ServerFingerprintMismatch:
                errors[CONF_FINGERPRINT] = "fingerprint_mismatch"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Flappy Board setup")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_FINGERPRINT: fingerprint,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
