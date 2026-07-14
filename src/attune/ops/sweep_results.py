"""Scope-keyed persistence for discovery-sweep results.

Phase 2A of ``docs/specs/discovery-sweep-ops-integration/``.

Stores the JSON output of a discovery-sweep run keyed by a hash of
its canonicalized scope path, so the dashboard's workflow row can
read the latest sweep result for a given path without re-running.

Wire diagram (Option A from the Phase 0 audit):

    DiscoverySweepWorkflow.execute()  (subprocess)
        → emits ATTUNE_DS_VERSION 1
        → emits ATTUNE_DS <event> ... lines
        → emits ATTUNE_DS final <json>
                                  │ stdout (captured by ops daemon)
                                  ▼
    RunnerService._execute()  (ops daemon)
        → captures stdout into Run.lines
        → on run complete + workflow == "discovery-sweep" + exit 0,
          calls persist_from_lines() in THIS module (Phase 2B —
          deferred until the conflict-prone runner.py unblocks)

    Dashboard
        → reads result via read_result(<scope-hash>)  (Phase 2B)

Phase 2A scope is **storage primitives only**: no daemon wiring, no
HTTP route, no automatic persistence. Anyone (a script, a future PR,
the daemon when 2B lands) can compose these primitives:

    >>> from attune.ops import sweep_results
    >>> result = sweep_results.parse_lines(captured_stdout_lines)
    >>> if result is not None:
    ...     sweep_results.persist_result(scope_path, result, config)
    >>> sweep_results.read_result(sweep_results.scope_hash(path), config)

All filesystem writes are atomic (tempfile + os.replace in the same
dir) so a partial write never corrupts the read side.

Feature flag: ``ATTUNE_OPS_SWEEP_RESULTS=1`` env var. ``is_persistence_enabled()``
returns False by default — Phase 2B wiring checks this before
auto-persisting, so the surface stays opt-in until the user enables it.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from attune.ops.config import Config
from attune.workflows.discovery_sweep import ds_stdout

logger = logging.getLogger(__name__)

ENABLE_ENV = "ATTUNE_OPS_SWEEP_RESULTS"
RESULTS_SUBDIR = ("ops", "sweep-results")
HASH_LENGTH = 16


def is_persistence_enabled() -> bool:
    """True when ``ATTUNE_OPS_SWEEP_RESULTS`` is set to a non-empty value.

    Phase 2B's daemon-side auto-persist hook gates on this. Phase 2A's
    pure utility functions ignore it — a caller that imports this
    module is opting in explicitly, so the gate is one-level-up.
    """
    return bool(os.environ.get(ENABLE_ENV))


def results_dir(config: Config) -> Path:
    """Return ``<attune_home>/ops/sweep-results/`` (created if missing).

    The directory is created with ``parents=True, exist_ok=True`` so
    callers don't have to. Subdirectory layout is fixed by
    ``RESULTS_SUBDIR``; users who want a different path override
    ``ATTUNE_HOME`` via :func:`attune.ops.config.attune_home`.
    """
    out = config.attune_home.joinpath(*RESULTS_SUBDIR)
    out.mkdir(parents=True, exist_ok=True)
    return out


def scope_hash(scope_path: str) -> str:
    """Hash a scope path to a fixed-length hex identifier.

    Canonicalizes via :meth:`Path.resolve` so ``./src``, ``src/``, and
    the absolute path all hash to the same identifier. Returns the
    first ``HASH_LENGTH`` (16) hex chars of sha256 — collision
    probability across realistic scope sets is negligible.

    Empty / whitespace-only paths are not canonicalized (resolve()
    would return cwd, which is misleading); they hash directly so
    that the empty case is at least deterministic.
    """
    if not scope_path or not scope_path.strip():
        canonical = scope_path
    else:
        try:
            canonical = str(Path(scope_path).resolve())
        except (OSError, RuntimeError):
            # Fallback to the raw string; persistence is best-effort.
            canonical = scope_path
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest[:HASH_LENGTH]


def parse_lines(lines: list[str]) -> dict[str, Any] | None:
    """Parse a captured stdout buffer into the final SweepResult JSON.

    Walks the lines looking for ATTUNE_DS records via
    :func:`ds_stdout.parse_line`. Returns the dict from the
    ``ATTUNE_DS final <json>`` line if found; ``None`` otherwise.

    Refuses unknown ``ATTUNE_DS_VERSION`` values: if a version line
    is present and doesn't match :data:`ds_stdout.VERSION`, returns
    ``None`` with a logged warning so the daemon doesn't persist
    data it might be parsing wrong. A missing version line is
    treated as legacy / non-emitting output (returns ``None``
    without warning).

    Non-ATTUNE_DS lines are ignored — captured stdout may legitimately
    interleave markdown rendering with the structured stream.
    """
    saw_version = False
    final_json: str | None = None

    for line in lines:
        parsed = ds_stdout.parse_line(line)
        if parsed is None:
            continue
        if parsed["event"] == "version":
            saw_version = True
            if parsed["version"] != ds_stdout.VERSION:
                logger.warning(
                    "discovery-sweep ATTUNE_DS version mismatch: got %s, "
                    "expected %s — refusing to parse",
                    parsed["version"],
                    ds_stdout.VERSION,
                )
                return None
        elif parsed["event"] == "final":
            final_json = parsed["json"]

    if not saw_version or final_json is None:
        return None

    try:
        decoded: dict[str, Any] = json.loads(final_json)
    except json.JSONDecodeError as exc:
        logger.warning(
            "discovery-sweep ATTUNE_DS final line is not valid JSON: %s",
            exc,
        )
        return None
    return decoded


def persist_result(scope_path: str, sweep_result: dict[str, Any], config: Config) -> Path:
    """Atomically write ``sweep_result`` to ``<results_dir>/<hash>.json``.

    Uses ``tempfile.NamedTemporaryFile`` + ``os.replace`` in the same
    directory so a partial write never produces a half-readable file
    on the read side. Overwrites the existing file for the same scope
    (latest-only semantics; history is post-v1 per spec decisions.md).

    Returns the path written.
    """
    digest = scope_hash(scope_path)
    out_dir = results_dir(config)
    target = out_dir / f"{digest}.json"

    # Atomic-replace: write to a temp file in the same dir, then rename.
    # Same-dir-tempfile is required so os.replace is atomic across
    # mount-point boundaries (the temp dir might be on tmpfs).
    fd, tmp_name = tempfile.mkstemp(prefix=f".{digest}.", suffix=".json.tmp", dir=str(out_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(sweep_result, f, indent=2)
        os.replace(tmp_name, target)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: cleanup-and-reraise, not a mask — the broad
        # catch exists only so the temp file never leaks, and the
        # bare `raise` preserves the original exception unchanged.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def read_result(digest: str, config: Config) -> dict[str, Any] | None:
    """Read a previously-persisted result by its scope-hash digest.

    Returns the JSON dict or ``None`` if no result has been persisted
    for that hash. Malformed JSON on disk returns ``None`` with a
    logged warning — the dashboard's read API should surface "no
    data yet" rather than crashing on a partially-corrupted file
    (atomic writes make this rare but not impossible if a user
    edits a sidecar manually).
    """
    out_dir = results_dir(config)
    target = out_dir / f"{digest}.json"
    if not target.exists():
        return None
    try:
        with target.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("discovery-sweep sidecar at %s is unreadable: %s", target, exc)
        return None


def persist_from_lines(scope_path: str, lines: list[str], config: Config) -> Path | None:
    """Parse captured stdout lines and persist the result for ``scope_path``.

    Composition of :func:`parse_lines` + :func:`persist_result`. Returns
    the written path on success, ``None`` if the lines did not contain
    a valid ATTUNE_DS payload (no version line, malformed JSON, version
    mismatch).

    This is the function the Phase 2B daemon-side hook calls once a
    discovery-sweep run completes successfully.
    """
    result = parse_lines(lines)
    if result is None:
        return None
    return persist_result(scope_path, result, config)
