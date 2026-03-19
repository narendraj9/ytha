"""JavaScript module registration for YTHA frontend card."""

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = "/ytha"
JSMODULES = [{"filename": "ytha-card.js"}]


class JSModuleRegistration:
    """Registers the YTHA card JS module in Home Assistant."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.lovelace = hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Register static path and Lovelace resource."""
        await self._async_register_path()
        if self.lovelace and self.lovelace.mode == "storage":
            await self._async_wait_for_lovelace_resources()

    async def _async_register_path(self) -> None:
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, Path(__file__).parent, cache_headers=False)]
            )
        except RuntimeError:
            _LOGGER.debug("Static path %s already registered", URL_BASE)

    async def _async_wait_for_lovelace_resources(self) -> None:
        async def _check_loaded(_now: Any) -> None:
            if self.lovelace.resources.loaded:
                await self._async_register_modules()
            else:
                _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(None)

    async def _async_register_modules(self) -> None:
        existing = [
            r for r in self.lovelace.resources.async_items()
            if r["url"].startswith(URL_BASE)
        ]
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            if not any(r["url"].startswith(url) for r in existing):
                _LOGGER.info("Registering Lovelace resource: %s", url)
                await self.lovelace.resources.async_create_item(
                    {"res_type": "module", "url": url}
                )

    async def async_unregister(self) -> None:
        """Remove Lovelace resources registered by this integration."""
        if not self.lovelace or self.lovelace.mode != "storage":
            return
        if not self.lovelace.resources.loaded:
            return
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            for resource in self.lovelace.resources.async_items():
                if resource["url"].startswith(url):
                    await self.lovelace.resources.async_delete_item(resource["id"])
