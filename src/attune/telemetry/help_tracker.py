"""Help-query telemetry.

Privacy-first, local-only tracking of `/coach` and `help_lookup` MCP
queries to measure actual use of the help system. Data is stored in
``~/.attune/telemetry/help_queries.jsonl``.

Set ``ATTUNE_HELP_TELEMETRY=0`` in the environment to disable.

Event shape (JSONL, one event per line)::

    {
        "v": "1.0",
        "ts": "2026-04-19T18:30:00.123456+00:00",
        "source": "help_lookup",
        "mode": "progressive",
        "topic": "security-audit",
        "success": true,
        "found": true,
        "depth_level": 0,
        "duration_ms": 12.4
    }

Unmatched queries — lookups that completed but resolved no help
topic — are additionally appended to
``~/.attune/telemetry/help_unmatched.jsonl``. This is channel 1 of
the FAQ Generator (real user questions with no matching topic; see
docs/specs/archive/help-docs-single-source/follow-ups.md FG1)::

    {
        "v": "1.0",
        "ts": "2026-04-19T18:30:00.123456+00:00",
        "source": "help_lookup",
        "mode": "progressive",
        "query": "how do I rotate api keys"
    }

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOG_VERSION = "1.0"
_DEFAULT_DIR = Path.home() / ".attune" / "telemetry"
_DEFAULT_FILE = "help_queries.jsonl"
_UNMATCHED_FILE = "help_unmatched.jsonl"


def _enabled() -> bool:
    return os.environ.get("ATTUNE_HELP_TELEMETRY", "1") != "0"


class HelpTracker:
    """Append-only JSONL tracker for help-system queries.

    Thread-safe via a single module-level lock. No buffering — help
    queries are infrequent (<100/day typical), so durability matters
    more than throughput.
    """

    def __init__(
        self,
        log_dir: Path | None = None,
        filename: str = _DEFAULT_FILE,
        unmatched_filename: str = _UNMATCHED_FILE,
    ):
        """Construct a tracker.

        Args:
            log_dir: Directory for telemetry files. Defaults to
                ``~/.attune/telemetry/``.
            filename: JSONL filename within ``log_dir``.
            unmatched_filename: JSONL filename for the unmatched-query
                (FAQ channel-1) log within ``log_dir``.
        """
        self._dir = log_dir or _DEFAULT_DIR
        self._path = self._dir / filename
        self._unmatched_path = self._dir / unmatched_filename
        self._lock = threading.Lock()

    @property
    def path(self) -> Path:
        """Path to the JSONL log file."""
        return self._path

    @property
    def unmatched_path(self) -> Path:
        """Path to the unmatched-query JSONL log file."""
        return self._unmatched_path

    def log(
        self,
        *,
        source: str,
        mode: str,
        topic: str,
        success: bool,
        found: bool,
        duration_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a single event to the log.

        No-ops silently if ``ATTUNE_HELP_TELEMETRY=0`` or if the write
        fails — telemetry must never break the caller.

        Args:
            source: Call site, e.g., ``"help_lookup"``, ``"rag"``.
            mode: Sub-mode within the source (e.g., ``"progressive"``).
            topic: Query string or topic name the user asked about.
            success: Whether the call returned without error.
            found: Whether the query yielded a non-empty result.
            duration_ms: Optional wall-clock duration of the lookup.
            metadata: Optional extra fields (e.g., depth_level, tags).
        """
        if not _enabled():
            return
        event = {
            "v": _LOG_VERSION,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "mode": mode,
            "topic": topic,
            "success": success,
            "found": found,
        }
        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 2)
        if metadata:
            event["metadata"] = metadata
        self._append(self._path, event)

    def log_unmatched(
        self,
        *,
        query: str,
        mode: str,
        source: str = "help_lookup",
    ) -> None:
        """Append an unmatched query to the FAQ channel-1 log.

        Called when a help lookup completed but resolved no topic —
        the raw query is what the future FAQ Generator ranks by
        frequency. No-ops silently if ``ATTUNE_HELP_TELEMETRY=0`` or
        if the write fails.

        Args:
            query: The topic/query string that found no help topic.
            mode: Lookup sub-mode (e.g., ``"progressive"``).
            source: Call site, e.g., ``"help_lookup"``.
        """
        if not _enabled():
            return
        event = {
            "v": _LOG_VERSION,
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "mode": mode,
            "query": query,
        }
        self._append(self._unmatched_path, event)

    def _append(self, path: Path, event: dict[str, Any]) -> None:
        """Append one event to a JSONL file; never raises."""
        try:
            with self._lock:
                self._dir.mkdir(parents=True, exist_ok=True)
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as err:
            logger.debug("help telemetry write failed: %s", err)


_DEFAULT_TRACKER: HelpTracker | None = None
_DEFAULT_LOCK = threading.Lock()


def get_tracker() -> HelpTracker:
    """Return a process-wide default HelpTracker."""
    global _DEFAULT_TRACKER
    if _DEFAULT_TRACKER is None:
        with _DEFAULT_LOCK:
            if _DEFAULT_TRACKER is None:
                _DEFAULT_TRACKER = HelpTracker()
    return _DEFAULT_TRACKER
