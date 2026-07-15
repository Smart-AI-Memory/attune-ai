"""Unit tests for the library-health snapshot collector.

Spec: docs/specs/ops-dashboard-polish/decisions.md (Phase E)

Covers:

- ``_safe``: the per-signal isolation wrapper (success + failure).
- Each ``_signal_*`` collector in isolation, with network/subprocess
  calls monkeypatched — no real HTTP requests, no dependency on
  ``gh``/network being available in CI.
- ``collect_snapshot``: full orchestration with every signal mocked;
  asserts a signal failure never propagates past ``_safe``.
- Persistence: atomic write, ``latest.json`` overwrite semantics, no
  leftover tempfiles, corrupt-file handling.
- ``is_stale`` boundary behavior.
- ``HealthRefreshRunner``: single-in-flight-job guard.
- ``main()`` CLI entry.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

from attune.ops import health_snapshot as hs

# ---------------------------------------------------------------------------
# _safe
# ---------------------------------------------------------------------------


class TestSafe:
    def test_success_wraps_value(self) -> None:
        result = hs._safe(lambda: 42)
        assert result == {"status": "ok", "value": 42}

    def test_exception_degrades_to_unavailable(self) -> None:
        def boom() -> None:
            raise RuntimeError("network is down")

        result = hs._safe(boom)
        assert result == {"status": "unavailable", "reason": "network is down"}

    def test_exception_without_message_uses_class_name(self) -> None:
        def boom() -> None:
            raise ValueError

        result = hs._safe(boom)
        assert result["status"] == "unavailable"
        assert result["reason"] == "ValueError"

    def test_passes_args_and_kwargs(self) -> None:
        result = hs._safe(lambda a, b, c=0: a + b + c, 1, 2, c=3)
        assert result == {"status": "ok", "value": 6}


# ---------------------------------------------------------------------------
# _signal_coverage
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class TestSignalCoverage:
    def test_success_top_level_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse({"coverage": 94.123}))
        result = hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)
        assert result == {"coverage_percent": 94.12, "source": "codecov_api_v2"}

    def test_success_nested_totals_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "requests.get", lambda *a, **k: _FakeResponse({"totals": {"coverage": 88.0}})
        )
        result = hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)
        assert result["coverage_percent"] == 88.0

    def test_missing_coverage_field_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse({"unrelated": 1}))
        with pytest.raises(RuntimeError, match="missing a coverage field"):
            hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)

    def test_http_error_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse({}, status=404))
        import requests

        with pytest.raises(requests.HTTPError):
            hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)

    def test_invalid_repo_slug_raises(self) -> None:
        with pytest.raises(ValueError, match="owner/repo"):
            hs._signal_coverage("not-a-slug", timeout=5)

    def test_uses_codecov_token_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        def fake_get(url: str, headers: dict[str, str], timeout: int) -> _FakeResponse:
            captured["headers"] = headers
            return _FakeResponse({"coverage": 50.0})

        monkeypatch.setenv("CODECOV_TOKEN", "secret-token")
        monkeypatch.setattr("requests.get", fake_get)
        hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)
        assert captured["headers"]["Authorization"] == "Bearer secret-token"

    def test_no_token_omits_auth_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}

        def fake_get(url: str, headers: dict[str, str], timeout: int) -> _FakeResponse:
            captured["headers"] = headers
            return _FakeResponse({"coverage": 50.0})

        monkeypatch.delenv("CODECOV_TOKEN", raising=False)
        monkeypatch.setattr("requests.get", fake_get)
        hs._signal_coverage("Smart-AI-Memory/attune-ai", timeout=5)
        assert "Authorization" not in captured["headers"]


# ---------------------------------------------------------------------------
# _signal_complexity
# ---------------------------------------------------------------------------


class TestSignalComplexity:
    def test_computes_average_and_d_count(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        # A trivial function (complexity 1) and a deliberately gnarly
        # one (>=21 branches -> D-or-worse) so both buckets are covered.
        simple = "def f():\n    return 1\n"
        branches = "\n".join(f"    if x == {i}:\n        return {i}" for i in range(25))
        gnarly = f"def g(x):\n{branches}\n    return -1\n"
        (src / "a.py").write_text(simple, encoding="utf-8")
        (src / "b.py").write_text(gnarly, encoding="utf-8")

        result = hs._signal_complexity(tmp_path)
        assert result["blocks"] == 2
        assert result["d_or_worse_count"] == 1
        assert result["avg_rank"] in ("A", "B", "C", "D", "E", "F")

    def test_no_python_files_raises(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        with pytest.raises(RuntimeError, match="no complexity blocks"):
            hs._signal_complexity(tmp_path)

    def test_syntax_error_file_skipped_not_fatal(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "broken.py").write_text("def f(:\n", encoding="utf-8")
        (src / "ok.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        result = hs._signal_complexity(tmp_path)
        assert result["blocks"] == 1


# ---------------------------------------------------------------------------
# _signal_churn
# ---------------------------------------------------------------------------


class TestSignalChurn:
    def test_counts_and_ranks_top_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        fake_output = "\n".join(["src/a.py", "src/b.py", "src/a.py", "", "src/a.py", "src/c.py"])
        monkeypatch.setattr(hs, "_run_git", lambda args, cwd, timeout: fake_output)
        result = hs._signal_churn(tmp_path, timeout=5, top_n=2)
        assert result["window_days"] == 90
        assert result["total_changes"] == 5
        assert result["top_files"][0] == {"path": "src/a.py", "changes": 3}
        assert len(result["top_files"]) == 2

    def test_no_changes_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(hs, "_run_git", lambda args, cwd, timeout: "")
        result = hs._signal_churn(tmp_path, timeout=5)
        assert result["total_changes"] == 0
        assert result["top_files"] == []

    def test_git_failure_propagates(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def boom(args: Any, cwd: Any, timeout: Any) -> str:
            raise subprocess.CalledProcessError(128, ["git", "log"])

        monkeypatch.setattr(hs, "_run_git", boom)
        with pytest.raises(subprocess.CalledProcessError):
            hs._signal_churn(tmp_path, timeout=5)


# ---------------------------------------------------------------------------
# Docs gate scripts
# ---------------------------------------------------------------------------


class TestRunGateScript:
    def test_missing_script_raises(self, tmp_path: Path) -> None:
        (tmp_path / "scripts").mkdir()
        with pytest.raises(FileNotFoundError):
            hs._run_gate_script("does_not_exist.py", tmp_path, timeout=5)

    def test_clean_exit_reports_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "fake_gate.py").write_text("", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                cmd, returncode=0, stdout='{"findings": []}', stderr=""
            )

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        result = hs._run_gate_script("fake_gate.py", tmp_path, timeout=5)
        assert result == {"exit_code": 0, "clean": True, "detail": {"findings": []}}

    def test_nonzero_exit_is_a_real_finding_not_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "fake_gate.py").write_text("", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout='{"findings": [1, 2]}', stderr=""
            )

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        result = hs._run_gate_script("fake_gate.py", tmp_path, timeout=5)
        assert result["clean"] is False
        assert result["exit_code"] == 1
        assert result["detail"]["findings"] == [1, 2]

    def test_non_json_stdout_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "fake_gate.py").write_text("", encoding="utf-8")

        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="not json", stderr="")

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        with pytest.raises(RuntimeError, match="did not produce valid JSON"):
            hs._run_gate_script("fake_gate.py", tmp_path, timeout=5)


class TestProjectionDriftSignal:
    def test_delegates_to_projector_and_wraps_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import attune.authoring.projector as projector_mod

        monkeypatch.setattr(
            projector_mod,
            "check_projection_drift",
            lambda root, help_dir: ["finding 1", "finding 2"],
        )
        result = hs._signal_projection_drift(tmp_path)
        assert result == {"findings_count": 2, "findings": ["finding 1", "finding 2"]}

    def test_clean_result(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import attune.authoring.projector as projector_mod

        monkeypatch.setattr(projector_mod, "check_projection_drift", lambda root, help_dir: [])
        result = hs._signal_projection_drift(tmp_path)
        assert result == {"findings_count": 0, "findings": []}


# ---------------------------------------------------------------------------
# _signal_sloc
# ---------------------------------------------------------------------------


class TestSignalSloc:
    def test_counts_files_and_lines(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("line1\nline2\nline3\n", encoding="utf-8")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_a.py").write_text(
            "def test_one():\n    pass\n\n\nasync def test_two():\n    pass\n",
            encoding="utf-8",
        )

        result = hs._signal_sloc(tmp_path)
        assert result["src_files"] == 1
        assert result["src_lines"] == 3
        assert result["test_files"] == 1
        assert result["test_lines"] == 6
        assert result["test_to_src_ratio"] == round(6 / 3, 2)
        assert result["test_function_count"] == 2

    def test_no_src_files_raises(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        with pytest.raises(RuntimeError, match="no source files"):
            hs._signal_sloc(tmp_path)

    def test_missing_tests_dir_is_zero_not_fatal(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("x = 1\n", encoding="utf-8")
        result = hs._signal_sloc(tmp_path)
        assert result["test_files"] == 0
        assert result["test_lines"] == 0
        assert result["test_to_src_ratio"] == 0.0
        assert result["test_function_count"] == 0


class TestCountTestFunctions:
    def test_counts_sync_and_async_defs(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.py").write_text(
            "def test_one():\n    pass\n\n\nasync def test_two():\n    pass\n",
            encoding="utf-8",
        )
        (tmp_path / "test_b.py").write_text(
            "class TestThing:\n    def test_three(self):\n        pass\n",
            encoding="utf-8",
        )

        assert hs._count_test_functions(tmp_path) == 3

    def test_ignores_non_test_defs(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.py").write_text(
            "def helper():\n    pass\n\n\ndef test_real():\n    pass\n",
            encoding="utf-8",
        )

        assert hs._count_test_functions(tmp_path) == 1

    def test_empty_dir_is_zero(self, tmp_path: Path) -> None:
        assert hs._count_test_functions(tmp_path) == 0


# ---------------------------------------------------------------------------
# _signal_todos
# ---------------------------------------------------------------------------


class TestSignalTodos:
    def test_counts_todo_fixme_xxx(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text(
            "# TODO: fix this\ndef f():\n    pass  # FIXME later\n# XXX hack\n",
            encoding="utf-8",
        )
        result = hs._signal_todos(tmp_path)
        assert result["count"] == 3

    def test_no_markers_returns_zero(self, tmp_path: Path) -> None:
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        result = hs._signal_todos(tmp_path)
        assert result["count"] == 0

    def test_missing_src_dir_returns_zero(self, tmp_path: Path) -> None:
        result = hs._signal_todos(tmp_path)
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# _signal_open_prs_issues
# ---------------------------------------------------------------------------


class TestSignalOpenPrsIssues:
    def test_counts_from_gh_cli(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            if "pr" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout=json.dumps([{"number": 1}, {"number": 2}])
                )
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps([{"number": 9}]))

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        result = hs._signal_open_prs_issues(timeout=5)
        assert result == {"open_prs": 2, "open_issues": 1}

    def test_gh_not_installed_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError("gh not found")

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        with pytest.raises(FileNotFoundError):
            hs._signal_open_prs_issues(timeout=5)

    def test_gh_not_authenticated_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, cmd)

        monkeypatch.setattr(hs.subprocess, "run", fake_run)
        with pytest.raises(subprocess.CalledProcessError):
            hs._signal_open_prs_issues(timeout=5)


# ---------------------------------------------------------------------------
# collect_snapshot — full orchestration, everything mocked
# ---------------------------------------------------------------------------


class TestCollectSnapshot:
    def test_shape_and_schema_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Every individual signal is unmocked here and will fail for
        # trivial reasons (no src/, no network, no gh) — the point of
        # this test is that collect_snapshot NEVER raises regardless.
        snapshot = hs.collect_snapshot(tmp_path, timeout=1)
        assert snapshot["schema_version"] == 1
        assert "collected_at" in snapshot
        assert snapshot["project_root"] == str(tmp_path)
        expected_signals = {
            "coverage",
            "complexity",
            "churn",
            "doc_import_audit",
            "docs_wiring_audit",
            "help_completeness",
            "projection_drift",
            "sloc",
            "todos",
            "open_prs_issues",
        }
        assert set(snapshot["signals"]) == expected_signals
        for name, signal in snapshot["signals"].items():
            assert signal["status"] in ("ok", "unavailable"), name

    def test_never_raises_even_when_every_signal_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force every underlying _signal_* collector to raise, so this
        # test is deterministic regardless of the sandbox's actual
        # network/gh-auth state (some signals — todos, projection_drift
        # on an empty masters glob — are legitimately tolerant of a
        # bare tmp_path and would report "ok" with a zero value rather
        # than failing, which is correct behavior but not what this
        # test is isolating). The point here is purely: one exploding
        # signal (or ten) never propagates past collect_snapshot.
        signal_names = [
            "_signal_coverage",
            "_signal_complexity",
            "_signal_churn",
            "_signal_doc_import_audit",
            "_signal_docs_wiring_audit",
            "_signal_help_completeness",
            "_signal_projection_drift",
            "_signal_sloc",
            "_signal_todos",
            "_signal_open_prs_issues",
        ]

        def _boom(*a: Any, **k: Any) -> None:
            raise RuntimeError("forced failure")

        for name in signal_names:
            monkeypatch.setattr(hs, name, _boom)

        snapshot = hs.collect_snapshot(tmp_path, timeout=1)
        statuses = {name: sig["status"] for name, sig in snapshot["signals"].items()}
        assert all(status == "unavailable" for status in statuses.values()), statuses


# ---------------------------------------------------------------------------
# latest_llm_report
# ---------------------------------------------------------------------------


class TestLatestLlmReport:
    def test_picks_lexicographically_latest(self, tmp_path: Path) -> None:
        reports = tmp_path / "docs" / "reports"
        reports.mkdir(parents=True)
        (reports / "library-health-2026-06-01.md").write_text("old", encoding="utf-8")
        (reports / "library-health-2026-07-14.md").write_text("new", encoding="utf-8")
        result = hs.latest_llm_report(tmp_path)
        assert result == "docs/reports/library-health-2026-07-14.md"

    def test_no_reports_dir_returns_none(self, tmp_path: Path) -> None:
        assert hs.latest_llm_report(tmp_path) is None

    def test_not_relative_falls_back_to_absolute_posix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The defensive ValueError fallback still yields forward slashes."""
        reports = tmp_path / "docs" / "reports"
        reports.mkdir(parents=True)
        (reports / "library-health-2026-07-14.md").write_text("x", encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> Path:
            raise ValueError("not in the subpath")

        monkeypatch.setattr(Path, "relative_to", _boom)
        result = hs.latest_llm_report(tmp_path)
        assert result == (reports / "library-health-2026-07-14.md").as_posix()
        assert "\\" not in result

    def test_empty_reports_dir_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "reports").mkdir(parents=True)
        assert hs.latest_llm_report(tmp_path) is None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_persist_and_read_round_trip(self, tmp_path: Path) -> None:
        snapshot = {"schema_version": 1, "collected_at": "2026-07-14T12:00:00+00:00", "signals": {}}
        target = hs.persist_snapshot(snapshot, tmp_path)
        assert target.exists()
        assert hs.read_latest(tmp_path) == snapshot

    def test_persist_creates_health_dir(self, tmp_path: Path) -> None:
        assert not (tmp_path / "ops" / "health").exists()
        snapshot = {"schema_version": 1, "collected_at": "2026-07-14T12:00:00+00:00", "signals": {}}
        hs.persist_snapshot(snapshot, tmp_path)
        assert (tmp_path / "ops" / "health").is_dir()

    def test_persist_writes_timestamped_and_latest(self, tmp_path: Path) -> None:
        snapshot = {"schema_version": 1, "collected_at": "2026-07-14T12:00:00+00:00", "signals": {}}
        hs.persist_snapshot(snapshot, tmp_path)
        files = sorted(p.name for p in hs.health_dir(tmp_path).iterdir())
        assert "latest.json" in files
        assert "2026-07-14T12-00-00+00-00.json" in files

    def test_no_tempfile_left_behind(self, tmp_path: Path) -> None:
        snapshot = {"schema_version": 1, "collected_at": "2026-07-14T12:00:00+00:00", "signals": {}}
        hs.persist_snapshot(snapshot, tmp_path)
        files = list(hs.health_dir(tmp_path).iterdir())
        assert not any(f.name.endswith(".tmp") for f in files)

    def test_latest_overwritten_by_second_write(self, tmp_path: Path) -> None:
        first = {
            "schema_version": 1,
            "collected_at": "2026-07-14T12:00:00+00:00",
            "signals": {"n": 1},
        }
        second = {
            "schema_version": 1,
            "collected_at": "2026-07-14T13:00:00+00:00",
            "signals": {"n": 2},
        }
        hs.persist_snapshot(first, tmp_path)
        hs.persist_snapshot(second, tmp_path)
        assert hs.read_latest(tmp_path) == second
        # Both timestamped files remain (history), only latest.json overwrites.
        files = [p.name for p in hs.health_dir(tmp_path).iterdir()]
        assert len([f for f in files if f != "latest.json"]) == 2

    def test_read_missing_returns_none(self, tmp_path: Path) -> None:
        assert hs.read_latest(tmp_path) is None

    def test_read_corrupt_file_returns_none(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        out_dir = hs.health_dir(tmp_path)
        (out_dir / "latest.json").write_text("{not valid", encoding="utf-8")
        with caplog.at_level("WARNING"):
            assert hs.read_latest(tmp_path) is None
        assert any("unreadable" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# is_stale
# ---------------------------------------------------------------------------


class TestIsStale:
    def test_none_snapshot_is_stale(self) -> None:
        assert hs.is_stale(None) is True

    def test_missing_collected_at_is_stale(self) -> None:
        assert hs.is_stale({"signals": {}}) is True

    def test_malformed_timestamp_is_stale(self) -> None:
        assert hs.is_stale({"collected_at": "not-a-timestamp"}) is True

    def test_fresh_snapshot_is_not_stale(self) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        assert hs.is_stale({"collected_at": now}) is False

    def test_old_snapshot_is_stale(self) -> None:
        from datetime import datetime, timedelta, timezone

        old = (datetime.now(timezone.utc) - timedelta(hours=13)).isoformat()
        assert hs.is_stale({"collected_at": old}) is True

    def test_boundary_respects_custom_max_age(self) -> None:
        from datetime import datetime, timedelta, timezone

        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert hs.is_stale({"collected_at": two_hours_ago}, max_age_hours=1) is True
        assert hs.is_stale({"collected_at": two_hours_ago}, max_age_hours=3) is False

    def test_naive_timestamp_treated_as_utc(self) -> None:
        from datetime import datetime

        naive_now = datetime.now().isoformat()
        assert hs.is_stale({"collected_at": naive_now}) is False


# ---------------------------------------------------------------------------
# HealthRefreshRunner
# ---------------------------------------------------------------------------


class TestHealthRefreshRunner:
    def test_start_returns_true_and_running_reflects_thread(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        release = threading.Event()
        started = threading.Event()

        def fake_run_and_persist(project_root: Path, attune_home: Path, **kwargs: Any) -> Path:
            started.set()
            release.wait(timeout=5)
            return tmp_path / "snapshot.json"

        monkeypatch.setattr(hs, "run_and_persist", fake_run_and_persist)
        runner = hs.HealthRefreshRunner()
        assert runner.running is False

        result = runner.start(tmp_path, tmp_path)
        assert result is True
        assert started.wait(timeout=5)
        assert runner.running is True

        release.set()
        # Give the thread a moment to finish.
        for _ in range(50):
            if not runner.running:
                break
            threading.Event().wait(0.05)
        assert runner.running is False

    def test_start_is_noop_while_already_running(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        release = threading.Event()
        started = threading.Event()
        call_count = {"n": 0}

        def fake_run_and_persist(project_root: Path, attune_home: Path, **kwargs: Any) -> Path:
            call_count["n"] += 1
            started.set()
            release.wait(timeout=5)
            return tmp_path / "snapshot.json"

        monkeypatch.setattr(hs, "run_and_persist", fake_run_and_persist)
        runner = hs.HealthRefreshRunner()
        assert runner.start(tmp_path, tmp_path) is True
        assert started.wait(timeout=5)
        # Second start while the first is still in flight is a no-op.
        assert runner.start(tmp_path, tmp_path) is False
        assert call_count["n"] == 1
        release.set()

    def test_background_exception_is_caught_not_raised(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        def boom(project_root: Path, attune_home: Path, **kwargs: Any) -> Path:
            raise RuntimeError("collector exploded")

        monkeypatch.setattr(hs, "run_and_persist", boom)
        runner = hs.HealthRefreshRunner()
        with caplog.at_level("ERROR"):
            assert runner.start(tmp_path, tmp_path) is True
            thread = runner._thread
            assert thread is not None
            thread.join(timeout=5)
        assert runner.running is False
        assert any("background refresh failed" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# run_and_persist
# ---------------------------------------------------------------------------


class TestRunAndPersist:
    def test_collects_and_persists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_snapshot = {
            "schema_version": 1,
            "collected_at": "2026-07-14T12:00:00+00:00",
            "signals": {},
        }
        monkeypatch.setattr(hs, "collect_snapshot", lambda *a, **k: fake_snapshot)
        target = hs.run_and_persist(tmp_path, tmp_path)
        assert target.exists()
        assert hs.read_latest(tmp_path) == fake_snapshot


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


class TestMain:
    def test_writes_snapshot_and_prints_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        fake_snapshot = {
            "schema_version": 1,
            "collected_at": "2026-07-14T12:00:00+00:00",
            "signals": {},
        }
        monkeypatch.setattr(hs, "collect_snapshot", lambda *a, **k: fake_snapshot)
        exit_code = hs.main(
            ["--project-root", str(tmp_path), "--attune-home", str(tmp_path / "home")]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Wrote" in captured.out
        assert hs.read_latest(tmp_path / "home") == fake_snapshot

    def test_defaults_attune_home_when_not_provided(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake_snapshot = {
            "schema_version": 1,
            "collected_at": "2026-07-14T12:00:00+00:00",
            "signals": {},
        }
        monkeypatch.setattr(hs, "collect_snapshot", lambda *a, **k: fake_snapshot)
        monkeypatch.setattr("attune.ops.config.attune_home", lambda: tmp_path / "default-home")
        exit_code = hs.main(["--project-root", str(tmp_path)])
        assert exit_code == 0
        assert hs.read_latest(tmp_path / "default-home") == fake_snapshot
