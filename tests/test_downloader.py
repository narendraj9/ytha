"""Tests for YTHA downloader."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ytha.const import EVENT_DOWNLOAD_PROGRESS
from custom_components.ytha.downloader import Downloader


@pytest.fixture
def downloader(hass: HomeAssistant) -> Downloader:
    """Create a downloader instance."""
    return Downloader(
        hass=hass,
        output_dir="/media/ytha",
    )


def test_build_ydl_opts(downloader: Downloader) -> None:
    """Test that yt-dlp options are correctly built."""
    opts = downloader._build_ydl_opts("test-id")

    assert opts["format"] == "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio"
    assert opts["noplaylist"] is True
    assert opts["outtmpl"] == "/media/ytha/%(artist&{} - |)s%(title)s.%(ext)s"
    assert opts["geo_bypass"] is True
    assert opts["age_limit"] == 99
    assert opts["extractor_args"] == {"youtube": {"player_client": ["android", "web"]}}
    assert "extract_audio" not in opts


async def test_download_fires_events(hass: HomeAssistant, downloader: Downloader) -> None:
    """Test that download fires progress events."""
    events = []
    hass.bus.async_listen(EVENT_DOWNLOAD_PROGRESS, lambda e: events.append(e.data))

    mock_info = {"title": "Test Video", "ext": "opus"}
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    mock_ydl_instance.__exit__ = MagicMock(return_value=False)
    mock_ydl_instance.extract_info.return_value = mock_info
    mock_ydl_instance.prepare_filename.return_value = "/media/ytha/Test Video.opus"

    mock_yt_dlp_module = MagicMock()
    mock_yt_dlp_module.YoutubeDL.return_value = mock_ydl_instance

    with (
        patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp_module}),
        patch("os.makedirs"),
    ):
        result = await downloader.async_download(
            url="https://example.com/video",
            download_id="test-123",
        )

    await hass.async_block_till_done()
    statuses = [e["status"] for e in events]
    assert "starting" in statuses
    assert "complete" in statuses
    assert result == "/media/ytha/Test Video.opus"


async def test_download_error_fires_error_event(
    hass: HomeAssistant, downloader: Downloader
) -> None:
    """Test that a failed download fires an error event."""
    events = []
    hass.bus.async_listen(EVENT_DOWNLOAD_PROGRESS, lambda e: events.append(e.data))

    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_ydl.extract_info.side_effect = Exception("Network error")

    mock_yt_dlp_module = MagicMock()
    mock_yt_dlp_module.YoutubeDL.return_value = mock_ydl

    with (
        patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp_module}),
        patch("os.makedirs"),
    ):
        with pytest.raises(Exception, match="Network error"):
            await downloader.async_download(
                url="https://example.com/bad",
                download_id="err-123",
            )

    await hass.async_block_till_done()
    statuses = [e["status"] for e in events]
    assert "error" in statuses
    error_event = next(e for e in events if e["status"] == "error")
    assert "Network error" in error_event["error"]
