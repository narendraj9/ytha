"""YTHA - Audio Downloader integration for Home Assistant."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from aiohttp import web
from homeassistant.components.ffmpeg import get_ffmpeg_manager
from homeassistant.components.http import HomeAssistantView
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
_CARD_FILE = Path(__file__).parent / "frontend" / "ytha-card.js"


class YthaCardView(HomeAssistantView):
    """Serve ytha-card.js with correct MIME type."""
    url = _CARD_URL
    name = "ytha_card_js"
    requires_auth = False

    async def get(self, request):
        return web.Response(
            body=_CARD_FILE.read_bytes(),
            content_type="application/javascript",
        )


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register frontend resources once at integration load time."""
    hass.http.register_view(YthaCardView)

    async def _register_frontend(_event=None) -> None:
        lovelace = hass.data.get("lovelace")
        resources = getattr(lovelace, "resources", None)
        if not resources or not hasattr(resources, "async_create_item"):
            return
        if not resources.loaded:
            await resources.async_load()
        existing = {r["url"] for r in resources.async_items()}
        if _CARD_URL not in existing:
            await resources.async_create_item({"res_type": "module", "url": _CARD_URL})
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
