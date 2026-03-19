"""Shared test fixtures for YTHA."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant import loader
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ytha.const import (
    CONF_OUTPUT_DIR,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations in all tests."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_OUTPUT_DIR: "/media/ytha",
        },
        title="YTHA Audio Downloader",
        unique_id=DOMAIN,
    )


@pytest.fixture
def mock_setup_entry() -> AsyncMock:
    """Mock setting up a config entry."""
    with patch(
        "custom_components.ytha.async_setup_entry", return_value=True
    ) as mock:
        yield mock
