"""Core download logic wrapping yt-dlp."""

from __future__ import annotations

import logging
import os
import uuid

from homeassistant.core import HomeAssistant

from .const import EVENT_DOWNLOAD_PROGRESS

_LOGGER = logging.getLogger(__name__)


class Downloader:
    """Manages audio downloads using yt-dlp."""

    def __init__(
        self,
        hass: HomeAssistant,
        ffmpeg_binary: str,
        output_dir: str,
    ) -> None:
        self.hass = hass
        self._ffmpeg_binary = ffmpeg_binary
        self._output_dir = output_dir

    def _fire_event(self, download_id: str, data: dict) -> None:
        """Fire a progress event (thread-safe)."""
        self.hass.bus.fire(EVENT_DOWNLOAD_PROGRESS, {"download_id": download_id, **data})

    def _build_ydl_opts(self, download_id: str) -> dict:
        """Build yt-dlp options dict."""
        def progress_hook(d: dict) -> None:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = round((downloaded / total) * 100, 1) if total else 0
                self._fire_event(download_id, {
                    "status": "downloading",
                    "progress": percent,
                    "filename": d.get("filename", ""),
                    "speed": d.get("speed"),
                    "eta": d.get("eta"),
                })
            elif d["status"] == "finished":
                self._fire_event(download_id, {
                    "status": "processing",
                    "filename": d.get("filename", ""),
                })

        return {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self._output_dir, "%(artist&{} - |)s%(title)s.%(ext)s"),
            "ffmpeg_location": self._ffmpeg_binary,
            "progress_hooks": [progress_hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "flac",
            }],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

    def _do_download(self, url: str, download_id: str) -> str:
        """Synchronous download — runs in executor thread."""
        import yt_dlp

        os.makedirs(self._output_dir, exist_ok=True)
        opts = self._build_ydl_opts(download_id)

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            return base + ".flac"

    async def async_download(
        self,
        url: str,
        download_id: str | None = None,
    ) -> str:
        """Start a download. Returns the output file path."""
        if download_id is None:
            download_id = uuid.uuid4().hex[:8]

        self._fire_event(download_id, {"status": "starting", "url": url})

        try:
            output_path = await self.hass.async_add_executor_job(
                self._do_download, url, download_id
            )
            self._fire_event(download_id, {
                "status": "complete",
                "filename": output_path,
            })
            return output_path
        except Exception as err:
            _LOGGER.error("Download failed for %s: %s", url, err)
            self._fire_event(download_id, {
                "status": "error",
                "error": str(err),
            })
            raise
