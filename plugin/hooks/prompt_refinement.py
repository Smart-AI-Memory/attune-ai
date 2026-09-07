#!/usr/bin/env python
"""Inject the shared prompt-refinement policy on each Claude Code user turn."""

from __future__ import annotations

import json
import sys


def main() -> int:
    """Emit a current policy; fail visibly without blocking the incoming prompt."""
    try:
        from attune.prompt_refinement import refinement_status

        event = json.load(sys.stdin)
        if not isinstance(event, dict) or not isinstance(event.get("prompt"), str):
            raise ValueError("Expected a user prompt event")
        result = refinement_status(
            skip_this_prompt=event["prompt"].lstrip().startswith("[no-refine]")
        )
        context = "Attune refinement hook result for this turn:\n" + json.dumps(result)
    except (ImportError, OSError, ValueError, UnicodeError) as exc:
        print(f"Attune prompt refinement unavailable: {exc}", file=sys.stderr)
        context = (
            "Attune prompt refinement is unavailable; continue ordinary assistance. "
            "Do not automatically refine this prompt."
        )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
