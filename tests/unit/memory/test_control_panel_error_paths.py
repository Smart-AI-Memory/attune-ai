"""Tests for MemoryControlPanel error-handling fallback branches.

The existing `tests/memory/test_control_panel.py` and
`tests/unit/memory/test_control_panel.py` cover the happy paths
and most of the surface (93% line + branch combined). This file
covers the remaining error-handling fallbacks discovered by the
test-quality-program rubric pass:

- storage_bytes calculation OSError fallback (line 229-231)
- long-term `get_statistics()` exception handler (241-242)
- health_check "long_term not initialized" branch (415-419)
- `_count_patterns()` OSError/PermissionError handler (491-493)

These are all defensive paths around real I/O — exercised via
patched `Path.glob` / `Path.stat` / `Path.exists` and a fake
long-term that raises on `get_statistics()`.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.memory.control_panel import ControlPanelConfig, MemoryControlPanel


@pytest.fixture
def panel(tmp_path) -> MemoryControlPanel:
    """Fresh panel pointing storage at tmp_path (which exists)."""
    cfg = ControlPanelConfig(
        storage_dir=str(tmp_path),
        audit_dir=str(tmp_path / "audit"),
        auto_start_redis=False,
    )
    return MemoryControlPanel(config=cfg)


@pytest.fixture
def panel_missing_storage(tmp_path) -> MemoryControlPanel:
    """Panel with storage_dir that does NOT exist."""
    cfg = ControlPanelConfig(
        storage_dir=str(tmp_path / "nonexistent"),
        audit_dir=str(tmp_path / "audit"),
        auto_start_redis=False,
    )
    return MemoryControlPanel(config=cfg)


# ---------------------------------------------------------------------------
# get_statistics() — storage_bytes fallback (line 229-231)
# ---------------------------------------------------------------------------


class TestStatisticsStorageBytesFallback:
    """When summing file sizes raises, storage_bytes falls back to 0."""

    def test_storage_bytes_zero_on_glob_exception(self, panel, tmp_path):
        """Patch Path.glob to raise; storage_bytes must end at 0."""
        # Place at least one file so storage_path.exists() == True
        (tmp_path / "marker.json").write_text("{}")

        with patch.object(type(tmp_path), "glob", side_effect=OSError("denied")):
            stats = panel.get_statistics()

        assert stats.storage_bytes == 0
        assert stats.long_term_available is True


# ---------------------------------------------------------------------------
# get_statistics() — long-term stats fallback (line 241-242)
# ---------------------------------------------------------------------------


class TestStatisticsLongTermFallback:
    """When _get_long_term() / get_statistics() raises, the warning
    branch fires and pattern counts stay at their dataclass defaults.
    """

    def test_long_term_raises_does_not_crash(self, panel, tmp_path):
        (tmp_path / "marker.json").write_text("{}")

        with patch.object(panel, "_get_long_term", side_effect=RuntimeError("lt down")):
            stats = panel.get_statistics()

        # Defaults preserved.
        assert stats.patterns_total == 0
        assert stats.patterns_public == 0
        assert stats.patterns_internal == 0
        assert stats.patterns_sensitive == 0
        assert stats.patterns_encrypted == 0

    def test_get_statistics_succeeds_when_long_term_returns_partial(self, panel, tmp_path):
        """When get_statistics() returns a missing-key dict, the
        ``.get(...)`` fallbacks keep things at zero without raising.
        """

        class FakeLT:
            def get_statistics(self_inner):
                return {}  # entirely empty

        with patch.object(panel, "_get_long_term", return_value=FakeLT()):
            stats = panel.get_statistics()

        assert stats.patterns_total == 0
        assert stats.patterns_public == 0
        assert stats.patterns_internal == 0
        assert stats.patterns_sensitive == 0
        assert stats.patterns_encrypted == 0


# ---------------------------------------------------------------------------
# health_check() — long-term unavailable branch (line 415-419)
# ---------------------------------------------------------------------------


class TestHealthCheckLongTermUnavailable:
    """When ``status['long_term']['status']`` != 'available', the
    warning branch fires with the right recommendation.
    """

    def test_missing_storage_triggers_warn(self, panel_missing_storage):
        result = panel_missing_storage.health_check()

        long_term_check = next(c for c in result["checks"] if c["name"] == "long_term")
        assert long_term_check["status"] == "warn"
        assert "Storage not initialized" in long_term_check["message"]
        assert "Initialize long-term storage directory" in result["recommendations"]
        assert result["overall"] == "degraded"


# ---------------------------------------------------------------------------
# _count_patterns() — OSError/PermissionError handler (line 491-493)
# ---------------------------------------------------------------------------


class TestCountPatternsErrorHandler:
    """When Path.glob raises OSError/PermissionError, _count_patterns
    returns 0 instead of crashing.
    """

    def test_glob_oserror_returns_zero(self, panel, tmp_path):
        with patch.object(type(tmp_path), "glob", side_effect=OSError("io")):
            assert panel._count_patterns() == 0

    def test_glob_permissionerror_returns_zero(self, panel, tmp_path):
        with patch.object(type(tmp_path), "glob", side_effect=PermissionError("denied")):
            assert panel._count_patterns() == 0

    def test_count_patterns_zero_when_storage_missing(self, panel_missing_storage):
        """Early-return path: storage_path.exists() is False."""
        assert panel_missing_storage._count_patterns() == 0
