"""Daemon-parseable stdout side-channel for run metadata.

When the ``ATTUNE_RUN_META_EMIT=1`` environment variable is set, the
CLI's ``_print_workflow_result`` emits one ``ATTUNE_RUN_META …`` line
per non-None metadata field from the ``WorkflowResult`` that the ops
runner cares about (currently the ``sdk_stderr`` / ``sdk_error_kind``
fields populated by ``BaseWorkflow._error_result()`` when an SDK
workflow fails). The ops runner (``RunnerService._execute``) sets the
env var when spawning the workflow subprocess, parses these lines
from the captured stdout, stashes the values on the in-memory
``Run`` object, and filters the marker lines out of ``run.lines`` so
the user-facing log stays clean.

Why an env var and not non-TTY detection: legitimate users pipe
``attune workflow run code-review > out.md`` to capture markdown
output. Non-TTY would pollute that file with ATTUNE_RUN_META lines.
The env var lets the daemon opt in explicitly without breaking the
pipe-to-file UX. See the existing
``ATTUNE_DS_EMIT`` precedent in
``attune.workflows.discovery_sweep.ds_stdout`` and the
``feedback_standalone_preview_pages``-adjacent CLAUDE.md lesson on
env-gated structured stdout (2026-05-13).

Grammar (one event per line):

    ATTUNE_RUN_META_VERSION 1
    ATTUNE_RUN_META sdk_error_kind=<kind>
    ATTUNE_RUN_META sdk_stderr_b64=<base64>
    ATTUNE_RUN_META report_b64=<base64-json>

The ``sdk_stderr`` field is base64-encoded because raw stderr
typically spans multiple lines and includes characters (quotes,
backslashes, control chars) that would break a single-line plaintext
grammar. ``sdk_error_kind`` is a short single-word literal from the
classifier (one of ``api_quota`` / ``auth`` / ``rate_limit`` /
``not_found`` / ``schema_rejected`` / ``unknown``) so plain text is
fine — see ``SdkErrorKind`` in ``agent_sdk_adapter.py``.

This module is import-light — only stdlib — so the ops runner's
parser can import ``parse_line`` without pulling in any of the
workflow runtime.

Part of the ``docs/specs/sdk-error-message-fidelity/`` Phase 3b flow.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import base64
import io
import os
import re
import select
import sys
import time
from typing import Any

EMIT_ENV = "ATTUNE_RUN_META_EMIT"
VERSION = 1

#: Max seconds to wait per select() round for a non-blocking stdout to
#: drain. The loop re-selects until the write completes or the
#: deadline below expires.
_WRITE_WAIT_S = 1.0

#: Total elapsed ceiling for one _write() call. A reader that dies
#: without closing its pipe end would otherwise stall the retry loop
#: forever. Generous by design: the daemon drains continuously, so a
#: healthy pipe never gets near this.
_WRITE_DEADLINE_S = 30.0

# Allowed key names. Restricting to a known set keeps the grammar tight;
# extending this requires updating both ``emit_field_line`` and
# ``parse_line`` (and the consumer in ``RunnerService._execute``).
# ``report_b64`` carries the serialized ``WorkflowReport`` dict
# (base64-encoded JSON) so the dashboard's run view can render a
# structured report panel — workflow-result-formatting T6.
_ALLOWED_KEYS = frozenset(("sdk_error_kind", "sdk_stderr_b64", "report_b64"))

# Regex per line kind. Anchored at start; trailing content is the value.
_RE_VERSION = re.compile(r"^ATTUNE_RUN_META_VERSION (\d+)$")
# Value pattern is permissive (\S* for value text — base64 alphabet
# plus padding, or single-word literal). Key admits digits because
# field names like ``sdk_stderr_b64`` carry them. The parser does a
# key-name allowlist check (_ALLOWED_KEYS) after the regex match.
_RE_FIELD = re.compile(r"^ATTUNE_RUN_META ([a-z0-9_]+)=(\S*)$")


def is_emission_enabled() -> bool:
    """True when ``ATTUNE_RUN_META_EMIT`` is set to any non-empty value."""
    return bool(os.environ.get(EMIT_ENV))


def _write(line: str) -> None:
    """Write a single line to stdout and flush so a subprocess parent
    reads it in real time.

    The daemon runs the CLI with its stdout on a pipe that can be in
    non-blocking mode, and ``report_b64`` lines routinely exceed the
    64 KiB pipe buffer — a plain ``sys.stdout.write`` then raises
    ``BlockingIOError`` mid-line and crashes an otherwise-succeeded
    run. Write at the fd level with a ``select()``-wait retry so
    partial writes complete instead.

    The retry is bounded by ``_WRITE_DEADLINE_S``: a reader that dies
    without closing its end would otherwise park this loop forever —
    trading the original crash for a silent hang. On deadline the
    raised ``TimeoutError`` (an ``OSError``) reaches the caller's
    emission guard, which warns and moves on.
    """
    try:
        fd = sys.stdout.fileno()
    except (ValueError, OSError, io.UnsupportedOperation):
        # Captured/test stdout without a real fd: plain write is safe
        # there (no non-blocking pipe involved).
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        return

    deadline = time.monotonic() + _WRITE_DEADLINE_S

    def _wait_writable() -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"run-meta write stalled >{_WRITE_DEADLINE_S:.0f}s on a non-draining pipe"
            )
        select.select([], [fd], [], _WRITE_WAIT_S)

    # Drain any buffered text output first so line ordering holds.
    while True:
        try:
            sys.stdout.flush()
            break
        except BlockingIOError:
            _wait_writable()

    data = (line + "\n").encode("utf-8")
    view = memoryview(data)
    offset = 0
    while offset < len(data):
        try:
            offset += os.write(fd, view[offset:])
        except BlockingIOError:
            _wait_writable()


def emit_version_line() -> None:
    """Write the schema-version line. Parsers refuse unknown versions."""
    _write(f"ATTUNE_RUN_META_VERSION {VERSION}")


def emit_field_line(key: str, value: str) -> None:
    """Write one ``ATTUNE_RUN_META`` line for a named field.

    For ``sdk_stderr`` (multi-line, may contain shell-special chars),
    callers should pre-encode with :func:`encode_stderr` and pass the
    resulting base64 string under the ``sdk_stderr_b64`` key. For
    ``sdk_error_kind`` (single-word literal), pass the raw kind value.

    Unknown keys are silently dropped — the parser will refuse them
    on the daemon side, so emitting a malformed line is worse than
    skipping. Empty values are also dropped (no point emitting a
    field the consumer can't act on).
    """
    if key not in _ALLOWED_KEYS or not value:
        return
    # Newlines in the value would break the one-line-per-event
    # grammar. The base64-encoded path is safe by construction; the
    # plain-text path (sdk_error_kind) is a single-word literal so
    # newlines aren't expected — but we defensively reject them
    # rather than silently corrupting the wire format.
    if "\n" in value or "\r" in value:
        return
    _write(f"ATTUNE_RUN_META {key}={value}")


def encode_stderr(stderr_text: str) -> str:
    """Base64-encode a multi-line stderr string for wire-safe transit.

    Uses standard base64 (not url-safe) — the output goes through a
    pipe, not a URL. Empty input encodes to empty string; the caller
    is expected to skip emission for empty stderr.
    """
    if not stderr_text:
        return ""
    return base64.b64encode(stderr_text.encode("utf-8")).decode("ascii")


def decode_stderr(b64_text: str) -> str:
    """Inverse of :func:`encode_stderr`. Returns empty string on
    malformed input (the consumer logs a warning and continues)."""
    if not b64_text:
        return ""
    try:
        return base64.b64decode(b64_text, validate=True).decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError):
        return ""


def encode_report(report_dict: dict[str, Any]) -> str:
    """Base64-encode a serialized ``WorkflowReport`` dict for wire transit.

    JSON is compact-encoded (no whitespace) before base64 so the single
    marker line stays as short as possible. Returns empty string when
    the dict can't be JSON-encoded — the caller skips emission rather
    than writing a malformed marker.
    """
    import json

    try:
        raw = json.dumps(report_dict, separators=(",", ":"))
    except (TypeError, ValueError):
        return ""
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def decode_report(b64_text: str) -> dict[str, Any] | None:
    """Inverse of :func:`encode_report`. ``None`` on malformed input.

    The consumer (``RunnerService.handle_stdout_line``) treats ``None``
    as "drop the marker, keep any previously-stashed report".
    """
    import json

    if not b64_text:
        return None
    try:
        raw = base64.b64decode(b64_text, validate=True).decode("utf-8")
        parsed = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_line(line: str) -> dict[str, Any] | None:
    """Parse one ATTUNE_RUN_META line back into a dict. None on no match.

    Returns:
        - ``{"event": "version", "version": int}`` for the version line.
        - ``{"event": "field", "key": str, "value": str}`` for a
          field line. The ``value`` is the raw on-wire string — the
          consumer applies :func:`decode_stderr` for the
          ``sdk_stderr_b64`` key, or uses the value as-is for plain
          fields.
        - ``None`` for any non-``ATTUNE_RUN_META`` line, malformed
          entry, or unknown key name.

    Round-trips with the ``emit_*_line()`` functions in this module.
    """
    stripped = line.rstrip("\r\n")
    if not stripped.startswith("ATTUNE_RUN_META"):
        return None
    m = _RE_VERSION.match(stripped)
    if m:
        return {"event": "version", "version": int(m.group(1))}
    m = _RE_FIELD.match(stripped)
    if m:
        key = m.group(1)
        if key not in _ALLOWED_KEYS:
            return None
        return {"event": "field", "key": key, "value": m.group(2)}
    return None
