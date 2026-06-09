"""``attune patterns`` — the human-in-the-loop pattern review queue CLI.

``attune patterns review`` lists staged patterns; ``promote <id>`` moves
one into the active (backend-persisted) :class:`PersistentPatternLibrary`;
``reject <id>`` drops it. The queue and the library share one memory
backend (file by default, Redis AMS when configured), so a promote is
durable across processes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from attune.pattern_review import PatternReviewQueue, PersistentPatternLibrary

logger = logging.getLogger(__name__)


def cmd_patterns_review(args: Any) -> int:
    """List staged patterns awaiting review."""
    queue = PatternReviewQueue()
    staged = queue.list(
        pattern_type=getattr(args, "type", None),
        agent_id=getattr(args, "agent", None),
        min_confidence=getattr(args, "min_confidence", None),
    )

    if getattr(args, "json", False):
        print(json.dumps([p.to_dict() for p in staged], indent=2))
        return 0

    if not staged:
        print("No patterns staged for review.")
        return 0

    print(f"{len(staged)} pattern(s) staged for review:\n")
    for p in staged:
        print(f"  [{p.confidence:.2f}] {p.pattern_id}  ({p.pattern_type}, by {p.agent_id})")
        print(f"        {p.name}")
        if p.code:
            preview = " ".join(p.code.split())
            if len(preview) > 80:
                preview = preview[:77] + "..."
            print(f"        {preview}")
    print("\nPromote with: attune patterns promote <id>   (or reject <id>)")
    return 0


def cmd_patterns_promote(args: Any) -> int:
    """Promote a staged pattern into the active library."""
    pattern_id = getattr(args, "pattern_id", None)
    if not pattern_id:
        print("Error: a pattern id is required: attune patterns promote <id>")
        return 2

    queue = PatternReviewQueue()
    library = PersistentPatternLibrary()
    try:
        promoted = queue.promote(pattern_id, library)
    except ValueError as exc:
        print(f"Cannot promote {pattern_id!r}: {exc}")
        return 1

    if promoted is None:
        print(f"No staged pattern with id {pattern_id!r}.")
        return 1

    print(f"Promoted {pattern_id!r} into the pattern library.")
    return 0


def cmd_patterns_reject(args: Any) -> int:
    """Reject (drop) a staged pattern."""
    pattern_id = getattr(args, "pattern_id", None)
    if not pattern_id:
        print("Error: a pattern id is required: attune patterns reject <id>")
        return 2

    queue = PatternReviewQueue()
    reason = getattr(args, "reason", None) or ""
    if queue.reject(pattern_id, reason=reason):
        print(f"Rejected {pattern_id!r}.")
        return 0
    print(f"No staged pattern with id {pattern_id!r}.")
    return 1
