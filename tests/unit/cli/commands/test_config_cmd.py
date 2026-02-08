"""Tests for config_cmd.py — Configuration CLI commands.

Covers cmd_config_show, cmd_config_set, cmd_config_get, cmd_config_validate,
cmd_config_reset, cmd_config_list_keys, cmd_config_path, _convert_value, _print_config_tree.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import sys
import types
from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

# The config_cmd module imports from attune.config which may not have all
# these exports. We mock them at import time.
_mock_config = types.ModuleType("attune.config")
_mock_config.ConfigLoader = type(
    "ConfigLoader",
    (),
    {
        "discover_config_path": staticmethod(lambda: None),
    },
)
_mock_config.ConfigLoader.discover_config_path.__doc__ = "Search: 1. path"
_mock_config.UnifiedConfig = MagicMock()
_mock_config.get_loader = MagicMock()
_mock_config.load_unified_config = MagicMock()
_mock_config.save_unified_config = MagicMock()
_mock_config.validate_config = MagicMock()
_mock_config._validate_file_path = MagicMock(side_effect=lambda p: p)

_mock_loader = types.ModuleType("attune.config.loader")
_mock_loader.CONFIG_SEARCH_PATHS = ["/etc/attune", "~/.attune", "./attune.config.json"]

_mock_discovery = types.ModuleType("attune.discovery")
_mock_discovery.show_tip_if_available = MagicMock()

_mock_logging_config = types.ModuleType("attune.logging_config")
_mock_logging_config.get_logger = MagicMock(return_value=MagicMock())

_mock_platform_utils = types.ModuleType("attune.platform_utils")
_mock_platform_utils.setup_asyncio_policy = MagicMock()

# Patch before importing config_cmd
with patch.dict(
    sys.modules,
    {
        "attune.config": _mock_config,
        "attune.config.loader": _mock_loader,
        "attune.discovery": _mock_discovery,
        "attune.logging_config": _mock_logging_config,
        "attune.platform_utils": _mock_platform_utils,
    },
):
    from attune.cli.commands.config_cmd import (
        _convert_value,
        _print_config_tree,
        cmd_config_get,
        cmd_config_list_keys,
        cmd_config_path,
        cmd_config_reset,
        cmd_config_set,
        cmd_config_show,
        cmd_config_validate,
    )

# Module path prefix for patching local bindings
_CMD = "attune.cli.commands.config_cmd"


# ---------------------------------------------------------------------------
# _convert_value
# ---------------------------------------------------------------------------


class TestConvertValue:
    """Tests for _convert_value() type coercion."""

    def test_bool_true_variants(self) -> None:
        for v in ("true", "1", "yes", "on", "True", "YES"):
            assert _convert_value(v, True) is True

    def test_bool_false_variants(self) -> None:
        for v in ("false", "0", "no", "off", "False", "NO"):
            assert _convert_value(v, False) is False

    def test_bool_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid boolean"):
            _convert_value("maybe", True)

    def test_int_conversion(self) -> None:
        assert _convert_value("42", 0) == 42

    def test_int_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid integer"):
            _convert_value("abc", 0)

    def test_float_conversion(self) -> None:
        assert _convert_value("3.14", 0.0) == pytest.approx(3.14)

    def test_float_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid float"):
            _convert_value("abc", 0.0)

    def test_list_conversion(self) -> None:
        result = _convert_value("a, b, c", [])
        assert result == ["a", "b", "c"]

    def test_string_passthrough(self) -> None:
        assert _convert_value("hello", "default") == "hello"


# ---------------------------------------------------------------------------
# _print_config_tree
# ---------------------------------------------------------------------------


class TestPrintConfigTree:
    """Tests for _print_config_tree()."""

    def test_simple_dict(self, capsys: pytest.CaptureFixture) -> None:
        _print_config_tree({"key": "value"})
        assert "key: value" in capsys.readouterr().out

    def test_nested_dict(self, capsys: pytest.CaptureFixture) -> None:
        _print_config_tree({"parent": {"child": "val"}})
        output = capsys.readouterr().out
        assert "parent:" in output
        assert "child: val" in output

    def test_list_value(self, capsys: pytest.CaptureFixture) -> None:
        _print_config_tree({"items": ["a", "b"]})
        output = capsys.readouterr().out
        assert "items:" in output
        assert "- a" in output

    def test_empty_list(self, capsys: pytest.CaptureFixture) -> None:
        _print_config_tree({"items": []})
        assert "items: []" in capsys.readouterr().out

    def test_skips_underscore_keys(self, capsys: pytest.CaptureFixture) -> None:
        _print_config_tree({"_meta": "hidden", "visible": "yes"})
        output = capsys.readouterr().out
        assert "_meta" not in output
        assert "visible: yes" in output


# ---------------------------------------------------------------------------
# cmd_config_show
# ---------------------------------------------------------------------------


class TestCmdConfigShow:
    """Tests for cmd_config_show()."""

    @patch(f"{_CMD}.load_unified_config")
    def test_show_all_default(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {"routing": {"tier": "cheap"}}
        mock_load.return_value = mock_config
        args = Namespace(section=None, json=False)
        result = cmd_config_show(args)
        assert result == 0
        assert "routing" in capsys.readouterr().out

    @patch(f"{_CMD}.load_unified_config")
    def test_show_json_format(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {"key": "val"}
        mock_load.return_value = mock_config
        args = Namespace(section=None, json=True)
        result = cmd_config_show(args)
        assert result == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed == {"key": "val"}

    @patch(f"{_CMD}.load_unified_config")
    def test_show_specific_section(
        self, mock_load: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        mock_config = MagicMock()
        section = MagicMock()
        section.to_dict.return_value = {"tier": "cheap"}
        mock_config.routing = section
        mock_load.return_value = mock_config
        args = Namespace(section="routing", json=False)
        result = cmd_config_show(args)
        assert result == 0

    @patch(f"{_CMD}.load_unified_config")
    def test_show_unknown_section(
        self, mock_load: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        mock_config = MagicMock(spec=[])  # no attributes
        mock_load.return_value = mock_config
        args = Namespace(section="nonexistent", json=False)
        result = cmd_config_show(args)
        assert result == 1
        assert "Unknown section" in capsys.readouterr().err

    @patch(f"{_CMD}.load_unified_config", side_effect=ValueError("bad"))
    def test_show_value_error(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_show(Namespace(section=None, json=False))
        assert result == 1

    @patch(
        f"{_CMD}.load_unified_config",
        side_effect=json.JSONDecodeError("err", "", 0),
    )
    def test_show_json_decode_error(
        self, mock_load: MagicMock, capsys: pytest.CaptureFixture
    ) -> None:
        result = cmd_config_show(Namespace(section=None, json=False))
        assert result == 1


# ---------------------------------------------------------------------------
# cmd_config_set
# ---------------------------------------------------------------------------


class TestCmdConfigSet:
    """Tests for cmd_config_set()."""

    def test_invalid_key_format(self, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_set(Namespace(key="noperiod", value="val"))
        assert result == 1
        assert "Invalid key format" in capsys.readouterr().err

    @patch(f"{_CMD}.load_unified_config", side_effect=ValueError("broken"))
    def test_load_error(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_set(Namespace(key="routing.tier", value="val"))
        assert result == 1

    @patch(f"{_CMD}.save_unified_config", return_value="/path/config.json")
    @patch(f"{_CMD}.validate_config", return_value=[])
    @patch(f"{_CMD}.load_unified_config")
    def test_successful_set(
        self,
        mock_load: MagicMock,
        mock_validate: MagicMock,
        mock_save: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_config = MagicMock()
        mock_config.get_value.return_value = "old_val"  # string type
        mock_load.return_value = mock_config
        result = cmd_config_set(Namespace(key="routing.tier", value="capable"))
        assert result == 0
        mock_config.set_value.assert_called_once_with("routing.tier", "capable")

    @patch(f"{_CMD}.load_unified_config")
    def test_unknown_key(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_config = MagicMock()
        mock_config.get_value.side_effect = KeyError("nope")
        mock_config.get_all_keys.return_value = ["routing.tier"]
        mock_load.return_value = mock_config
        result = cmd_config_set(Namespace(key="bad.key", value="val"))
        assert result == 1

    @patch(f"{_CMD}.validate_config")
    @patch(f"{_CMD}.load_unified_config")
    def test_validation_errors_block_save(
        self,
        mock_load: MagicMock,
        mock_validate: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_config = MagicMock()
        mock_config.get_value.return_value = "old"
        mock_load.return_value = mock_config
        err = MagicMock()
        err.severity = "error"
        err.__str__ = lambda self: "validation error"
        mock_validate.return_value = [err]
        result = cmd_config_set(Namespace(key="routing.tier", value="bad"))
        assert result == 1


# ---------------------------------------------------------------------------
# cmd_config_get
# ---------------------------------------------------------------------------


class TestCmdConfigGet:
    """Tests for cmd_config_get()."""

    def test_invalid_key_format(self, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_get(Namespace(key="noperiod"))
        assert result == 1

    @patch(f"{_CMD}.load_unified_config")
    def test_successful_get(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_config = MagicMock()
        mock_config.get_value.return_value = "cheap"
        mock_load.return_value = mock_config
        result = cmd_config_get(Namespace(key="routing.tier"))
        assert result == 0
        assert "cheap" in capsys.readouterr().out

    @patch(f"{_CMD}.load_unified_config")
    def test_unknown_key(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_config = MagicMock()
        mock_config.get_value.side_effect = KeyError("nope")
        mock_config.get_all_keys.return_value = ["routing.tier"]
        mock_load.return_value = mock_config
        result = cmd_config_get(Namespace(key="bad.key"))
        assert result == 1

    @patch(f"{_CMD}.load_unified_config", side_effect=ValueError("broken"))
    def test_load_error(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_get(Namespace(key="routing.tier"))
        assert result == 1


# ---------------------------------------------------------------------------
# cmd_config_validate
# ---------------------------------------------------------------------------


class TestCmdConfigValidate:
    """Tests for cmd_config_validate()."""

    @patch(f"{_CMD}.validate_config", return_value=[])
    @patch(f"{_CMD}.load_unified_config")
    def test_valid_config(
        self,
        mock_load: MagicMock,
        mock_validate: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_load.return_value = MagicMock()
        result = cmd_config_validate(Namespace())
        assert result == 0
        assert "valid" in capsys.readouterr().out.lower()

    @patch(f"{_CMD}.validate_config")
    @patch(f"{_CMD}.load_unified_config")
    def test_config_with_errors(
        self,
        mock_load: MagicMock,
        mock_validate: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_load.return_value = MagicMock()
        err = MagicMock()
        err.severity = "error"
        err.__str__ = lambda self: "bad value"
        mock_validate.return_value = [err]
        result = cmd_config_validate(Namespace())
        assert result == 1

    @patch(f"{_CMD}.validate_config")
    @patch(f"{_CMD}.load_unified_config")
    def test_config_with_warnings_only(
        self,
        mock_load: MagicMock,
        mock_validate: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_load.return_value = MagicMock()
        warn = MagicMock()
        warn.severity = "warning"
        warn.__str__ = lambda self: "minor issue"
        mock_validate.return_value = [warn]
        result = cmd_config_validate(Namespace())
        assert result == 0

    @patch(f"{_CMD}.load_unified_config", side_effect=ValueError("broken"))
    def test_load_error(self, mock_load: MagicMock, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_validate(Namespace())
        assert result == 1


# ---------------------------------------------------------------------------
# cmd_config_reset
# ---------------------------------------------------------------------------


class TestCmdConfigReset:
    """Tests for cmd_config_reset()."""

    def test_no_confirm_exits(self, capsys: pytest.CaptureFixture) -> None:
        result = cmd_config_reset(Namespace(confirm=False))
        assert result == 1
        assert "confirm" in capsys.readouterr().out.lower()

    @patch(f"{_CMD}.save_unified_config", return_value="/path/config.json")
    @patch(f"{_CMD}.UnifiedConfig", return_value=MagicMock())
    def test_with_confirm(
        self,
        mock_cls: MagicMock,
        mock_save: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        result = cmd_config_reset(Namespace(confirm=True))
        assert result == 0
        assert "reset" in capsys.readouterr().out.lower()

    @patch(
        f"{_CMD}.save_unified_config",
        side_effect=PermissionError("denied"),
    )
    @patch(f"{_CMD}.UnifiedConfig", return_value=MagicMock())
    def test_save_error(
        self,
        mock_cls: MagicMock,
        mock_save: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        result = cmd_config_reset(Namespace(confirm=True))
        assert result == 1


# ---------------------------------------------------------------------------
# cmd_config_list_keys
# ---------------------------------------------------------------------------


class TestCmdConfigListKeys:
    """Tests for cmd_config_list_keys()."""

    @patch(f"{_CMD}.UnifiedConfig")
    def test_lists_keys(self, mock_cls: MagicMock, capsys: pytest.CaptureFixture) -> None:
        mock_instance = MagicMock()
        mock_instance.get_all_keys.return_value = [
            "routing.tier",
            "routing.fallback",
            "auth.strategy",
        ]
        mock_instance.get_value.side_effect = lambda k: {
            "routing.tier": "cheap",
            "routing.fallback": True,
            "auth.strategy": "subscription",
        }[k]
        mock_cls.return_value = mock_instance
        result = cmd_config_list_keys(Namespace())
        assert result == 0
        output = capsys.readouterr().out
        assert "routing" in output.lower()


# ---------------------------------------------------------------------------
# cmd_config_path
# ---------------------------------------------------------------------------


class TestCmdConfigPath:
    """Tests for cmd_config_path()."""

    @patch("attune.config.loader.CONFIG_SEARCH_PATHS", ["/a", "/b"])
    @patch(f"{_CMD}.ConfigLoader")
    @patch(f"{_CMD}.get_loader")
    def test_shows_active_config(
        self,
        mock_get_loader: MagicMock,
        mock_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_loader = MagicMock()
        mock_loader.discover_config_path.return_value = "/home/user/attune.json"
        mock_get_loader.return_value = mock_loader
        mock_cls.discover_config_path = MagicMock()
        mock_cls.discover_config_path.__doc__ = "Search: 1. a 2. b"
        result = cmd_config_path(Namespace())
        assert result == 0
        assert "Active config" in capsys.readouterr().out

    @patch("attune.config.loader.CONFIG_SEARCH_PATHS", ["/a"])
    @patch(f"{_CMD}.ConfigLoader")
    @patch(f"{_CMD}.get_loader")
    def test_shows_default_when_no_config(
        self,
        mock_get_loader: MagicMock,
        mock_cls: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_loader = MagicMock()
        mock_loader.discover_config_path.return_value = None
        mock_loader.get_default_config_path.return_value = "/default/config.json"
        mock_get_loader.return_value = mock_loader
        mock_cls.discover_config_path = MagicMock()
        mock_cls.discover_config_path.__doc__ = "Search: 1. a"
        result = cmd_config_path(Namespace())
        assert result == 0
        assert "Default location" in capsys.readouterr().out
