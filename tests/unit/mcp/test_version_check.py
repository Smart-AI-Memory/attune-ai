"""Tests for MCP version check module.

Covers: check_for_updates, get_update_status, _compare_versions.
"""

from __future__ import annotations

import json
import types
from unittest.mock import MagicMock, patch

from attune.mcp.version_check import (
    _compare_versions,
    check_for_updates,
    get_update_status,
)


def _make_urlopen_mock(response_body: bytes) -> MagicMock:
    """Create a mock for urllib.request.urlopen context manager."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestCheckForUpdates:
    """Tests for check_for_updates."""

    def setup_method(self):
        """Reset cache before each test."""
        import attune.mcp.version_check as vc

        vc._cached_status = None

    def test_returns_update_info_when_newer(self):
        """Returns dict with update_available=True when newer version exists."""
        pypi_data = json.dumps({"info": {"version": "99.0.0"}}).encode()
        mock_attune = types.ModuleType("attune")
        mock_attune.__version__ = "1.0.0"

        with (
            patch.dict("sys.modules", {"attune": mock_attune}),
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock(pypi_data)),
        ):
            result = check_for_updates()

        assert result is not None
        assert result["update_available"] is True
        assert result["latest"] == "99.0.0"
        assert result["current"] == "1.0.0"

    def test_returns_cached_result_on_second_call(self):
        """Second call returns cached result without network."""
        import attune.mcp.version_check as vc

        vc._cached_status = {
            "latest": "2.0.0",
            "current": "1.0.0",
            "update_available": True,
        }

        result = check_for_updates()

        assert result is not None
        assert result["latest"] == "2.0.0"

    def test_returns_none_on_network_error(self):
        """Returns None when PyPI request fails."""
        mock_attune = types.ModuleType("attune")
        mock_attune.__version__ = "1.0.0"

        with (
            patch.dict("sys.modules", {"attune": mock_attune}),
            patch("urllib.request.urlopen", side_effect=OSError("network")),
        ):
            result = check_for_updates()

        assert result is None

    def test_returns_none_when_version_unknown(self):
        """Returns None when current version can't be determined."""
        # Simulate attune import failing inside the function
        with patch.dict("sys.modules", {"attune": None}):
            result = check_for_updates()

        assert result is None

    def test_returns_none_when_latest_empty(self):
        """Returns None when PyPI returns empty version string."""
        pypi_data = json.dumps({"info": {"version": ""}}).encode()
        mock_attune = types.ModuleType("attune")
        mock_attune.__version__ = "1.0.0"

        with (
            patch.dict("sys.modules", {"attune": mock_attune}),
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock(pypi_data)),
        ):
            result = check_for_updates()

        assert result is None

    def test_no_update_when_same_version(self):
        """Returns dict with update_available=False when versions match."""
        pypi_data = json.dumps({"info": {"version": "1.0.0"}}).encode()
        mock_attune = types.ModuleType("attune")
        mock_attune.__version__ = "1.0.0"

        with (
            patch.dict("sys.modules", {"attune": mock_attune}),
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock(pypi_data)),
        ):
            result = check_for_updates()

        assert result is not None
        assert result["update_available"] is False


class TestGetUpdateStatus:
    """Tests for get_update_status."""

    def test_returns_none_when_not_checked(self):
        """Returns None before check_for_updates has been called."""
        import attune.mcp.version_check as vc

        vc._cached_status = None
        assert get_update_status() is None

    def test_returns_cached_status(self):
        """Returns cached status after check_for_updates has run."""
        import attune.mcp.version_check as vc

        vc._cached_status = {
            "latest": "2.0.0",
            "current": "1.0.0",
            "update_available": True,
        }

        result = get_update_status()

        assert result is not None
        assert result["latest"] == "2.0.0"


class TestCompareVersions:
    """Tests for _compare_versions."""

    def test_newer_version_returns_true(self):
        assert _compare_versions("1.0.0", "2.0.0") is True

    def test_same_version_returns_false(self):
        assert _compare_versions("1.0.0", "1.0.0") is False

    def test_older_version_returns_false(self):
        assert _compare_versions("2.0.0", "1.0.0") is False

    def test_minor_version_update(self):
        assert _compare_versions("1.0.0", "1.1.0") is True

    def test_patch_version_update(self):
        assert _compare_versions("1.0.0", "1.0.1") is True

    def test_invalid_version_falls_back_to_string(self):
        """Non-numeric versions fall back to string comparison."""
        assert _compare_versions("1.0.0", "1.0.0-beta") is True
        assert _compare_versions("abc", "abc") is False
