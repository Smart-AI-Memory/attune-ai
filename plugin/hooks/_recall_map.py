"""Curated decision-point -> rule map for just-in-time recall.

The single reviewable source for which durable rules surface at which
tool-call decision points (docs/specs/just-in-time-recall/, decision
D3). Keyed by tool name; valued by short ``{rule_id, text}`` entries.

Authoring rules:

- ``text`` is a distilled ONE-LINER nudge (decision D4) — the full
  lesson stays in ``.claude/CLAUDE.md`` / the ``feedback_*`` memories
  as the source of truth.
- Only instrument genuine, observed slip-points (R3: low noise).
  Growing this map is deliberate, diff-reviewed work — not a dumping
  ground for every lesson.
- ``rule_id`` is stable and filesystem-safe (it keys the per-session
  surface-once sentinel).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

RECALL_MAP: dict[str, list[dict[str, str]]] = {
    # Proof case (R6): the question-shape rule was stored in two places
    # on 2026-06-03 and still slipped three times mid-session.
    "AskUserQuestion": [
        {
            "rule_id": "question-shape",
            "text": (
                "Question-shape rule: ask ONE question per turn; lead with "
                "your recommendation as the FIRST option, its label ending "
                "in '(Recommended)'; options concise and directly "
                "selectable — no and/or bundles, no buried prose."
            ),
        },
    ],
}
