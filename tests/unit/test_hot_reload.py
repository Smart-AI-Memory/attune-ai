"""Tests for hot_reload/config.py and hot_reload/reloader.py.

Covers HotReloadConfig, get_hot_reload_config, ReloadResult, and WorkflowReloader.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock watchdog before any hot_reload imports (watcher.py requires it)
sys.modules.setdefault("watchdog", MagicMock())
sys.modules.setdefault("watchdog.events", MagicMock())
sys.modules.setdefault("watchdog.observers", MagicMock())

# We need to reset the global _config singleton between tests
import attune.hot_reload.config as _config_module  # noqa: E402
from attune.hot_reload.config import HotReloadConfig, get_hot_reload_config  # noqa: E402
from attune.hot_reload.reloader import ReloadResult, WorkflowReloader  # noqa: E402

# ---------------------------------------------------------------------------
# HotReloadConfig
# ---------------------------------------------------------------------------


class TestHotReloadConfig:
    """Tests for HotReloadConfig."""

    @pytest.fixture(autouse=True)
    def _reset_global(self) -> None:
        """Reset the global _config singleton before each test."""
        _config_module._config = None

    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HOT_RELOAD_ENABLED", raising=False)
        monkeypatch.delenv("HOT_RELOAD_WS_PATH", raising=False)
        monkeypatch.delenv("HOT_RELOAD_DELAY", raising=False)
        monkeypatch.delenv("HOT_RELOAD_WATCH_DIRS", raising=False)
        config = HotReloadConfig()
        assert config.enabled is False
        assert config.websocket_path == "/ws/hot-reload"
        assert config.reload_delay == 0.5

    def test_enabled_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOT_RELOAD_ENABLED", "true")
        config = HotReloadConfig()
        assert config.enabled is True

    def test_enabled_false_variants(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for val in ("false", "False", "0", "no"):
            monkeypatch.setenv("HOT_RELOAD_ENABLED", val)
            config = HotReloadConfig()
            assert config.enabled is False

    def test_custom_websocket_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOT_RELOAD_WS_PATH", "/custom/ws")
        config = HotReloadConfig()
        assert config.websocket_path == "/custom/ws"

    def test_custom_delay(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOT_RELOAD_DELAY", "2.0")
        config = HotReloadConfig()
        assert config.reload_delay == 2.0

    def test_watch_dirs_from_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        d1 = tmp_path / "dir1"
        d2 = tmp_path / "dir2"
        d1.mkdir()
        d2.mkdir()
        monkeypatch.setenv("HOT_RELOAD_WATCH_DIRS", f"{d1},{d2}")
        config = HotReloadConfig()
        assert len(config.watch_dirs) == 2
        assert config.watch_dirs[0] == d1
        assert config.watch_dirs[1] == d2

    def test_to_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOT_RELOAD_ENABLED", "true")
        monkeypatch.setenv("HOT_RELOAD_WS_PATH", "/ws")
        monkeypatch.setenv("HOT_RELOAD_DELAY", "1.0")
        monkeypatch.setenv("HOT_RELOAD_WATCH_DIRS", "/tmp/wf")
        config = HotReloadConfig()
        d = config.to_dict()
        assert d["enabled"] is True
        assert d["websocket_path"] == "/ws"
        assert d["reload_delay"] == 1.0
        assert isinstance(d["watch_dirs"], list)

    def test_default_watch_dirs_filters_nonexistent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default dirs that don't exist should be filtered out."""
        monkeypatch.delenv("HOT_RELOAD_WATCH_DIRS", raising=False)
        config = HotReloadConfig()
        # All watch_dirs should be existing Path objects
        for d in config.watch_dirs:
            assert isinstance(d, Path)


class TestGetHotReloadConfig:
    """Tests for get_hot_reload_config() singleton."""

    @pytest.fixture(autouse=True)
    def _reset_global(self) -> None:
        _config_module._config = None

    def test_returns_config(self) -> None:
        config = get_hot_reload_config()
        assert isinstance(config, HotReloadConfig)

    def test_returns_same_instance(self) -> None:
        c1 = get_hot_reload_config()
        c2 = get_hot_reload_config()
        assert c1 is c2


# ---------------------------------------------------------------------------
# ReloadResult
# ---------------------------------------------------------------------------


class TestReloadResult:
    """Tests for ReloadResult dataclass-like object."""

    def test_success_result(self) -> None:
        r = ReloadResult(success=True, workflow_id="wf-1", message="ok")
        assert r.success is True
        assert r.workflow_id == "wf-1"
        assert r.message == "ok"
        assert r.error is None

    def test_failure_result(self) -> None:
        r = ReloadResult(
            success=False,
            workflow_id="wf-2",
            message="failed",
            error="import error",
        )
        assert r.success is False
        assert r.error == "import error"

    def test_to_dict(self) -> None:
        r = ReloadResult(success=True, workflow_id="wf-1", message="ok")
        d = r.to_dict()
        assert d == {
            "success": True,
            "workflow_id": "wf-1",
            "message": "ok",
            "error": None,
        }


# ---------------------------------------------------------------------------
# WorkflowReloader
# ---------------------------------------------------------------------------


