"""Tests for YTHA integration setup."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ytha.const import DOMAIN


@pytest.fixture
def mock_http(hass: HomeAssistant):
    """Mock hass.http for static path registration."""
    mock = MagicMock()
    hass.http = mock
    return mock


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_http,
) -> None:
    """Test successful setup of a config entry."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.ytha.get_ffmpeg_manager") as mock_ffmpeg:
        mock_manager = MagicMock()
        mock_manager.binary = "/usr/bin/ffmpeg"
        mock_ffmpeg.return_value = mock_manager

        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert result
    assert DOMAIN in hass.data
    assert "downloader" in hass.data[DOMAIN]
    assert hass.services.has_service(DOMAIN, "download_audio")
    mock_http.register_static_path.assert_called_once()


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_http,
) -> None:
    """Test unloading a config entry cleans up."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.ytha.get_ffmpeg_manager") as mock_ffmpeg:
        mock_manager = MagicMock()
        mock_manager.binary = "/usr/bin/ffmpeg"
        mock_ffmpeg.return_value = mock_manager

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN in hass.data

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN not in hass.data
    assert not hass.services.has_service(DOMAIN, "download_audio")
