"""AlertEngine's database must survive a later chdir.

``alerts watch --daemon`` calls ``os.chdir("/")`` inside ``_daemonize``
while the default ``db_path`` is CWD-relative (``.attune/alerts.db``).
An unanchored path therefore resolves to ``/.attune/alerts.db`` for
every query issued after the fork, and ``sqlite3.connect`` fails with
"unable to open database file" for a non-root user — daemon mode could
not reach the database it had just created.

The same anchoring rule is documented in
``attune.memory.storage_backend.default_storage_dir``: return an
absolute path so a later chdir cannot move the target.

Copyright 2025 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from attune.monitoring.engine import AlertEngine


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    """A directory to construct the engine from, then leave."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestPathIsAnchored:
    def test_relative_db_path_becomes_absolute(self, workdir):
        engine = AlertEngine(db_path=".attune/alerts.db")

        assert engine.db_path.is_absolute()
        # Compared through resolve() on BOTH sides so the assertion is
        # symlink-agnostic (/var -> /private/var on macOS).
        assert engine.db_path.resolve() == (workdir / ".attune" / "alerts.db").resolve()

    def test_absolute_db_path_is_preserved(self, tmp_path):
        target = tmp_path / "nested" / "alerts.db"

        engine = AlertEngine(db_path=target)

        assert engine.db_path == target, "an absolute path must be preserved as given"


class TestSurvivesChdir:
    def test_engine_still_reads_its_own_database_after_chdir(self, workdir, tmp_path):
        """The daemon case: construct here, chdir away, keep querying."""
        engine = AlertEngine(db_path=".attune/alerts.db")
        created = engine.db_path
        assert created.exists(), "engine did not create its database"

        # _daemonize does exactly this.
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        os.chdir(elsewhere)

        # Would raise sqlite3.OperationalError("unable to open database
        # file") against an unanchored relative path.
        engine.list_alerts()

        assert engine.db_path == created
        assert not (elsewhere / ".attune").exists(), "engine created a second database"

    def test_chdir_to_root_does_not_strand_the_database(self, workdir):
        """The literal daemon path: os.chdir("/"), which is unwritable."""
        engine = AlertEngine(db_path=".attune/alerts.db")

        os.chdir("/")

        engine.list_alerts()
        assert engine.db_path.exists()
        assert not Path("/.attune").exists(), "engine reached for a root-level database"
