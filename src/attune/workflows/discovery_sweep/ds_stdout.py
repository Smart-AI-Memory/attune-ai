"""Daemon-parseable stdout side-channel for discovery-sweep.

When the ``ATTUNE_DS_EMIT=1`` environment variable is set, the engine
writes one ``ATTUNE_DS …`` line to stdout per per-source event plus a
final ``ATTUNE_DS final <json>`` line with the SweepResult. The ops
daemon (Phase 2 of ``docs/specs/discovery-sweep-ops-integration/``)
captures these lines from the subprocess it spawns and writes a
scope-keyed sidecar JSON the dashboard reads.

Why an env var and not non-TTY detection: legitimate users pipe
``attune workflow run discovery-sweep > out.md`` to capture markdown
output. Non-TTY would pollute that file with ATTUNE_DS lines. The
env var lets the daemon opt in explicitly without breaking the
pipe-to-file UX. See ``decisions.md`` entry #10.

Grammar (one event per line):

    ATTUNE_DS_VERSION 1
    ATTUNE_DS source_started   <name> ts=<iso>
    ATTUNE_DS source_finished  <name> ts=<iso> findings=<int>
    ATTUNE_DS source_failed    <name> ts=<iso> error=<ClassName>
    ATTUNE_DS final <json-on-one-line>

Whitespace-separated. Source names are workflow-defined identifiers
without spaces. The final-line JSON is the same blob ``--json`` /
``output_format="json"`` already produces.

This module is import-light — no engine deps — so the ops daemon's
parser (Phase 2) can ``from attune.workflows.discovery_sweep.ds_stdout
import parse_line`` without pulling in the whole workflow surface.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

EMIT_ENV = "ATTUNE_DS_EMIT"
VERSION = 1

# Regex per line kind. Anchored at start; trailing content is the value.
_RE_VERSION = re.compile(r"^ATTUNE_DS_VERSION (\d+)$")
_RE_STARTED = re.compile(r"^ATTUNE_DS source_started (\S+) ts=(\S+)$")
_RE_FINISHED = re.compile(r"^ATTUNE_DS source_finished (\S+) ts=(\S+) findings=(\d+)$")
_RE_FAILED = re.compile(r"^ATTUNE_DS source_failed (\S+) ts=(\S+) error=(\S+)$")
_RE_FINAL = re.compile(r"^ATTUNE_DS final (.+)$")


def is_emission_enabled() -> bool:
    """True when ``ATTUNE_DS_EMIT`` is set to any non-empty value."""
    return bool(os.environ.get(EMIT_ENV))


def _write(line: str) -> None:
    """Write a single line to stdout and flush so a subprocess parent
    reads it in real time."""
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def emit_version_line() -> None:
    """Write the schema-version line. Parsers refuse unknown versions."""
    _write(f"ATTUNE_DS_VERSION {VERSION}")


def emit_event_line(event: dict[str, Any]) -> None:
    """Write one ATTUNE_DS line for an engine-emitted event dict.

    Unknown event kinds are silently dropped — the parser will refuse
    them on the daemon side, so emitting a malformed line is worse
    than skipping. Existing kinds: source_started, source_finished,
    source_failed. The ``sweep_id`` field on each event is intentionally
    NOT serialized — daemon-side callers correlate via ``run_id``
    (which they own) and CLI callers leave it None; including it in
    the wire format would just add noise.
    """
    kind = event.get("event")
    source = event.get("source", "")
    ts = event.get("ts", "")
    if kind == "source_started":
        _write(f"ATTUNE_DS source_started {source} ts={ts}")
    elif kind == "source_finished":
        n = int(event.get("findings_count", 0))
        _write(f"ATTUNE_DS source_finished {source} ts={ts} findings={n}")
    elif kind == "source_failed":
        err = event.get("error", "UnknownError")
        _write(f"ATTUNE_DS source_failed {source} ts={ts} error={err}")
    # else: unknown kind — drop silently.


def emit_final_line(result_json: str) -> None:
    """Write the final ATTUNE_DS line carrying the full SweepResult JSON.

    The JSON blob must be single-line; callers pass the output of
    ``json.dumps(...)`` (no ``indent=`` arg). Multiline JSON would
    break the one-line-per-event grammar.
    """
    # Defensive: strip embedded newlines if a caller passes pretty-
    # printed JSON. Daemon parser expects one line per record.
    single_line = result_json.replace("\n", "").replace("\r", "")
    _write(f"ATTUNE_DS final {single_line}")


def parse_line(line: str) -> dict[str, Any] | None:
    """Parse one ATTUNE_DS line back into a dict. None on no match.

    Returns:
        - ``{"event": "version", "version": int}`` for the version line.
        - ``{"event": "source_started", "source": str, "ts": str}``.
        - ``{"event": "source_finished", "source": str, "ts": str,
          "findings_count": int}``.
        - ``{"event": "source_failed", "source": str, "ts": str,
          "error": str}``.
        - ``{"event": "final", "json": str}`` (caller does
          ``json.loads(d["json"])``).
        - ``None`` for any non-``ATTUNE_DS`` line or malformed entry.

    Round-trips with the ``emit_*_line()`` functions in this module.
    """
    stripped = line.rstrip("\r\n")
    if not stripped.startswith("ATTUNE_DS"):
        return None
    m = _RE_VERSION.match(stripped)
    if m:
        return {"event": "version", "version": int(m.group(1))}
    m = _RE_STARTED.match(stripped)
    if m:
        return {
            "event": "source_started",
            "source": m.group(1),
            "ts": m.group(2),
        }
    m = _RE_FINISHED.match(stripped)
    if m:
        return {
            "event": "source_finished",
            "source": m.group(1),
            "ts": m.group(2),
            "findings_count": int(m.group(3)),
        }
    m = _RE_FAILED.match(stripped)
    if m:
        return {
            "event": "source_failed",
            "source": m.group(1),
            "ts": m.group(2),
            "error": m.group(3),
        }
    m = _RE_FINAL.match(stripped)
    if m:
        return {"event": "final", "json": m.group(1)}
    return None
