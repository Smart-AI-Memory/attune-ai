#!/usr/bin/env python3
"""SessionStart spec-orientation hook.

Fires on every SessionStart event. Branches on the ``source``
field (verified 2026-05-09 to be one of ``startup``, ``resume``,
``clear``, or ``compact``):

- ``compact`` → emit the most-recent in-flight spec's tasks.md
  (or design / requirements as a fallback) so the model has the
  spec body in fresh post-compact context. Replaces the original
  PreCompact-injection design (V2 found PreCompact has no
  content-injection mechanism).
- everything else → emit a short orientation paragraph naming up
  to 3 in-flight specs.

Output goes to stdout; Claude Code splices it into the model's
initial context. The hook is wrapped in try/except so a crash
never breaks the user's session.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

# Force utf-8 on stdout and stderr. On Windows the default cp1252
# encoding can't emit emoji/em-dash and would crash this hook (caught
# by the outer try/except → silent breakage). errors='replace'
# substitutes '?' for any stray non-encodable byte.
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding and _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Hooks are invoked as standalone scripts; ensure sibling helpers
# resolve.
_HOOKS_DIR = str(Path(__file__).resolve().parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

from _state import (  # noqa: E402 — sys.path bootstrap above
    SpecInfo,
    discover_specs,
    prune_stale_sentinels,
    read_drift_cache,
    workspace_roots,
)


def _audit_annotations_enabled() -> bool:
    """Kill switch (spec-status-integrity, design §3).

    ``ATTUNE_SPEC_AUDIT=off`` suppresses both the ``⚠ drifted``
    drift-cache annotation and the existing suspected-stale hint.
    Anything else (including unset) leaves them on.
    """
    return os.environ.get("ATTUNE_SPEC_AUDIT", "").strip().lower() != "off"


# Char budget for the post-compact spec body. Generous so the
# spec survives compaction with full content; the model sees this
# as fresh context immediately after the compact summary.
_POST_COMPACT_CHAR_BUDGET = 8_000

# Max specs named in the orientation paragraph.
_ORIENTATION_MAX_SPECS = 3


def _format_phase(spec: SpecInfo, annotate: bool = True) -> str:
    """Short ``(phase status)`` blurb for the orientation list.

    ``annotate=False`` (the ``ATTUNE_SPEC_AUDIT=off`` kill switch)
    suppresses the suspected-stale hint; the status_conflict hint is
    self-truthing, not an audit annotation, and always renders.

    Renders the reconciled ``effective_status`` (not the raw header
    ``status``) so a stale "draft" header above a closed checklist
    doesn't show up as in-flight draft.

    When ``status_conflict`` is True (header drifted from the
    completion state), append a one-line hint so the source drift
    surfaces and can be fixed.

    When ``staleness`` is ``"suspected-stale"`` (every declared
    deliverable resolves on disk but the status is still non-terminal),
    append a parallel hint so a session doesn't rebuild shipped work.
    The two hints don't collide: an in-body terminal signal would have
    set ``status_conflict`` and excluded the spec from the in-flight
    list, so a still-listed spec that is ``suspected-stale`` has no
    terminal signal — but ``status_conflict`` is checked first anyway.
    """
    phase_label = {
        "requirements": "requirements",
        "design": "design",
        "tasks": "tasks",
    }.get(spec.phase, spec.phase)
    effective = spec.effective_status or spec.status or "no status"
    base = f"{phase_label} {effective}"
    if spec.status_conflict:
        source_label = {
            "checklist": "tasks closed per checklist",
            "terminal-line": "marked terminal in body",
        }.get(spec.status_source, spec.status_source)
        raw = spec.status or "no header"
        return f'{base} — {source_label}; header says "{raw}", worth fixing'
    if annotate and spec.staleness == "suspected-stale":
        raw = spec.status or "no status"
        return f'{base} — ⚠ deliverables present, status still "{raw}"; verify before building'
    return base


def _drift_suffix(spec: SpecInfo, drift_cache: dict[str, dict]) -> str:
    """`` ⚠ drifted: attune-author #95 merged`` when the drift cache
    marks this spec drifted; empty otherwise (design §3). The cache is
    read from disk only — the hook makes no network calls."""
    entry = drift_cache.get(f"{spec.layer}/{spec.slug}")
    if not isinstance(entry, dict) or entry.get("verdict") != "drifted":
        return ""
    prs = [p for p in entry.get("prs") or [] if isinstance(p, str)]
    detail = f": {', '.join(prs)} merged" if prs else ""
    return f" ⚠ drifted{detail}"


def format_orientation(
    specs: list[SpecInfo],
    drift_cache: dict[str, dict] | None = None,
    annotate: bool = True,
) -> str:
    """Short markdown list of in-flight specs for non-compact starts."""
    if not specs:
        return ""
    drift = drift_cache or {}
    lines = ["attune workspace — in-flight specs:"]
    for spec in specs[:_ORIENTATION_MAX_SPECS]:
        layer_prefix = "" if spec.layer == "workspace" else f"{spec.layer}/"
        line = f"- {layer_prefix}specs/{spec.slug}/  ({_format_phase(spec, annotate=annotate)})"
        if annotate:
            line += _drift_suffix(spec, drift)
        lines.append(line)
    leftover = len(specs) - _ORIENTATION_MAX_SPECS
    if leftover > 0:
        lines.append(f"- (+{leftover} more)")
    return "\n".join(lines)


def render_spec_pin(spec: SpecInfo, char_budget: int = _POST_COMPACT_CHAR_BUDGET) -> str:
    """Render a spec body for post-compact context restoration.

    Picks the highest-priority phase file present in the spec dir
    (tasks > design > requirements) and emits its body up to the
    char budget. Adds a header naming the spec so the model can
    map the body back to its location.
    """
    for fname in ("tasks.md", "design.md", "requirements.md"):
        fpath = spec.path / fname
        if not fpath.is_file():
            continue
        try:
            body = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        layer_prefix = "" if spec.layer == "workspace" else f"{spec.layer}/"
        spec_path = f"{layer_prefix}specs/{spec.slug}/{fname}"
        header = (
            f"# Active spec restored after compact: `{spec_path}`\n"
            f"# Phase: {spec.phase} — Status: {spec.status or 'unknown'}\n\n"
        )
        truncated = body[:char_budget]
        if len(body) > char_budget:
            truncated += "\n\n…(spec body truncated for context budget)"
        return header + truncated
    return ""


def main() -> int:
    """Entry point — branches on ``source``, never raises."""
    try:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        source = (payload.get("source") or "startup").lower()
        cwd = Path(payload.get("cwd") or Path.cwd())

        # Opportunistic TTL prune — keeps sentinel dir tidy without
        # a separate cron.
        try:
            prune_stale_sentinels()
        except Exception:  # noqa: BLE001 — never propagate
            pass

        roots = workspace_roots(cwd=cwd)
        specs = discover_specs(roots)
        if not specs:
            return 0

        if source == "compact":
            body = render_spec_pin(specs[0])
            if body:
                print(body)
        else:
            annotate = _audit_annotations_enabled()
            # Offline by design: the drift signal comes from the cache
            # spec_audit --pr-links wrote, never from a network call.
            drift_cache = read_drift_cache(roots) if annotate else {}
            orient = format_orientation(specs, drift_cache=drift_cache, annotate=annotate)
            if orient:
                print(orient)
        return 0
    except Exception:  # noqa: BLE001 — hook must never crash a session
        # Log the full traceback to stderr so plugin authors can
        # diagnose, but exit cleanly so Claude Code keeps going.
        traceback.print_exc(file=sys.stderr)
        return 0


if __name__ == "__main__":
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    raise SystemExit(main())
