"""Voice personality constants for Attune AI.

Defines the tone, formatting conventions, and phrasing
templates used across all output surfaces.

The personality is a friendly senior engineer: direct,
warm, and empathic without making a big deal about it.
Empathy is part of the communication style, not a feature.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Greeting / sign-off phrases by result context
# ---------------------------------------------------------------------------

GREETING_SUCCESS = "Here's what I found."
GREETING_PARTIAL = "I ran into a few things worth flagging."
GREETING_FAILURE = "This one didn't go as planned — here's what happened."

# ---------------------------------------------------------------------------
# Score commentary — friendly, not robotic
# ---------------------------------------------------------------------------

SCORE_EXCELLENT = "Looking solid — this is in great shape."
SCORE_GOOD = "Pretty good overall, with a few things to tighten up."
SCORE_NEEDS_WORK = "There's some real work to do here — let me walk you through it."
SCORE_CRITICAL = "This needs attention before it goes anywhere."


def score_commentary(score: int) -> str:
    """Return a human commentary line for a score.

    Args:
        score: Score value 0-100.

    Returns:
        Friendly one-liner about the score.

    """
    if score >= 85:
        return SCORE_EXCELLENT
    if score >= 70:
        return SCORE_GOOD
    if score >= 50:
        return SCORE_NEEDS_WORK
    return SCORE_CRITICAL


# ---------------------------------------------------------------------------
# Next-step phrasing — sounds like a colleague, not a menu
# ---------------------------------------------------------------------------


def phrase_next_step(workflow_name: str, description: str) -> str:
    """Phrase a next-step suggestion in the engineer's voice.

    Args:
        workflow_name: Target workflow name (e.g. "security-audit").
        description: What the suggestion is about.

    Returns:
        A natural-language suggestion string.

    """
    return f"I'd run `attune workflow run {workflow_name}` next — {description}"


def phrase_next_step_short(workflow_name: str, description: str) -> str:
    """Shorter next-step for compact contexts (MCP, errors).

    Args:
        workflow_name: Target workflow name.
        description: Brief description.

    Returns:
        Compact suggestion string.

    """
    return f"Try `{workflow_name}` — {description}"


# ---------------------------------------------------------------------------
# Error phrasing — calm, not alarming
# ---------------------------------------------------------------------------

ERROR_PREFIX = "Something went wrong"
ERROR_TRANSIENT = "This looks like a temporary issue — worth retrying."
ERROR_CONFIG = "This might be a configuration issue. Check your setup."
ERROR_GENERIC = "Here's the error so you can dig in:"


def phrase_error(error_type: str | None) -> str:
    """Return contextual phrasing for an error type.

    Args:
        error_type: Structured error type from WorkflowResult.

    Returns:
        Friendly error context string.

    """
    if error_type == "transient":
        return ERROR_TRANSIENT
    if error_type == "config":
        return ERROR_CONFIG
    return ERROR_GENERIC


# ---------------------------------------------------------------------------
# Section headers — consistent across all surfaces
# ---------------------------------------------------------------------------

HEADER_NEXT_STEPS = "What I'd Do Next"
HEADER_COST = "Cost & Time"
HEADER_ERROR = "What Went Wrong"