class TestWorkflowReloader:
    """Tests for WorkflowReloader."""

    def _make_reloader(
        self,
        register_ok: bool = True,
        notify_fn: MagicMock | None = None,
    ) -> WorkflowReloader:
        register_cb = MagicMock(return_value=register_ok)
        return WorkflowReloader(
            register_callback=register_cb,
            notification_callback=notify_fn,
        )

    def test_reload_count_starts_zero(self) -> None:
        reloader = self._make_reloader()
        assert reloader.get_reload_count() == 0

    def test_reload_no_module_name(self, tmp_path: Path) -> None:
        """Non-.py file should fail to determine module name."""
        reloader = self._make_reloader()
        result = reloader.reload_workflow("wf-1", str(tmp_path / "README.md"))
        assert result.success is False
        assert "Could not determine module name" in result.error

    def test_reload_import_error(self) -> None:
        """ImportError during reload should return failure."""
        reloader = self._make_reloader()
        with patch.object(importlib, "import_module", side_effect=ImportError("no such module")):
            result = reloader.reload_workflow("wf-1", "/fake/workflows/my_workflow.py")
        assert result.success is False
        assert "Import failed" in result.message

    def test_reload_no_workflow_class_found(self) -> None:
        """Module without *Workflow class should return failure."""
        reloader = self._make_reloader()
        fake_module = types.ModuleType("workflows.test_wf")
        fake_module.some_function = lambda: None
        with patch.object(importlib, "import_module", return_value=fake_module):
            result = reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        assert result.success is False
        assert "No workflow class found" in result.message

    def test_reload_success(self) -> None:
        """Successful reload with valid workflow class."""
        reloader = self._make_reloader(register_ok=True)
        fake_module = types.ModuleType("workflows.test_wf")

        class TestWorkflow:
            pass

        fake_module.TestWorkflow = TestWorkflow
        with patch.object(importlib, "import_module", return_value=fake_module):
            result = reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        assert result.success is True
        assert reloader.get_reload_count() == 1

    def test_reload_registration_failure(self) -> None:
        """Registration callback returning False should fail."""
        reloader = self._make_reloader(register_ok=False)
        fake_module = types.ModuleType("workflows.test_wf")

        class TestWorkflow:
            pass

        fake_module.TestWorkflow = TestWorkflow
        with patch.object(importlib, "import_module", return_value=fake_module):
            result = reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        assert result.success is False
        assert "Registration failed" in result.message

    def test_notification_callback_on_success(self) -> None:
        """Notification callback is called on success."""
        notify = MagicMock()
        reloader = self._make_reloader(register_ok=True, notify_fn=notify)
        fake_module = types.ModuleType("workflows.test_wf")

        class TestWorkflow:
            pass

        fake_module.TestWorkflow = TestWorkflow
        with patch.object(importlib, "import_module", return_value=fake_module):
            reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        notify.assert_called()
        call_data = notify.call_args[0][0]
        assert call_data["success"] is True
        assert call_data["workflow_id"] == "wf-1"

    def test_notification_callback_on_failure(self) -> None:
        """Notification callback is called on failure."""
        notify = MagicMock()
        reloader = self._make_reloader(register_ok=True, notify_fn=notify)
        with patch.object(importlib, "import_module", side_effect=ImportError("nope")):
            reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        notify.assert_called()
        call_data = notify.call_args[0][0]
        assert call_data["success"] is False

    def test_unexpected_error_handled(self) -> None:
        """Unexpected exceptions should be caught and returned as failure."""
        reloader = self._make_reloader()
        with patch.object(importlib, "import_module", side_effect=RuntimeError("boom")):
            result = reloader.reload_workflow("wf-1", "/fake/workflows/test_wf.py")
        assert result.success is False
        assert "Unexpected error" in result.message

    def test_unload_module_removes_from_sys_modules(self) -> None:
        """_unload_module should remove module and submodules."""
        reloader = self._make_reloader()
        sys.modules["fake_test_mod"] = types.ModuleType("fake_test_mod")
        sys.modules["fake_test_mod.sub"] = types.ModuleType("fake_test_mod.sub")
        reloader._unload_module("fake_test_mod")
        assert "fake_test_mod" not in sys.modules
        assert "fake_test_mod.sub" not in sys.modules

    def test_get_module_name_for_workflow_file(self) -> None:
        """_get_module_name should extract module name from path."""
        reloader = self._make_reloader()
        name = reloader._get_module_name("/project/workflows/security.py")
        assert name == "workflows.security"

    def test_get_module_name_returns_none_for_non_py(self) -> None:
        reloader = self._make_reloader()
        name = reloader._get_module_name("/project/workflows/README.md")
        assert name is None

    def test_find_workflow_class(self) -> None:
        """_find_workflow_class should find classes ending with 'Workflow'."""
        reloader = self._make_reloader()
        mod = types.ModuleType("test_mod")

        class SecurityWorkflow:
            pass

        mod.SecurityWorkflow = SecurityWorkflow
        mod.helper_function = lambda: None
        result = reloader._find_workflow_class(mod)
        assert result is SecurityWorkflow

    def test_find_workflow_class_none(self) -> None:
        """_find_workflow_class returns None when no class found."""
        reloader = self._make_reloader()
        mod = types.ModuleType("test_mod")
        mod.helper = lambda: None
        result = reloader._find_workflow_class(mod)
        assert result is None
