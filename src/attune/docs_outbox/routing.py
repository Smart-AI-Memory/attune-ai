# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""Mechanical routing by artifact type (R2) — no per-case judgment.

Lessons, reports, drafts, and plans ALWAYS go to the outbox;
``decisions.md`` rulings, spec status flips, and starter-adjacent
state ALWAYS merge now via the existing flow, because parallel
sessions act on them the same day.
"""

from __future__ import annotations

#: Outbox-routed kinds -> default target (repo-relative), or None
#: when the writer must name a target explicitly.
OUTBOX_TARGETS: dict[str, str | None] = {
    "lesson": ".claude/lessons.md",
    "report": None,
    "draft": None,
    "plan": None,
}

#: Kinds that must ship merge-now — the outbox refuses them.
MERGE_NOW_KINDS = frozenset({"decision", "spec-status", "starter"})


def route(kind: str) -> str:
    """Return ``"outbox"`` or ``"merge-now"`` for a known kind.

    Raises:
        ValueError: for a kind outside the ratified routing table.
    """
    if kind in OUTBOX_TARGETS:
        return "outbox"
    if kind in MERGE_NOW_KINDS:
        return "merge-now"
    known = sorted(OUTBOX_TARGETS) + sorted(MERGE_NOW_KINDS)
    raise ValueError(f"unknown artifact kind {kind!r}; known kinds: {', '.join(known)}")
