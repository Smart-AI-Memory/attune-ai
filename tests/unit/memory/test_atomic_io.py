"""The durability primitives, exercised against the real filesystem.

Every case here came out of the codex D11 review lane on the tier-1
library-review fix (2026-08-20): the first version of these primitives
closed the temp-name collision and the whole-store lost update, but left
three narrower races behind. Real files, real subprocesses, real locks —
per the class M ruling, a test may not stand in for the boundary its fix
is about.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time

import pytest

from attune.memory.atomic_io import STALE_LOCK_SECONDS, append_line, atomic_write_text, file_lock


def test_lock_is_exclusive_between_processes(tmp_path):
    """The basic guarantee, across a real process boundary."""
    target = tmp_path / "store.json"
    target.write_text("{}", encoding="utf-8")

    script = textwrap.dedent(
        f"""
        from attune.memory.atomic_io import file_lock
        with file_lock({str(target)!r}, timeout=0.2) as got:
            print("ACQUIRED" if got else "REFUSED")
        """
    )
    with file_lock(target) as locked:
        assert locked
        peer = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, check=False
        )

    assert "REFUSED" in peer.stdout, peer.stdout + peer.stderr


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX-only: Windows can't unlink a lock file file_lock holds open "
    "(WinError 32), so a peer can never break-and-retake it — the ABA race "
    "this guards against cannot occur on Windows.",
)
def test_release_does_not_delete_a_lock_we_no_longer_own(tmp_path):
    """The ABA race: a broken-as-stale holder must not free the new owner.

    Reproduced by breaking OUR lock from underneath us — exactly what
    ``_break_if_stale`` does to a holder that outran the stale window —
    and then letting a peer take it. On release we must leave the peer's
    lock alone.
    """
    target = tmp_path / "store.json"
    lock_path = target.with_name(target.name + ".lock")

    with file_lock(target) as locked:
        assert locked
        # A peer decides our lock is stale and breaks it, then takes it.
        lock_path.unlink()
        lock_path.write_text("peer-token", encoding="utf-8")

    assert lock_path.exists(), "released a lock that belonged to someone else"
    assert lock_path.read_text(encoding="ascii") == "peer-token"
    lock_path.unlink()


def test_a_lock_left_by_a_dead_holder_is_broken(tmp_path):
    """Staleness still works — the ABA fix must not wedge the store."""
    target = tmp_path / "store.json"
    lock_path = target.with_name(target.name + ".lock")
    lock_path.write_text("99999:deadbeef", encoding="ascii")
    old = time.time() - (STALE_LOCK_SECONDS + 5)
    os.utime(lock_path, (old, old))

    with file_lock(target, timeout=1.0) as locked:
        assert locked is True


def test_a_fresh_peer_lock_is_waited_out_not_broken(tmp_path):
    """A lock inside the stale window is respected until the timeout."""
    target = tmp_path / "store.json"
    lock_path = target.with_name(target.name + ".lock")
    lock_path.write_text("99999:deadbeef", encoding="ascii")

    started = time.monotonic()
    with file_lock(target, timeout=0.3) as locked:
        assert locked is False
    assert time.monotonic() - started >= 0.3
    lock_path.unlink()


def test_atomic_write_leaves_no_temp_file_behind(tmp_path):
    target = tmp_path / "store.json"
    atomic_write_text(target, json.dumps({"a": 1}))

    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["store.json"]


def test_atomic_write_cleans_up_when_the_write_fails(tmp_path):
    """A failed write must not leave a temp file for the next glob to find."""
    target = tmp_path / "store.json"

    class _Unserializable:
        pass

    with pytest.raises(TypeError):
        atomic_write_text(target, json.dumps({"a": _Unserializable()}))  # raises before write

    assert list(tmp_path.iterdir()) == []


def test_append_line_adds_the_newline_it_needs(tmp_path):
    target = tmp_path / "log.jsonl"
    append_line(target, '{"a": 1}')
    append_line(target, '{"a": 2}\n')

    assert target.read_text(encoding="utf-8") == '{"a": 1}\n{"a": 2}\n'
