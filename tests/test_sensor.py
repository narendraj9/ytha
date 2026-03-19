"""Tests for YTHA sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ytha.const import DOMAIN, EVENT_DOWNLOAD_PROGRESS

SENSOR_ENTITY_ID = "sensor.download_status"


async def _setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the integration for sensor tests."""
    entry.add_to_hass(hass)
    hass.http = MagicMock()

    with patch("custom_components.ytha.get_ffmpeg_manager") as mock_ffmpeg:
        mock_manager = MagicMock()
        mock_manager.binary = "/usr/bin/ffmpeg"
        mock_ffmpeg.return_value = mock_manager
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


async def test_sensor_initial_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor starts in idle state."""
    await _setup_integration(hass, mock_config_entry)

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state is not None
    assert state.state == "idle"


async def test_sensor_updates_on_download_event(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor updates when download progress events fire."""
    await _setup_integration(hass, mock_config_entry)

    hass.bus.async_fire(EVENT_DOWNLOAD_PROGRESS, {
        "download_id": "test-1",
        "status": "starting",
        "url": "https://example.com/video",
    })
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state is not None
    assert state.state == "downloading"

    hass.bus.async_fire(EVENT_DOWNLOAD_PROGRESS, {
        "download_id": "test-1",
        "status": "downloading",
        "progress": 50.0,
        "filename": "test.opus",
    })
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state.state == "downloading"
    assert state.attributes["progress"] == 50.0

    hass.bus.async_fire(EVENT_DOWNLOAD_PROGRESS, {
        "download_id": "test-1",
        "status": "complete",
        "filename": "/media/ytha/test.opus",
    })
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state.state == "complete"
    assert state.attributes["progress"] == 100
    assert state.attributes["filename"] == "/media/ytha/test.opus"


async def test_sensor_handles_error_event(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensor reflects error state."""
    await _setup_integration(hass, mock_config_entry)

    hass.bus.async_fire(EVENT_DOWNLOAD_PROGRESS, {
        "download_id": "err-1",
        "status": "error",
        "error": "Video unavailable",
    })
    await hass.async_block_till_done()

    state = hass.states.get(SENSOR_ENTITY_ID)
    assert state is not None
    assert state.state == "error"
    assert state.attributes["error"] == "Video unavailable"
