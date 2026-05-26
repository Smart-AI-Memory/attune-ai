"""File-backed bulletin storage.

Layout under ``<attune_home>/bulletin/``:

    active.jsonl                # current day's append-only log
    archive/YYYY-MM-DD.jsonl    # rotated daily snapshots

Concurrency model: each ``append`` opens the file with ``O_APPEND`` and
writes a single newline-terminated JSON record in one ``os.write``
call. POSIX guarantees writes ≤ ``PIPE_BUF`` (typically 4096B) to a
file opened in append mode are atomic. Our entries are well under
that limit (~250-400B). This avoids the cross-platform pitfalls of
``fcntl`` (POSIX-only) while keeping the bulletin advisory-safe.

Readers tolerate malformed lines — if a Windows race produced an
interleaved write, the bad line is skipped and the rest of the log
is still usable.

If the bulletin directory is unwritable, ``append`` logs at WARN and
returns silently. The bulletin is advisory; it must not gate the
underlying workflow.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .protocol import BulletinEntry

logger = logging.getLogger(__name__)

# Maximum line length (sanity bound — entries should be ~250-400B).
# Any line longer than this on read is treated as corrupted.
_MAX_LINE_BYTES = 16_384


class FileBulletinBackend:
    """File-backed implementation of :class:`BulletinBackend`."""

    def __init__(self, root: Path) -> None:
        """Create the backend rooted at ``<root>``.

        ``<root>`` is typically ``<attune_home>/bulletin``. The
        directory is created lazily on first ``append``.
        """
        self._root = Path(root)

    @property
    def active_path(self) -> Path:
        """Path to the current day's append-only log."""
        return self._root / "active.jsonl"

    @property
    def archive_dir(self) -> Path:
        """Directory holding rotated daily snapshots."""
        return self._root / "archive"

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def append(self, entry: BulletinEntry) -> None:
        """Append an entry to the active log.

        Failures (unwritable disk, permission denied) are logged at
        WARN and swallowed — the bulletin is advisory.
        """
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("bulletin: cannot create %s: %s", self._root, e)
            return

        # Rotate yesterday's log into archive before writing today's.
        try:
            self._maybe_rotate()
        except OSError as e:
            # Rotation failure is non-fatal — we'd rather keep writing
            # to a long active.jsonl than drop the entry.
            logger.warning("bulletin: rotate failed: %s", e)

        line = (json.dumps(entry.to_dict()) + "\n").encode("utf-8")
        if len(line) > _MAX_LINE_BYTES:
            logger.warning("bulletin: entry exceeds %d bytes; dropping", _MAX_LINE_BYTES)
            return

        try:
            # O_APPEND ensures atomic appends ≤ PIPE_BUF on POSIX.
            # On Windows the same call works but atomicity isn't
            # formally guaranteed; reads tolerate malformed lines.
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            fd = os.open(str(self.active_path), flags, 0o644)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
        except OSError as e:
            logger.warning("bulletin: append failed: %s", e)

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def read_active(self, *, stale_after_seconds: float = 90.0) -> list[BulletinEntry]:
        """Return current non-stale, non-terminal entries.

        Dedupe by ``run_id`` keeping the newest by ``last_heartbeat``.
        Drop entries whose latest heartbeat is older than
        ``stale_after_seconds``.
        """
        if not self.active_path.exists():
            return []

        latest_by_run: dict[str, BulletinEntry] = {}
        for entry in self._iter_entries(self.active_path):
            existing = latest_by_run.get(entry.run_id)
            if existing is None or entry.last_heartbeat > existing.last_heartbeat:
                latest_by_run[entry.run_id] = entry

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=stale_after_seconds)
        out: list[BulletinEntry] = []
        for entry in latest_by_run.values():
            if entry.is_terminal():
                continue
            heartbeat = _parse_iso(entry.last_heartbeat)
            if heartbeat is None or heartbeat < cutoff:
                continue
            out.append(entry)
        # Stable order: most recent heartbeat first.
        out.sort(key=lambda e: e.last_heartbeat, reverse=True)
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _iter_entries(self, path: Path):
        """Yield :class:`BulletinEntry` for every well-formed line."""
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for lineno, raw in enumerate(fh, start=1):
                    raw = raw.rstrip("\n")
                    if not raw:
                        continue
                    if len(raw) > _MAX_LINE_BYTES:
                        logger.debug(
                            "bulletin: %s:%d line too long, skipping",
                            path,
                            lineno,
                        )
                        continue
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.debug(
                            "bulletin: %s:%d malformed JSON, skipping",
                            path,
                            lineno,
                        )
                        continue
                    if not isinstance(data, dict):
                        continue
                    try:
                        yield BulletinEntry.from_dict(data)
                    except TypeError:
                        # Missing required field — skip.
                        logger.debug(
                            "bulletin: %s:%d missing fields, skipping",
                            path,
                            lineno,
                        )
                        continue
        except OSError as e:
            logger.warning("bulletin: cannot read %s: %s", path, e)

    def _maybe_rotate(self) -> None:
        """Move yesterday's active.jsonl into archive/ if needed.

        Triggered lazily on append. Checks the file's mtime against
        today's date — if mtime is on an earlier day, rotate.
        """
        if not self.active_path.exists():
            return
        mtime = datetime.fromtimestamp(self.active_path.stat().st_mtime, tz=timezone.utc)
        if mtime.date() >= date.today():
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"{mtime.date().isoformat()}.jsonl"
        target = self.archive_dir / archive_name
        # ``replace`` is cross-platform; ``rename`` fails on Windows
        # if target exists (per CLAUDE.md lesson).
        try:
            self.active_path.replace(target)
        except OSError as e:
            logger.warning("bulletin: archive rotate failed: %s", e)


def _parse_iso(s: str) -> datetime | None:
    """Parse an ISO 8601 string, return ``None`` on failure."""
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
