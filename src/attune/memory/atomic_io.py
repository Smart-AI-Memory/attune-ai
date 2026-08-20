"""Durable local-file primitives for the memory layer.

Library-review G1: every file-backed store rewrote its whole file
through a temp path whose name was fixed (``findings.jsonl.tmp``), and
did so without synchronization. Two processes writing at once erased
each other's records — 18 of 40 lost in a two-writer repro — and both
were told the write succeeded, because the loss happens AFTER a
successful ``replace``.

Three primitives close that:

* :func:`atomic_write_text` — a temp file unique to this process, so a
  peer's ``replace`` can never move ours out from under us.
* :func:`append_line` — for append-only logs, which need no
  read-modify-write at all and so cannot lose an update.
* :func:`file_lock` — an advisory cross-process lock for the
  read-modify-write that remains (whole-dict stores, prune, forget).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import contextlib
import errno
import logging
import os
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)

#: A lock held longer than this is treated as abandoned by a dead
#: process. Every holder below does a bounded amount of local file I/O.
STALE_LOCK_SECONDS = 30.0

#: How long to wait for a peer's lock before giving up. Callers degrade
#: (report failure) rather than write over a peer.
DEFAULT_LOCK_TIMEOUT = 5.0


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Replace ``path`` with ``text`` atomically.

    The temp file is created by :func:`tempfile.mkstemp` in the target's
    own directory, so its name is unique per call and the rename stays
    on one filesystem.

    Raises:
        OSError: If the write or the replace fails. Callers must report
            the failure rather than claim a successful write.
        ValueError: If the path is unsafe (null bytes, a system directory).
    """
    path = _validate_file_path(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
        tmp.replace(path)
    finally:
        # A successful replace consumes the temp file, so this only ever
        # fires on the failure paths — no leftover .tmp either way.
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def append_line(path: Path, line: str, *, encoding: str = "utf-8") -> None:
    """Append one line to ``path``, creating it if absent.

    Appending is the durable shape for a log: there is no read-modify-
    write, so concurrent writers cannot erase each other. The line is
    written with a single ``write`` under ``O_APPEND``.

    Args:
        path: Target file.
        line: The line to append; a trailing newline is added if absent.

    Raises:
        OSError: If the append fails.
        ValueError: If the path is unsafe (null bytes, a system directory).
    """
    path = _validate_file_path(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not line.endswith("\n"):
        line += "\n"
    with open(path, "a", encoding=encoding) as handle:
        handle.write(line)


@contextlib.contextmanager
def file_lock(path: Path, *, timeout: float = DEFAULT_LOCK_TIMEOUT) -> Iterator[bool]:
    """Hold an advisory cross-process lock for ``path``.

    Yields True when the lock was taken and False when the wait timed
    out — callers must treat False as "did not write", never as
    permission to proceed unsynchronized.

    Implemented with ``O_CREAT | O_EXCL`` (atomic on POSIX and Windows,
    unlike ``flock``/``msvcrt``, which differ per platform). A lock file
    older than :data:`STALE_LOCK_SECONDS` is treated as abandoned by a
    crashed holder and broken.

    Args:
        path: The file being protected (the lock lives alongside it).
        timeout: Seconds to wait for a peer to release.
    """
    lock_path = _validate_file_path(str(path)).with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    fd: int | None = None

    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            if _break_if_stale(lock_path):
                continue
            if time.monotonic() >= deadline:
                logger.warning("file_lock_timeout path=%s", lock_path)
                yield False
                return
            time.sleep(0.02)
        except OSError as exc:
            if exc.errno == errno.EACCES:
                logger.warning("file_lock_unavailable path=%s error=%s", lock_path, exc)
                yield False
                return
            raise

    try:
        with contextlib.suppress(OSError):
            os.write(fd, str(os.getpid()).encode("ascii"))
        yield True
    finally:
        with contextlib.suppress(OSError):
            os.close(fd)
        with contextlib.suppress(OSError):
            lock_path.unlink()


def _break_if_stale(lock_path: Path) -> bool:
    """Remove a lock left behind by a dead holder. True if it was broken."""
    try:
        age = time.time() - lock_path.stat().st_mtime
    except OSError:
        # Gone already — the holder released it between our attempts.
        return True
    if age < STALE_LOCK_SECONDS:
        return False
    logger.warning("file_lock_stale_broken path=%s age=%.1fs", lock_path, age)
    try:
        lock_path.unlink()
    except OSError:
        return False
    return True
