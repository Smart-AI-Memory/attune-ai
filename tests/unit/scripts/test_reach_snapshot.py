"""Tests for scripts/reach_snapshot.py (usage-signals R4).

Network boundaries (pypistats HTTP, gh subprocess) are mocked; the
spacing/abort logic, snapshot shape, table rendering, and CLI exit
codes run real.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "reach_snapshot.py"

STATS = {"last_day": 1, "last_week": 7, "last_month": 30}


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_reach_snapshot", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_reach_snapshot"] = m
    try:
        spec.loader.exec_module(m)
        yield m
    finally:
        sys.modules.pop("_reach_snapshot", None)


class TestBuildSnapshot:
    def test_spacing_between_requests_not_before_first(self, mod, monkeypatch) -> None:
        sleeps: list[float] = []
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        snap = mod.build_snapshot(
            ["a", "b", "c"],
            spacing_seconds=60,
            fetcher=lambda pkg: dict(STATS),
            sleeper=sleeps.append,
        )
        assert sleeps == [60, 60]  # n-1 sleeps, none before the first
        assert set(snap["pypi_recent"]) == {"a", "b", "c"}
        assert snap["pypi_recent"]["a"] == STATS

    def test_rate_limit_aborts_without_further_fetches(self, mod, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        fetched: list[str] = []

        def fetcher(pkg: str):
            fetched.append(pkg)
            if pkg == "b":
                raise mod.RateLimitedError("wait 15 minutes")
            return dict(STATS)

        with pytest.raises(mod.RateLimitedError):
            mod.build_snapshot(
                ["a", "b", "c"], spacing_seconds=0, fetcher=fetcher, sleeper=lambda s: None
            )
        assert fetched == ["a", "b"]  # c never attempted


class TestRenderTable:
    def test_table_has_all_packages_and_github_line(self, mod) -> None:
        snap = {
            "date": "2026-06-12",
            "pypi_recent": {"attune-ai": STATS},
            "github": {"stars": 5},
        }
        out = mod.render_table(snap)
        assert "| attune-ai | 1 | 7 | 30 |" in out
        assert "stars=5" in out

    def test_table_omits_github_line_when_empty(self, mod) -> None:
        snap = {"date": "2026-06-12", "pypi_recent": {}, "github": {}}
        assert "GitHub:" not in mod.render_table(snap)


class TestCli:
    def test_writes_dated_json_and_prints_table(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(mod, "fetch_pypistats_recent", lambda pkg: dict(STATS))
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {"stars": 9})
        rc = mod.main(["--out", str(tmp_path), "--spacing", "0", "--packages", "attune-ai"])
        assert rc == 0
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["pypi_recent"]["attune-ai"] == STATS
        assert data["github"] == {"stars": 9}
        out = capsys.readouterr().out
        assert "| attune-ai | 1 | 7 | 30 |" in out

    def test_rate_limited_exit_1_with_wait_message(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        def boom(pkg: str):
            raise mod.RateLimitedError("pypistats rate-limited. Wait 15 minutes")

        monkeypatch.setattr(mod, "fetch_pypistats_recent", boom)
        rc = mod.main(["--out", str(tmp_path), "--spacing", "0", "--packages", "attune-ai"])
        assert rc == 1
        assert "Wait 15 minutes" in capsys.readouterr().err
        assert not list(tmp_path.glob("*.json"))
