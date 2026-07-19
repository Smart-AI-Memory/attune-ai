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


def _age_attempts(out_dir: Path, *, minutes: int) -> None:
    """Rewrite the day file's attempt timestamps ``minutes`` into the past."""
    from datetime import datetime, timedelta, timezone

    (day_file,) = out_dir.glob("*.json")
    data = json.loads(day_file.read_text(encoding="utf-8"))
    aged = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    for attempt in data.get("attempts", []):
        attempt["at"] = aged
    day_file.write_text(json.dumps(data), encoding="utf-8")


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

    def test_seed_skips_already_captured_no_duplicate_fetch(self, mod, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        fetched: list[str] = []

        def fetcher(pkg: str):
            fetched.append(pkg)
            return dict(STATS)

        snap = mod.build_snapshot(
            ["a", "b", "c"],
            spacing_seconds=0,
            seed={"a": dict(STATS), "b": dict(STATS)},
            fetcher=fetcher,
            sleeper=lambda s: None,
        )
        assert fetched == ["c"]  # only the remainder fetched
        assert set(snap["pypi_recent"]) == {"a", "b", "c"}  # seed preserved

    def test_persist_called_after_each_success(self, mod, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        writes: list[set[str]] = []

        snap = mod.build_snapshot(
            ["a", "b"],
            spacing_seconds=0,
            fetcher=lambda pkg: dict(STATS),
            sleeper=lambda s: None,
            persist=lambda s: writes.append(set(s["pypi_recent"])),
        )
        # one persist per fetched package, growing the set each time
        assert writes == [{"a"}, {"a", "b"}]
        assert set(snap["pypi_recent"]) == {"a", "b"}

    def test_rate_limit_persists_packages_fetched_before_it(self, mod, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        last_write: dict[str, set[str]] = {}

        def fetcher(pkg: str):
            if pkg == "c":
                raise mod.RateLimitedError("wait 15 minutes")
            return dict(STATS)

        with pytest.raises(mod.RateLimitedError):
            mod.build_snapshot(
                ["a", "b", "c"],
                spacing_seconds=0,
                fetcher=fetcher,
                sleeper=lambda s: None,
                persist=lambda s: last_write.update(seen=set(s["pypi_recent"])),
            )
        # a and b were persisted before c's 429 discarded the run
        assert last_write["seen"] == {"a", "b"}


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


class TestUs4CompletenessAndBudget:
    """US-4: manifest contract, attempt budget, retry guidance."""

    def test_complete_capture_manifest(self, mod, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_pypistats_recent", lambda pkg: dict(STATS))
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        rc = mod.main(["--out", str(tmp_path), "--spacing", "0", "--packages", "a", "b"])
        assert rc == 0
        (day_file,) = tmp_path.glob("*.json")
        data = json.loads(day_file.read_text(encoding="utf-8"))
        manifest = data["manifest"]
        assert manifest["complete"] is True
        assert manifest["expected"] == manifest["captured"] == ["a", "b"]
        assert manifest["missing"] == []
        assert manifest["source"] == mod.SOURCE
        assert data["attempts"][-1]["outcome"] == "complete"

    def test_rerun_within_gap_refused_before_any_request(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        def boom(pkg: str):
            raise mod.RateLimitedError("rate-limited")

        monkeypatch.setattr(mod, "fetch_pypistats_recent", boom)
        argv = ["--out", str(tmp_path), "--spacing", "0", "--packages", "a"]
        assert mod.main(argv) == 1

        fetched: list[str] = []
        monkeypatch.setattr(mod, "fetch_pypistats_recent", lambda pkg: fetched.append(pkg))
        assert mod.main(argv) == 1  # refused: last attempt seconds ago
        err = capsys.readouterr().err
        assert ">= 60 minutes apart" in err
        assert fetched == []  # refused BEFORE any request

    def test_attempt_budget_exhausted_after_three(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        def boom(pkg: str):
            raise mod.RateLimitedError("rate-limited")

        monkeypatch.setattr(mod, "fetch_pypistats_recent", boom)
        argv = ["--out", str(tmp_path), "--spacing", "0", "--packages", "a"]
        for _ in range(3):
            assert mod.main(argv) == 1
            _age_attempts(tmp_path, minutes=61)
        capsys.readouterr()

        fetched: list[str] = []
        monkeypatch.setattr(mod, "fetch_pypistats_recent", lambda pkg: fetched.append(pkg))
        assert mod.main(argv) == 1
        err = capsys.readouterr().err
        assert "attempt budget exhausted" in err
        assert "INCOMPLETE SNAPSHOT" in err
        assert fetched == []
        (day_file,) = tmp_path.glob("*.json")
        data = json.loads(day_file.read_text(encoding="utf-8"))
        assert len(data["attempts"]) == 3  # the refused run logs no attempt

    def test_completed_snapshot_rerun_skips_budget(self, mod, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(mod, "fetch_pypistats_recent", lambda pkg: dict(STATS))
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})
        argv = ["--out", str(tmp_path), "--spacing", "0", "--packages", "a"]
        assert mod.main(argv) == 0
        # Immediate rerun: nothing remaining → no request, no budget trip.
        assert mod.main(argv) == 0

    def test_429_retry_after_header_is_reported(self, mod, monkeypatch) -> None:
        import io
        import urllib.error

        def raise_429(url, timeout):
            raise urllib.error.HTTPError(
                url, 429, "Too Many Requests", {"Retry-After": "1800"}, io.BytesIO(b"")
            )

        monkeypatch.setattr(mod.urllib.request, "urlopen", raise_429)
        with pytest.raises(mod.RateLimitedError, match="retry after 1800s"):
            mod.fetch_pypistats_recent("attune-ai")


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

    def test_rate_limited_exit_1_logs_attempt_even_with_zero_capture(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        """US-4 zero-package capture: unmistakable warning + durable attempt."""

        def boom(pkg: str):
            raise mod.RateLimitedError("pypistats rate-limited. Wait 15 minutes")

        monkeypatch.setattr(mod, "fetch_pypistats_recent", boom)
        rc = mod.main(["--out", str(tmp_path), "--spacing", "0", "--packages", "attune-ai"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "Wait 15 minutes" in err
        assert "INCOMPLETE SNAPSHOT" in err
        assert "0/1 captured" in err
        # Even a zero-capture run persists its attempt — else the US-4
        # budget could never engage.
        (day_file,) = tmp_path.glob("*.json")
        data = json.loads(day_file.read_text(encoding="utf-8"))
        assert data["pypi_recent"] == {}
        assert data["manifest"]["complete"] is False
        assert data["manifest"]["missing"] == ["attune-ai"]
        assert len(data["attempts"]) == 1
        assert data["attempts"][0]["outcome"] == "rate-limited"

    def test_partial_then_rate_limit_persists_progress(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {})

        def fetcher(pkg: str):
            if pkg == "c":
                raise mod.RateLimitedError("Wait 15 minutes")
            return dict(STATS)

        monkeypatch.setattr(mod, "fetch_pypistats_recent", fetcher)
        rc = mod.main(["--out", str(tmp_path), "--spacing", "0", "--packages", "a", "b", "c"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "INCOMPLETE SNAPSHOT" in err
        assert "2/3 captured" in err
        # the day file holds the two packages fetched before the 429
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert set(data["pypi_recent"]) == {"a", "b"}
        assert data["manifest"]["missing"] == ["c"]
        assert data["manifest"]["complete"] is False

    def test_rerun_completes_remainder_then_clears(
        self, mod, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(mod, "fetch_github_signals", lambda: {"stars": 9})
        fetched: list[str] = []
        flaky = {"raise_on_c": True}

        def fetcher(pkg: str):
            fetched.append(pkg)
            if pkg == "c" and flaky["raise_on_c"]:
                raise mod.RateLimitedError("Wait 15 minutes")
            return dict(STATS)

        monkeypatch.setattr(mod, "fetch_pypistats_recent", fetcher)
        argv = ["--out", str(tmp_path), "--spacing", "0", "--packages", "a", "b", "c"]

        # first run: a,b succeed, c 429s
        assert mod.main(argv) == 1
        assert fetched == ["a", "b", "c"]

        # cooldown over (age the logged attempt past the 60-min gap):
        _age_attempts(tmp_path, minutes=61)
        flaky["raise_on_c"] = False
        fetched.clear()
        assert mod.main(argv) == 0
        assert fetched == ["c"]  # a,b not re-fetched

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert set(data["pypi_recent"]) == {"a", "b", "c"}
        assert data["github"] == {"stars": 9}
