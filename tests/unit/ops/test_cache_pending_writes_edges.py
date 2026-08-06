"""Edge coverage for the session-summary cache and pending-writes helpers.

Targets the I/O-failure and malformed-record branches the round-trip
suites skip: cache load validation (shape, key, field coercion),
atomic-save failure cleanup, journal parsing, PID liveness probes,
and the git-status / transient-path heuristics. All keyless; every
"failure" is injected via monkeypatch or crafted files.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune.ops import session_summary_cache as cache
from attune.ops.routes import pending_writes as pw
from attune.ops.session_summary_cache import (
    CacheKey,
    _hash_tail,
    _suppress_oserror,
    cache_path_for,
    compute_cache_key,
    load,
    save,
)


def _write_cache_record(attune_home: Path, session_id: str, record: object) -> Path:
    path = cache_path_for(attune_home, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = record if isinstance(record, str) else json.dumps(record)
    path.write_text(content, encoding="utf-8")
    return path


def _key(**overrides: object) -> CacheKey:
    base: dict[str, object] = {"filename": "s.jsonl", "mtime_ns": 123, "sha256": "abc"}
    base.update(overrides)
    return CacheKey(**base)  # type: ignore[arg-type]


class TestHashTailFailures:
    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _hash_tail(tmp_path / "absent.jsonl") is None

    def test_open_failure_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "s.jsonl"
        target.write_text("data\n", encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> None:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "open", _boom)
        assert _hash_tail(target) is None

    def test_compute_cache_key_none_when_digest_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "s.jsonl"
        target.write_text("data\n", encoding="utf-8")
        monkeypatch.setattr(cache, "_hash_tail", lambda p: None)
        assert compute_cache_key(target) is None


class TestLoadValidation:
    def test_read_failure_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_cache_record(tmp_path, "s1", {"key": {}})

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert load(tmp_path, "s1", _key()) is None

    def test_non_dict_payload_returns_none(self, tmp_path: Path) -> None:
        _write_cache_record(tmp_path, "s1", [1, 2, 3])
        assert load(tmp_path, "s1", _key()) is None

    def test_non_dict_key_returns_none(self, tmp_path: Path) -> None:
        _write_cache_record(tmp_path, "s1", {"key": "not-a-dict"})
        assert load(tmp_path, "s1", _key()) is None

    def test_missing_key_field_returns_none(self, tmp_path: Path) -> None:
        _write_cache_record(tmp_path, "s1", {"key": {"filename": "s.jsonl"}})
        assert load(tmp_path, "s1", _key()) is None

    def test_uncoercible_mtime_returns_none(self, tmp_path: Path) -> None:
        _write_cache_record(
            tmp_path,
            "s1",
            {"key": {"filename": "s.jsonl", "mtime_ns": "not-int", "sha256": "abc"}},
        )
        assert load(tmp_path, "s1", _key()) is None

    def test_matching_key_but_missing_summary_returns_none(self, tmp_path: Path) -> None:
        _write_cache_record(
            tmp_path,
            "s1",
            {"key": {"filename": "s.jsonl", "mtime_ns": 123, "sha256": "abc"}},
        )
        assert load(tmp_path, "s1", _key()) is None

    def test_hit_defaults_optional_fields(self, tmp_path: Path) -> None:
        _write_cache_record(
            tmp_path,
            "s1",
            {
                "key": {"filename": "s.jsonl", "mtime_ns": 123, "sha256": "abc"},
                "summary": "the summary",
            },
        )
        hit = load(tmp_path, "s1", _key())
        assert hit is not None
        assert hit.source == "cached"
        assert (hit.tokens_in, hit.tokens_out, hit.cost_usd) == (0, 0, 0.0)
        assert hit.created_at == ""


class TestSaveFailureCleanup:
    def test_replace_failure_raises_and_cleans_temp(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(self: Path, target: Path) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "replace", _boom)
        with pytest.raises(OSError, match="disk full"):
            save(
                tmp_path,
                "s1",
                key=_key(),
                summary="x",
                tokens_in=1,
                tokens_out=2,
                cost_usd=0.01,
            )
        cache_dir = cache_path_for(tmp_path, "s1").parent
        assert list(cache_dir.glob("*.tmp")) == []

    def test_suppress_oserror_contextmanager(self) -> None:
        with _suppress_oserror():
            raise OSError("swallowed")
        with pytest.raises(ValueError, match="propagates"), _suppress_oserror():
            raise ValueError("propagates")


class TestLoadJournalEntries:
    def test_read_failure_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        journal = tmp_path / "pending_writes.jsonl"
        journal.write_text('{"ok": 1}\n', encoding="utf-8")

        def _boom(self: Path, *args: object, **kwargs: object) -> str:
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "read_text", _boom)
        assert pw._load_journal_entries(journal) == []

    def test_blank_and_corrupt_lines_skipped(self, tmp_path: Path) -> None:
        journal = tmp_path / "pending_writes.jsonl"
        journal.write_text('\n   \n{broken\n{"ok": 1}\n', encoding="utf-8")
        assert pw._load_journal_entries(journal) == [{"ok": 1}]


class TestIsDashboardRunning:
    def test_non_positive_pid(self) -> None:
        assert pw._is_dashboard_running(0) is False
        assert pw._is_dashboard_running(-5) is False

    @pytest.mark.parametrize(
        ("exc", "expected"),
        [
            (ProcessLookupError(), False),
            (PermissionError(), True),
            (OSError("odd"), False),
        ],
    )
    def test_kill_probe_outcomes(
        self, monkeypatch: pytest.MonkeyPatch, exc: OSError, expected: bool
    ) -> None:
        def _kill(pid: int, sig: int) -> None:
            raise exc

        monkeypatch.setattr(os, "kill", _kill)
        assert pw._is_dashboard_running(12345) is expected

    def test_alive_pid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(os, "kill", lambda pid, sig: None)
        assert pw._is_dashboard_running(12345) is True


class TestCollectDirtyPaths:
    def test_missing_project_root(self, tmp_path: Path) -> None:
        assert pw._collect_dirty_paths(tmp_path / "absent") is None

    def test_git_failure_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(*args: object, **kwargs: object) -> None:
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr(pw.subprocess, "run", _boom)
        assert pw._collect_dirty_paths(tmp_path) is None

    def test_nonzero_exit_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            pw.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=128, stdout=""),
        )
        assert pw._collect_dirty_paths(tmp_path) is None

    def test_parses_statuses_renames_and_quotes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stdout = ' M f.py\n?? new.txt\nR  old.py -> new.py\n?? "sp ace.md"\n'
        monkeypatch.setattr(
            pw.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=0, stdout=stdout),
        )
        assert pw._collect_dirty_paths(tmp_path) == {
            "f.py",
            "new.txt",
            "old.py",
            "new.py",
            "sp ace.md",
        }


class TestIsFileCommitted:
    def test_unknown_dirty_set_returns_none(self, tmp_path: Path) -> None:
        assert pw._is_file_committed(tmp_path / "f.py", tmp_path, None) is None

    def test_file_outside_root(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "elsewhere.py"
        assert pw._is_file_committed(outside, root, set()) is None

    def test_clean_and_dirty_membership(self, tmp_path: Path) -> None:
        assert pw._is_file_committed(tmp_path / "f.py", tmp_path, set()) is True
        assert pw._is_file_committed(tmp_path / "f.py", tmp_path, {"f.py"}) is False


class TestIsRealEntry:
    def test_missing_or_non_string_root_rejected(self) -> None:
        assert pw._is_real_entry({}) is False
        assert pw._is_real_entry({"project_root": ""}) is False
        assert pw._is_real_entry({"project_root": 42}) is False

    def test_tmp_prefixed_root_rejected(self) -> None:
        assert pw._is_real_entry({"project_root": "/tmp/pytest-of-x/proj"}) is False

    def test_nonexistent_root_rejected(self) -> None:
        # Not under a tmp prefix, but gone from disk.
        assert pw._is_real_entry({"project_root": "/nonexistent-root-xyz/proj"}) is False

    def test_is_dir_error_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _boom(self: Path) -> bool:
            raise OSError("stat failed")

        monkeypatch.setattr(Path, "is_dir", _boom)
        assert pw._is_real_entry({"project_root": "/somewhere/real"}) is False

    def test_real_repo_root_accepted(self) -> None:
        # The test file's own repo directory: exists and is not under
        # any transient-path prefix.
        repo_dir = str(Path(__file__).resolve().parent)
        if any(repo_dir.startswith(p) for p in pw._TMP_PATH_PREFIXES):
            pytest.skip("test checkout itself lives under a tmp prefix")
        assert pw._is_real_entry({"project_root": repo_dir}) is True


class TestEnrichEdges:
    def test_bad_timestamp_and_missing_paths(self) -> None:
        enriched = pw._enrich(
            {"ts": "not-a-date", "dashboard_pid": "not-an-int"},
            now=datetime.now(timezone.utc),
            dirty_by_root={},
        )
        assert enriched["age_seconds"] is None
        assert enriched["dashboard_still_running"] is False
        assert enriched["current_disk_sha256"] is None
        assert enriched["matches_journal"] is False
        assert enriched["is_committed"] is None
