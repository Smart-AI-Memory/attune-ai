# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Tests for the 16.0.0 stale entry-point detector.

The detector's contract (round-table q-16-release-reliability-001):
one cached metadata scan per process, one warning line per external
distribution still declaring ``attune.plugins`` / ``attune.wizards``
entries, fail-open on any scan error.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from attune.plugins import stale_entry_points as sep


def _dist(name: str | None, *groups: str) -> SimpleNamespace:
    """Build a minimal fake distribution with one entry per group."""
    return SimpleNamespace(
        metadata={"Name": name},
        entry_points=[
            SimpleNamespace(group=group, name=f"ep-{i}") for i, group in enumerate(groups)
        ],
    )


@pytest.fixture(autouse=True)
def _fresh_scan_cache():
    """Each test starts with the once-per-process guard cleared."""
    sep._reset_scan_cache()
    yield
    sep._reset_scan_cache()


def test_warns_once_per_external_dist(monkeypatch, caplog):
    monkeypatch.setattr(
        sep.metadata,
        "distributions",
        lambda: iter(
            [
                _dist("legacy-plugin-pkg", "attune.plugins"),
                _dist("legacy-wizard-pkg", "attune.wizards", "console_scripts"),
                _dist("unrelated-pkg", "console_scripts"),
            ]
        ),
    )
    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 2
    messages = [r.getMessage() for r in warnings]
    assert any("legacy-plugin-pkg" in m and "'attune.plugins'" in m for m in messages)
    assert any("legacy-wizard-pkg" in m and "'attune.wizards'" in m for m in messages)
    assert all(sep.MIGRATION_GUIDE in m for m in messages)
    assert not any("unrelated-pkg" in m for m in messages)


def test_one_line_per_dist_merges_both_groups(monkeypatch, caplog):
    monkeypatch.setattr(
        sep.metadata,
        "distributions",
        lambda: iter([_dist("double-pkg", "attune.plugins", "attune.wizards")]),
    )
    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert "'attune.plugins', 'attune.wizards'" in message


def test_attune_ai_own_dist_is_skipped(monkeypatch, caplog):
    monkeypatch.setattr(
        sep.metadata,
        "distributions",
        lambda: iter(
            [
                _dist("attune-ai", "attune.plugins"),
                _dist("Attune_AI", "attune.wizards"),  # normalization variant
            ]
        ),
    )
    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_nameless_dist_is_skipped(monkeypatch, caplog):
    monkeypatch.setattr(
        sep.metadata,
        "distributions",
        lambda: iter([_dist(None, "attune.plugins")]),
    )
    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_quiet_when_nothing_stale(monkeypatch, caplog):
    monkeypatch.setattr(
        sep.metadata,
        "distributions",
        lambda: iter([_dist("clean-pkg", "console_scripts")]),
    )
    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_fail_open_on_scan_error(monkeypatch, caplog):
    def _boom():
        raise RuntimeError("corrupt metadata")

    monkeypatch.setattr(sep.metadata, "distributions", _boom)
    with caplog.at_level(logging.DEBUG, logger=sep.logger.name):
        sep.warn_stale_entry_points()  # must not raise

    assert not [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("skipping" in r.getMessage() for r in caplog.records)


def test_scan_runs_once_per_process(monkeypatch):
    calls = []

    def _counting():
        calls.append(1)
        return iter([])

    monkeypatch.setattr(sep.metadata, "distributions", _counting)
    sep.warn_stale_entry_points()
    sep.warn_stale_entry_points()
    sep.warn_stale_entry_points()

    assert len(calls) == 1


def test_fail_open_result_is_also_cached(monkeypatch):
    """A failed scan is not retried — the guard flips before the scan."""
    calls = []

    def _boom():
        calls.append(1)
        raise RuntimeError("corrupt metadata")

    monkeypatch.setattr(sep.metadata, "distributions", _boom)
    sep.warn_stale_entry_points()
    sep.warn_stale_entry_points()

    assert len(calls) == 1


def test_real_metadata_round_trip(tmp_path, monkeypatch, caplog):
    """Non-mocked round trip: a real dist-info on sys.path is detected.

    Exercises the actual importlib.metadata boundary instead of fakes —
    the scan must find a genuine ``*.dist-info`` declaring a collapsed
    group, exactly as pip would have installed it.
    """
    dist_info = tmp_path / "legacy_ext-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: legacy-ext\nVersion: 1.0\n",
        encoding="utf-8",
    )
    (dist_info / "entry_points.txt").write_text(
        "[attune.plugins]\nlegacy = legacy_ext:Plugin\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with caplog.at_level(logging.WARNING, logger=sep.logger.name):
        sep.warn_stale_entry_points()

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "legacy-ext" in m and "'attune.plugins'" in m and sep.MIGRATION_GUIDE in m for m in messages
    )


def test_plugin_registry_auto_discover_triggers_scan(monkeypatch):
    """The plugin registry's first load runs the detector."""
    from attune.plugins import registry as plugin_registry

    calls = []
    monkeypatch.setattr(sep, "warn_stale_entry_points", lambda: calls.append(1))
    reg = plugin_registry.PluginRegistry()
    reg.auto_discover()

    assert calls == [1]


def test_wizard_builtin_load_triggers_scan(monkeypatch):
    """The wizard registry's built-in load runs the detector."""
    from attune.wizards import registry as wizard_registry

    calls = []
    monkeypatch.setattr(sep, "warn_stale_entry_points", lambda: calls.append(1))
    monkeypatch.setattr(wizard_registry, "_WIZARD_REGISTRY", {})
    wizard_registry._load_builtins()

    assert calls == [1]
