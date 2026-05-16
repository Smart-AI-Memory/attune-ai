"""Unit tests for ``attune.ops.ops_config_store`` and CLI overlay.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T3).

Covers:

- Settings file roundtrip (write, read, missing, corrupt)
- Atomic write semantics
- ``resolve_specs_candidates_enabled`` three-state precedence
- CLI flag → resolver → Config field end-to-end
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from attune.ops import cli, ops_config_store
from attune.ops.config import Config


def _write_raw(path: Path, content: str) -> None:
    """Write arbitrary content directly to the settings path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# settings_path
# ---------------------------------------------------------------------------


class TestSettingsPath:
    def test_derives_from_attune_home(self, tmp_path: Path) -> None:
        expected = tmp_path / "ops" / "config.json"
        assert ops_config_store.settings_path(tmp_path) == expected

    def test_does_not_create_anything(self, tmp_path: Path) -> None:
        path = ops_config_store.settings_path(tmp_path)
        assert not path.exists()
        assert not path.parent.exists()


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


class TestLoadSettingsMissing:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert ops_config_store.load_settings(tmp_path) == {}

    def test_missing_does_not_log(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.WARNING, logger="attune.ops.ops_config_store")
        ops_config_store.load_settings(tmp_path)
        assert caplog.records == []


class TestLoadSettingsCorrupt:
    def test_invalid_json_returns_empty_and_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_raw(ops_config_store.settings_path(tmp_path), "{not json")
        caplog.set_level(logging.WARNING, logger="attune.ops.ops_config_store")
        assert ops_config_store.load_settings(tmp_path) == {}
        assert any("invalid JSON" in r.message for r in caplog.records)

    def test_non_object_root_returns_empty(self, tmp_path: Path) -> None:
        _write_raw(ops_config_store.settings_path(tmp_path), "[]")
        assert ops_config_store.load_settings(tmp_path) == {}

    def test_wrong_version_returns_empty(self, tmp_path: Path) -> None:
        _write_raw(
            ops_config_store.settings_path(tmp_path),
            json.dumps({"version": "bad", "settings": {"k": "v"}}),
        )
        assert ops_config_store.load_settings(tmp_path) == {}

    def test_missing_settings_key_returns_empty(self, tmp_path: Path) -> None:
        _write_raw(
            ops_config_store.settings_path(tmp_path),
            json.dumps({"version": ops_config_store.SCHEMA_VERSION}),
        )
        assert ops_config_store.load_settings(tmp_path) == {}

    def test_settings_not_dict_returns_empty(self, tmp_path: Path) -> None:
        _write_raw(
            ops_config_store.settings_path(tmp_path),
            json.dumps(
                {
                    "version": ops_config_store.SCHEMA_VERSION,
                    "settings": ["a", "b"],
                }
            ),
        )
        assert ops_config_store.load_settings(tmp_path) == {}


# ---------------------------------------------------------------------------
# save_setting (roundtrip + atomicity + validation)
# ---------------------------------------------------------------------------


class TestSaveSetting:
    def test_save_then_load(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", True)
        assert ops_config_store.load_settings(tmp_path) == {"specs_candidates_enabled": True}

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        assert not (tmp_path / "ops").exists()
        ops_config_store.save_setting(tmp_path, "x", 1)
        assert ops_config_store.settings_path(tmp_path).is_file()

    def test_multiple_keys_coexist(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "a", 1)
        ops_config_store.save_setting(tmp_path, "b", "two")
        assert ops_config_store.load_settings(tmp_path) == {"a": 1, "b": "two"}

    def test_overwrites_prior_value(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "k", "old")
        ops_config_store.save_setting(tmp_path, "k", "new")
        assert ops_config_store.load_settings(tmp_path) == {"k": "new"}

    def test_empty_key_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="key"):
            ops_config_store.save_setting(tmp_path, "", True)

    def test_non_string_key_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="key"):
            ops_config_store.save_setting(tmp_path, 1, True)  # type: ignore[arg-type]

    def test_returns_true_on_success(self, tmp_path: Path) -> None:
        assert ops_config_store.save_setting(tmp_path, "k", True) is True

    def test_returns_false_on_permission_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        def fail(*a: Any, **kw: Any) -> None:
            raise PermissionError("denied")

        monkeypatch.setattr(ops_config_store, "_write_atomic", fail)
        caplog.set_level(logging.WARNING, logger="attune.ops.ops_config_store")
        result = ops_config_store.save_setting(tmp_path, "k", True)
        assert result is False
        assert any("save failed" in r.message for r in caplog.records)


