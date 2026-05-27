"""Unit tests for FileBulletinBackend.

Covers:
- append/read roundtrip
- dedupe by run_id keeps newest heartbeat
- terminal entries are excluded from active reads
- stale entries (heartbeat > 90s old) are dropped on read
- two concurrent writers don't lose entries
- malformed lines are skipped, not fatal
- unwritable bulletin dir degrades gracefully
- daily rotation moves yesterday's log into archive/
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.bulletin import BulletinEntry, FileBulletinBackend


def _entry(
    *,
    actor_id: str = "actor-A",
    workflow: str = "code-review",
    run_id: str = "run-1",
    status: str = "running",
    heartbeat: str | None = None,
) -> BulletinEntry:
    """Build a test entry. Heartbeat defaults to now."""
    return BulletinEntry(
        actor_id=actor_id,
        actor_kind="cli",
        workflow=workflow,
        run_id=run_id,
        current_status=status,
        last_heartbeat=heartbeat or datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Basic roundtrip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_append_then_read_returns_entry(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        entry = _entry()
        backend.append(entry)

        active = backend.read_active()
        assert len(active) == 1
        assert active[0].run_id == "run-1"
        assert active[0].actor_id == "actor-A"

    def test_read_active_empty_when_no_log(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        assert backend.read_active() == []

    def test_read_active_empty_after_no_appends(self, tmp_path: Path) -> None:
        """Directory exists but log file doesn't yet."""
        root = tmp_path / "bulletin"
        root.mkdir()
        backend = FileBulletinBackend(root)
        assert backend.read_active() == []

    def test_creates_directory_lazily(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "nested" / "bulletin")
        backend.append(_entry())
        assert (tmp_path / "nested" / "bulletin" / "active.jsonl").exists()


# ---------------------------------------------------------------------------
# Dedupe by run_id
# ---------------------------------------------------------------------------


class TestDedupe:
    def test_newer_heartbeat_supersedes_older(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        now = datetime.now(timezone.utc)
        backend.append(_entry(heartbeat=(now - timedelta(seconds=30)).isoformat()))
        backend.append(_entry(heartbeat=now.isoformat()))

        active = backend.read_active()
        assert len(active) == 1
        assert active[0].last_heartbeat == now.isoformat()

    def test_different_run_ids_both_returned(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="run-1"))
        backend.append(_entry(run_id="run-2", workflow="security-audit"))

        active = backend.read_active()
        assert {e.run_id for e in active} == {"run-1", "run-2"}


# ---------------------------------------------------------------------------
# Terminal entries
# ---------------------------------------------------------------------------


