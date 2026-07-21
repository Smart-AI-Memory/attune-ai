"""Trap description formatter for Attune AI.

Turns a TrapEvent into the compact, factual description stored in the
session stash. No canned advice, no LLM — the finding is the evidence.
"""

from .listener import TrapEvent

_HEADLINES = {
    "precommit_rejection": "pre-commit rejected the commit",
    "pytest_failure": "test run failed",
}


def format_trap(event: TrapEvent) -> str:
    """Format a trap event as a stash-ready factual description.

    Args:
        event: The extracted trap event.

    Returns:
        A bounded plain-text description: headline, command, evidence.
    """
    headline = _HEADLINES.get(event.family, event.family)
    return f"Trap: {headline}. Command: `{event.command}`\n{event.detail}"
