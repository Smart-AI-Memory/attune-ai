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
        """Concurrent appends from two processes lose nothing, exactly.

        On POSIX, ``O_APPEND`` guarantees atomic appends for writes
        ≤ ``PIPE_BUF`` (typically 4096B); our ~250-400B entries are
        well under that.

        On Windows, the CRT's ``O_APPEND`` is seek-to-end + write —
        not atomic — so appends serialize on the backend's
        ``msvcrt.locking`` sentinel-byte mutex. Before that lock
        existed this branch tolerated a 15% loss rate and still
        flaked (a 2026-07-30 CI run rolled 19/100 lost); with the
        lock the assertion is exact on every platform. If this ever
        fails on the Windows lane again, the lock is broken — that
        is a real regression, not scheduling variance.
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
        assert len(missing) == 0, f"lost {len(missing)} entries: {sorted(missing)[:5]}..."


class _FakeMsvcrt:
    """Records locking() calls; optionally refuses non-blocking locks."""

    LK_NBLCK = 1
    LK_UNLCK = 2

    def __init__(self, *, refuse_locks: bool = False) -> None:
        self.refuse_locks = refuse_locks
        self.calls: list[tuple[int, int, int]] = []  # (mode, offset, nbytes)

    def locking(self, fd: int, mode: int, nbytes: int) -> None:
        offset = os.lseek(fd, 0, os.SEEK_CUR)
        self.calls.append((mode, offset, nbytes))
        if self.refuse_locks and mode == self.LK_NBLCK:
            raise OSError("region locked by another process")


class TestWin32AppendChoreography:
    """Pin _append_win32's lock choreography with a fake msvcrt.

    Real mandatory-lock semantics only exist on Windows — the Windows
    CI lane's exact-zero concurrency test above is that receipt. These
    tests run on every platform and pin the choreography instead:
    lock and unlock happen at the same sentinel offset around the
    write, and a lock timeout degrades to an unlocked append rather
    than dropping the entry.
    """

    @pytest.fixture()
    def _posix_o_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # os.O_BINARY only exists on Windows; give POSIX a no-op value
        # (on Windows this reassigns the real value — a no-op).
        monkeypatch.setattr(os, "O_BINARY", getattr(os, "O_BINARY", 0), raising=False)

    def _line(self, run_id: str) -> bytes:
        return (json.dumps(_entry(run_id=run_id).to_dict()) + "\n").encode("utf-8")

    @pytest.mark.usefixtures("_posix_o_binary")
    def test_locks_writes_then_unlocks_at_same_offset(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.bulletin.file_backend import _WIN32_LOCK_OFFSET

        fake = _FakeMsvcrt()
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)

        backend._append_win32(self._line("locked-run"))

        # Entry landed and reads back.
        assert {e.run_id for e in backend.read_active()} == {"locked-run"}
        # Exactly one lock + one unlock, both single-byte, both at the
        # sentinel offset (unlocking elsewhere would leak the lock).
        assert [(m, n) for m, o, n in fake.calls] == [
            (fake.LK_NBLCK, 1),
            (fake.LK_UNLCK, 1),
        ]
        assert [o for _m, o, _n in fake.calls] == [_WIN32_LOCK_OFFSET, _WIN32_LOCK_OFFSET]

    @pytest.mark.usefixtures("_posix_o_binary")
    def test_lock_timeout_degrades_to_unlocked_append(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.bulletin import file_backend as fb

        fake = _FakeMsvcrt(refuse_locks=True)
        monkeypatch.setitem(sys.modules, "msvcrt", fake)
        monkeypatch.setattr(fb, "_WIN32_LOCK_TIMEOUT_S", 0.01)
        backend = FileBulletinBackend(tmp_path / "bulletin")
        backend.active_path.parent.mkdir(parents=True, exist_ok=True)

        backend._append_win32(self._line("degraded-run"))

        # Entry still landed (advisory: never blocked on the lock)...
        assert {e.run_id for e in backend.read_active()} == {"degraded-run"}
        # ...and no unlock was attempted for a lock never acquired.
        assert all(m == fake.LK_NBLCK for m, _o, _n in fake.calls)


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
