"""YTHA - Audio Downloader integration for Home Assistant."""

from __future__ import annotations

import logging
import os
import uuid

from homeassistant.components.ffmpeg import get_ffmpeg_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DOMAIN,
)
from .downloader import Downloader

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up YTHA from a config entry."""
    output_dir = entry.data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)
    ffmpeg_manager = get_ffmpeg_manager(hass)

    downloader = Downloader(
        hass=hass,
        ffmpeg_binary=ffmpeg_manager.binary,
        output_dir=output_dir,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["downloader"] = downloader

    async def _download_and_sync(url: str, download_id: str) -> None:
        await downloader.async_download(url=url, download_id=download_id)
        for mass_entry in hass.config_entries.async_entries("mass") or hass.config_entries.async_entries("music_assistant"):
            if mass_entry.state.value == "loaded":
                try:
                    await mass_entry.runtime_data.mass.music.start_sync(
                        media_types=None, providers=None
                    )
                except Exception as err:
                    _LOGGER.warning("Could not trigger Music Assistant sync: %s", err)
                break

    async def handle_download_audio(call: ServiceCall) -> None:
        """Handle the download_audio service call."""
        url = call.data["url"]
        download_id = uuid.uuid4().hex[:8]
        hass.async_create_task(_download_and_sync(url=url, download_id=download_id))

    hass.services.async_register(DOMAIN, "download_audio", handle_download_audio)

    # Register static path for frontend card
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/ytha/frontend", frontend_dir, cache_headers=False)]
    )
    add_extra_js_url(hass, "/ytha/frontend/ytha-card.js")

    # Register as a Lovelace resource so the card shows up in the card picker
    resources = hass.data["lovelace"].resources
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    resource_url = "/ytha/frontend/ytha-card.js"
    already_added = any(
        r["url"].startswith(resource_url) for r in resources.async_items()
    )
    if not already_added:
        if isinstance(resources, ResourceStorageCollection):
            await resources.async_create_item(
                {"res_type": "module", "url": resource_url}
            )
        else:
            resources.data.append({"type": "module", "url": resource_url})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "download_audio")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)

    return unload_ok
