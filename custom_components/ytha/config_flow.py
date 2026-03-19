"""Config flow for YTHA integration."""

from __future__ import annotations

import os
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): str,
    }
)


class YthaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YTHA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            output_dir = user_input[CONF_OUTPUT_DIR]

            # Validate directory
            dir_ok = await self.hass.async_add_executor_job(
                self._validate_directory, output_dir
            )
            if not dir_ok:
                errors["base"] = "invalid_directory"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="YTHA Audio Downloader",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def _validate_directory(path: str) -> bool:
        """Check that the directory exists or can be created."""
        try:
            os.makedirs(path, exist_ok=True)
            return os.access(path, os.W_OK)
        except OSError:
            return False
