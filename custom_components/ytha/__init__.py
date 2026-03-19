"""YTHA - Audio Downloader integration for Home Assistant."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.ffmpeg import get_ffmpeg_manager
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, EVENT_HOMEASSISTANT_STARTED, HomeAssistant, ServiceCall

from .const import (
    CONF_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DOMAIN,
)
from .downloader import Downloader

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

_CARD_URL = "/ytha/ytha-card.js"
_FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register frontend resources once at integration load time."""
    async def _register_frontend(_event=None) -> None:
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig("/ytha", _FRONTEND_DIR, cache_headers=False)]
            )
        except RuntimeError:
            pass  # already registered

        lovelace = hass.data.get("lovelace")
        if not lovelace or lovelace.mode != "storage":
            return
        if not lovelace.resources.loaded:
            await lovelace.resources.async_load()
        existing = {r["url"] for r in lovelace.resources.async_items()}
        if _CARD_URL not in existing:
            await lovelace.resources.async_create_item(
                {"res_type": "module", "url": _CARD_URL}
            )
            _LOGGER.info("Registered Lovelace resource: %s", _CARD_URL)

    if hass.state == CoreState.running:
        await _register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    return True


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, "download_audio")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)

    return unload_ok