class TestSaveAtomicity:
    def test_no_temp_files_after_save(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "k", True)
        parent = ops_config_store.settings_path(tmp_path).parent
        leftovers = [p.name for p in parent.iterdir() if p.name.endswith(".tmp")]
        assert leftovers == []


# ---------------------------------------------------------------------------
# resolve_specs_candidates_enabled (the three-state precedence)
# ---------------------------------------------------------------------------


class TestResolveSpecsCandidatesEnabled:
    def test_cli_true_persists_and_returns_true(self, tmp_path: Path) -> None:
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=True, attune_home=tmp_path
        )
        assert result is True
        assert ops_config_store.load_settings(tmp_path) == {"specs_candidates_enabled": True}

    def test_cli_false_persists_and_returns_false(self, tmp_path: Path) -> None:
        # Prior True state.
        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", True)
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=False, attune_home=tmp_path
        )
        assert result is False
        assert ops_config_store.load_settings(tmp_path) == {"specs_candidates_enabled": False}

    def test_cli_none_no_persisted_returns_false(self, tmp_path: Path) -> None:
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result is False
        # No file written on the read-only path.
        assert not ops_config_store.settings_path(tmp_path).exists()

    def test_cli_none_with_persisted_true_returns_true(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", True)
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result is True

    def test_cli_none_with_persisted_false_returns_false(self, tmp_path: Path) -> None:
        ops_config_store.save_setting(tmp_path, "specs_candidates_enabled", False)
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result is False

    def test_corrupted_settings_falls_back_to_false(self, tmp_path: Path) -> None:
        _write_raw(ops_config_store.settings_path(tmp_path), "{broken")
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result is False


# ---------------------------------------------------------------------------
# CLI flag → resolver wiring
# ---------------------------------------------------------------------------


def _parse_ops_args(*argv: str) -> argparse.Namespace:
    """Helper: run argparse with the same setup cli.main() uses."""
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    cli.add_subparser(sub)
    return parser.parse_args(["ops", *argv])


class TestCliFlagParsing:
    def test_no_flag_means_none(self) -> None:
        args = _parse_ops_args()
        assert args.specs_candidates is None

    def test_specs_candidates_means_true(self) -> None:
        args = _parse_ops_args("--specs-candidates")
        assert args.specs_candidates is True

    def test_no_specs_candidates_means_false(self) -> None:
        args = _parse_ops_args("--no-specs-candidates")
        assert args.specs_candidates is False

    def test_mutually_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            _parse_ops_args("--specs-candidates", "--no-specs-candidates")


class TestCliPersistenceRoundtrip:
    """Simulates the launch-flag-then-relaunch flow described in the spec."""

    def test_first_launch_with_flag_persists(self, tmp_path: Path) -> None:
        # Launch 1: --specs-candidates → persist True
        result = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=True, attune_home=tmp_path
        )
        assert result is True

        # Launch 2: no flag → reads persisted True
        result2 = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result2 is True

        # Launch 3: --no-specs-candidates → persist False
        result3 = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=False, attune_home=tmp_path
        )
        assert result3 is False

        # Launch 4: no flag → reads persisted False
        result4 = ops_config_store.resolve_specs_candidates_enabled(
            cli_value=None, attune_home=tmp_path
        )
        assert result4 is False


class TestConfigField:
    """The Config dataclass exposes the new field."""

    def test_default_is_false(self) -> None:
        cfg = Config(project_root=Path("/x"), attune_home=Path("/y"))
        assert cfg.specs_candidates_enabled is False

    def test_can_be_set(self) -> None:
        cfg = Config(
            project_root=Path("/x"),
            attune_home=Path("/y"),
            specs_candidates_enabled=True,
        )
        assert cfg.specs_candidates_enabled is True

    def test_build_config_passes_through(self, tmp_path: Path) -> None:
        from attune.ops.config import build_config

        cfg = build_config(project_root=tmp_path, specs_candidates_enabled=True)
        assert cfg.specs_candidates_enabled is True
