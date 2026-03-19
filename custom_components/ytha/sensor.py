"""Sensor platform for YTHA download status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_DOWNLOAD_PROGRESS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up YTHA sensor from a config entry."""
    async_add_entities([YthaStatusSensor(entry)], True)


class YthaStatusSensor(SensorEntity):
    """Sensor showing current download status."""

    _attr_has_entity_name = True
    _attr_name = "Download Status"
    _attr_icon = "mdi:music-box-outline"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_native_value = "idle"
        self._download_id: str | None = None
        self._progress: float = 0
        self._filename: str | None = None
        self._url: str | None = None
        self._error: str | None = None
        self._unsub = None

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "download_id": self._download_id,
            "progress": self._progress,
            "filename": self._filename,
            "url": self._url,
            "error": self._error,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to download progress events."""
        self._unsub = self.hass.bus.async_listen(
            EVENT_DOWNLOAD_PROGRESS, self._handle_progress
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from events."""
        if self._unsub:
            self._unsub()

    @callback
    def _handle_progress(self, event) -> None:
        """Update sensor state from download progress events."""
        data = event.data
        status = data.get("status")
        self._download_id = data.get("download_id")

        if status == "starting":
            self._attr_native_value = "downloading"
            self._url = data.get("url")
            self._progress = 0
            self._filename = None
            self._error = None
        elif status == "downloading":
            self._attr_native_value = "downloading"
            self._progress = data.get("progress", 0)
            self._filename = data.get("filename")
        elif status == "processing":
            self._attr_native_value = "processing"
            self._filename = data.get("filename")
        elif status == "complete":
            self._attr_native_value = "complete"
            self._progress = 100
            self._filename = data.get("filename")
        elif status == "error":
            self._attr_native_value = "error"
            self._error = data.get("error")

        self.async_write_ha_state()