class TestTerminalEntries:
    @pytest.mark.parametrize("status", ["completed", "failed", "cancelled"])
    def test_terminal_excluded_from_active(self, tmp_path: Path, status: str) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry())
        # Newer entry marks the run terminal.
        backend.append(
            _entry(
                status=status,
                heartbeat=(datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
            )
        )
        assert backend.read_active() == []


# ---------------------------------------------------------------------------
# Stale GC
# ---------------------------------------------------------------------------


class TestStaleGc:
    def test_stale_heartbeat_dropped_on_read(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        stale = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        backend.append(_entry(heartbeat=stale))

        assert backend.read_active(stale_after_seconds=90.0) == []

    def test_fresh_heartbeat_kept(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry())
        assert len(backend.read_active(stale_after_seconds=90.0)) == 1

    def test_custom_stale_threshold(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        older = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        backend.append(_entry(heartbeat=older))
        # 5s threshold: drops the 10s-old entry
        assert backend.read_active(stale_after_seconds=5.0) == []
        # 30s threshold: keeps it
        assert len(backend.read_active(stale_after_seconds=30.0)) == 1


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def _writer_task(args: tuple[str, str, int]) -> None:
    """Subprocess entrypoint — append N entries with distinct run_ids."""
    root, actor_id, n = args
    backend = FileBulletinBackend(Path(root))
    for i in range(n):
        backend.append(
            BulletinEntry(
                actor_id=actor_id,
                actor_kind="cli",
                workflow="code-review",
                run_id=f"{actor_id}-{i}",
            )
        )


class TestConcurrency:
    def test_two_concurrent_writers_dont_lose_entries(self, tmp_path: Path) -> None:
        """Concurrent appends from two processes survive correctly.

        On POSIX, ``O_APPEND`` guarantees atomic appends for writes
        ≤ ``PIPE_BUF`` (typically 4096B); our ~250-400B entries are
        well under that so the assertion is exact (zero entries lost).

        On Windows, ``O_APPEND`` doesn't carry the same formal
        atomicity guarantee. Reads tolerate malformed lines, so the
        observed failure mode is "occasional skipped entry on
        contention" — empirically <10%. The Windows branch asserts
        the loss rate stays below 10%, which is the documented
        contract for the bulletin: advisory accuracy, not strict
        delivery. Switching to the Redis Streams backend (Phase 3)
        eliminates this entirely.
        """
        root = tmp_path / "bulletin"
        per_writer = 50
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=2) as pool:
            pool.map(
                _writer_task,
                [
                    (str(root), "actor-A", per_writer),
                    (str(root), "actor-B", per_writer),
                ],
            )

        backend = FileBulletinBackend(root)
        active = backend.read_active()
        run_ids = {e.run_id for e in active}
        expected = {f"actor-A-{i}" for i in range(per_writer)} | {
            f"actor-B-{i}" for i in range(per_writer)
        }
        missing = expected - run_ids

        if sys.platform == "win32":
            # Advisory: occasional skipped lines OK, drift = regression.
            loss_rate = len(missing) / len(expected)
            assert loss_rate < 0.10, (
                f"Windows loss rate {loss_rate:.1%} exceeds 10% — "
                f"lost {len(missing)}/{len(expected)} entries: "
                f"{sorted(missing)[:5]}..."
            )
        else:
            # POSIX: O_APPEND atomicity should be exact.
            assert len(missing) == 0, f"lost {len(missing)} entries: {sorted(missing)[:5]}..."


# ---------------------------------------------------------------------------
# Malformed-line tolerance
# ---------------------------------------------------------------------------


class TestMalformedLines:
    def test_malformed_lines_skipped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="run-1"))

        # Hand-inject a corrupted line, then a valid one.
        with backend.active_path.open("a", encoding="utf-8") as fh:
            fh.write("not-json-at-all\n")
            fh.write("{partial: line without closing\n")
        backend.append(_entry(run_id="run-2"))

        active = backend.read_active()
        assert {e.run_id for e in active} == {"run-1", "run-2"}

    def test_empty_lines_skipped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="run-1"))
        with backend.active_path.open("a", encoding="utf-8") as fh:
            fh.write("\n\n\n")
        assert len(backend.read_active()) == 1

    def test_non_dict_json_skipped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)
        with backend.active_path.open("w", encoding="utf-8") as fh:
            fh.write('["a", "list", "not", "a", "dict"]\n')
            fh.write("42\n")
            fh.write("null\n")
        assert backend.read_active() == []


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    def test_append_to_unwritable_dir_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bulletin is advisory — writes never raise to the caller."""
        root = tmp_path / "bulletin"
        backend = FileBulletinBackend(root)

        def _boom(*_a, **_kw):
            raise PermissionError("nope")

        monkeypatch.setattr(Path, "mkdir", _boom)
        # Must not raise.
        backend.append(_entry())

    def test_oversized_entry_dropped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        # Build an entry whose scope alone exceeds the 16K cap.
        backend.append(
            BulletinEntry(
                actor_id="A",
                actor_kind="cli",
                workflow="code-review",
                run_id="big",
                scope="x" * 20_000,
            )
        )
        assert backend.read_active() == []


# ---------------------------------------------------------------------------
# Daily rotation
# ---------------------------------------------------------------------------


class TestRotation:
    def test_yesterdays_log_moved_to_archive(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="yesterday-run"))

        # Backdate the active log's mtime to yesterday.
        yesterday = time.time() - 86_400 - 60
        os.utime(backend.active_path, (yesterday, yesterday))

        # Next append triggers rotation.
        backend.append(_entry(run_id="today-run"))

        # Active log now only has today's entry.
        active = backend.read_active()
        assert {e.run_id for e in active} == {"today-run"}

        # Archive holds yesterday's content.
        archives = list(backend.archive_dir.glob("*.jsonl"))
        assert len(archives) == 1
        with archives[0].open(encoding="utf-8") as fh:
            archived = [json.loads(line) for line in fh if line.strip()]
        assert any(e["run_id"] == "yesterday-run" for e in archived)

    def test_no_rotation_when_log_is_today(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="run-1"))
        backend.append(_entry(run_id="run-2"))
        # Archive should not exist yet.
        assert not backend.archive_dir.exists()


# ---------------------------------------------------------------------------
# Entry forward-compatibility
# ---------------------------------------------------------------------------


class TestForwardCompat:
    def test_unknown_keys_dropped_on_read(self, tmp_path: Path) -> None:
        """A newer actor may write extra fields; we tolerate them."""
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "actor_id": "A",
            "actor_kind": "cli",
            "workflow": "code-review",
            "run_id": "run-1",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "current_status": "running",
            "future_field": {"complex": "value"},
        }
        with backend.active_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

        active = backend.read_active()
        assert len(active) == 1
        assert active[0].run_id == "run-1"


# ---------------------------------------------------------------------------
# Error-path coverage (all paths swallow + log; bulletin is advisory)
# ---------------------------------------------------------------------------


class TestErrorPathsSwallowed:
    """All filesystem error paths must log + return, never raise.

    The bulletin is documented as advisory storage — workflows must
    run successfully even when the bulletin can't write.
    """

    def test_append_rotation_oserror_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")

        # Make rotation explode; append should still try to write.
        def _boom(self: FileBulletinBackend) -> None:
            raise OSError("rotation fails")

        monkeypatch.setattr(FileBulletinBackend, "_maybe_rotate", _boom)
        # Should not raise.
        backend.append(_entry(run_id="after-rotate-failure"))
        # The append's own write may or may not have run; the contract
        # is just "doesn't raise" — verified by reaching this line.

    def test_append_open_oserror_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")

        original_open = os.open

        def _selective_boom(path, flags, mode=0o777):
            if "active.jsonl" in str(path):
                raise OSError("disk full")
            return original_open(path, flags, mode)

        monkeypatch.setattr(os, "open", _selective_boom)
        # Must not raise.
        backend.append(_entry(run_id="open-fails"))

    def test_read_oserror_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="run-1"))

        def _boom(*_a, **_kw):
            raise PermissionError("cannot read")

        monkeypatch.setattr(Path, "open", _boom)
        # Read must not raise; should return [] when the iterator
        # can't open the file.
        assert backend.read_active() == []

    def test_rotation_replace_oserror_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.append(_entry(run_id="needs-rotating"))
        # Backdate so rotation triggers on next append.
        yesterday = time.time() - 86_400 - 60
        os.utime(backend.active_path, (yesterday, yesterday))

        def _boom(self, _target):
            raise OSError("permission denied")

        monkeypatch.setattr(Path, "replace", _boom)
        # Should not raise — and the active log keeps growing.
        backend.append(_entry(run_id="post-failed-rotate"))


class TestMalformedReadPaths:
    """Read path skips corrupt lines, missing fields, oversized lines."""

    def test_oversized_line_skipped_on_read(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)
        # Hand-write a line larger than _MAX_LINE_BYTES (16384) plus
        # a healthy entry. Reader should skip the huge one and keep
        # the healthy one.
        huge = "x" * 17_000
        with backend.active_path.open("w", encoding="utf-8") as fh:
            fh.write(huge + "\n")
            fh.write(json.dumps(_entry(run_id="healthy").to_dict()) + "\n")
        active = backend.read_active()
        assert {e.run_id for e in active} == {"healthy"}

    def test_missing_required_field_skipped(self, tmp_path: Path) -> None:
        """A dict missing a required field hits the TypeError branch."""
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)
        # Missing ``run_id`` — dataclass construction raises TypeError.
        bad = {
            "actor_id": "A",
            "actor_kind": "cli",
            "workflow": "code-review",
            # no run_id
        }
        with backend.active_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(bad) + "\n")
            fh.write(json.dumps(_entry(run_id="good").to_dict()) + "\n")
        active = backend.read_active()
        assert {e.run_id for e in active} == {"good"}

    def test_malformed_heartbeat_drops_entry(self, tmp_path: Path) -> None:
        """An unparseable last_heartbeat skips the entry on read."""
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "actor_id": "A",
            "actor_kind": "cli",
            "workflow": "code-review",
            "run_id": "bad-heartbeat",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "last_heartbeat": "not-an-iso-string",
            "current_status": "running",
        }
        with backend.active_path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
        # Heartbeat parse failure -> entry dropped as if stale.
        assert backend.read_active() == []


# ---------------------------------------------------------------------------
# read_archive coverage — error paths + skip conditions
# ---------------------------------------------------------------------------


class TestReadArchive:
    """Cover read_archive's edge paths: missing dir, OSError on iter,
    non-jsonl files, and non-ISO-date filenames."""

    def test_missing_archive_dir_returns_empty(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        # archive/ never created
        result = backend.read_archive(since=datetime.now(timezone.utc))
        assert result == []

    def test_iterdir_oserror_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.archive_dir.mkdir(parents=True, exist_ok=True)

        def boom(self):  # noqa: ANN001
            raise OSError("simulated")

        monkeypatch.setattr(Path, "iterdir", boom)
        result = backend.read_archive(since=datetime.now(timezone.utc))
        assert result == []

    def test_non_jsonl_files_are_skipped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.archive_dir.mkdir(parents=True, exist_ok=True)
        # A regular file with non-jsonl suffix and a subdirectory
        (backend.archive_dir / "README.md").write_text("ignore me", encoding="utf-8")
        (backend.archive_dir / "subdir").mkdir()
        # A valid jsonl-with-date file alongside the noise
        today_iso = datetime.now(timezone.utc).date().isoformat()
        valid_path = backend.archive_dir / f"{today_iso}.jsonl"
        entry = _entry(run_id="r1")
        valid_path.write_text(json.dumps(entry.to_dict()) + "\n", encoding="utf-8")
        result = backend.read_archive(since=datetime.now(timezone.utc) - timedelta(days=2))
        assert [e.run_id for e in result] == ["r1"]

    def test_non_date_filename_skipped(self, tmp_path: Path) -> None:
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.archive_dir.mkdir(parents=True, exist_ok=True)
        # File matching *.jsonl but stem isn't an ISO date
        bad = backend.archive_dir / "not-a-date.jsonl"
        bad.write_text("{}\n", encoding="utf-8")
        result = backend.read_archive(since=datetime.now(timezone.utc) - timedelta(days=1))
        assert result == []
