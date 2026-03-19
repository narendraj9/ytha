"""Tests for YTHA config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ytha.const import (
    CONF_OUTPUT_DIR,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def auto_mock_setup_entry(mock_setup_entry):
    """Prevent actual setup during config flow tests."""
    yield mock_setup_entry


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Test that a valid user input creates a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.ytha.config_flow.YthaConfigFlow._validate_directory",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_OUTPUT_DIR: "/media/ytha"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "YTHA Audio Downloader"
    assert result["data"] == {CONF_OUTPUT_DIR: "/media/ytha"}


async def test_user_flow_invalid_directory(hass: HomeAssistant) -> None:
    """Test that an invalid directory shows an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ytha.config_flow.YthaConfigFlow._validate_directory",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_OUTPUT_DIR: "/nonexistent/path"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_directory"}


async def test_single_instance_only(hass: HomeAssistant) -> None:
    """Test that only one instance can be configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ytha.config_flow.YthaConfigFlow._validate_directory",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_OUTPUT_DIR: "/media/ytha"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.ytha.config_flow.YthaConfigFlow._validate_directory",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_OUTPUT_DIR: "/media/ytha2"},
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
