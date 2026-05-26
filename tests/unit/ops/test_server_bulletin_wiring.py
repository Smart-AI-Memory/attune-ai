"""Server-layer bulletin wiring tests.

Covers ``_build_default_runner`` and ``Config.bulletin_dir`` —
the production glue that lets the dashboard write multi-actor
bulletin entries.
"""

from __future__ import annotations

from pathlib import Path

from attune.bulletin import FileBulletinBackend
from attune.ops.config import Config
from attune.ops.server import _build_default_runner


def _make_config(*, allow_run: bool, attune_home: Path, project_root: Path) -> Config:
    return Config(
        project_root=project_root,
        attune_home=attune_home,
        allow_run=allow_run,
    )


class TestBulletinDir:
    def test_bulletin_dir_under_attune_home(self, tmp_path: Path) -> None:
        cfg = _make_config(allow_run=True, attune_home=tmp_path / "ah", project_root=tmp_path)
        assert cfg.bulletin_dir == tmp_path / "ah" / "bulletin"


class TestBuildDefaultRunner:
    def test_writeable_mode_constructs_bulletin(self, tmp_path: Path) -> None:
        """The dashboard runner gets a FileBulletinBackend in writeable mode."""
        cfg = _make_config(allow_run=True, attune_home=tmp_path / "ah", project_root=tmp_path)
        runner = _build_default_runner(cfg)
        # The bulletin was wired and points at the right directory.
        assert isinstance(runner._bulletin, FileBulletinBackend)
        assert runner._bulletin._root == cfg.bulletin_dir
        # Actor identity defaults to the dashboard shape.
        assert runner._actor_kind == "dashboard"
        assert runner._actor_id.startswith("dashboard-")

    def test_read_only_mode_skips_bulletin(self, tmp_path: Path) -> None:
        """Read-only mode must not touch the user's ~/.attune directory."""
        cfg = _make_config(allow_run=False, attune_home=tmp_path / "ah", project_root=tmp_path)
        runner = _build_default_runner(cfg)
        assert runner._bulletin is None

    def test_writeable_runner_keeps_persistence_dir(self, tmp_path: Path) -> None:
        """Existing persistence wiring is preserved alongside the bulletin."""
        cfg = _make_config(allow_run=True, attune_home=tmp_path / "ah", project_root=tmp_path)
        runner = _build_default_runner(cfg)
        assert runner.persistence_dir == cfg.runs_dir
