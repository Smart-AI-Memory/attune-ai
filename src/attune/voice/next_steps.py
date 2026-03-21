"""Contextual next-step engine for the voice layer.

Wraps the existing suggestion engine (workflows/suggestions.py)
and adds spec-aware lifecycle guidance when an active spec exists.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from . import personality

if TYPE_CHECKING:
    from attune.workflows.data_classes import NextAction

logger = logging.getLogger(__name__)


def get_next_steps(
    workflow_name: str,
    result: Any,
    max_steps: int = 3,
    *,
    compact: bool = False,
) -> list[str]:
    """Generate voiced next-step lines for a workflow result.

    Combines the existing suggestion engine output with spec-aware
    lifecycle context (when not compact), then phrases each
    suggestion in the engineer's voice.

    Args:
        workflow_name: Name of the completed workflow.
        result: WorkflowResult from the completed workflow.
        max_steps: Maximum suggestions to return (1-3).
        compact: If True, use shorter phrasing and skip spec
            suggestions. Used for MCP responses.

    Returns:
        List of natural-language suggestion strings.

    """
    suggestions = _get_raw_suggestions(workflow_name, result)

    if not compact:
        spec_suggestions = _get_spec_suggestions(workflow_name)
        if spec_suggestions:
            suggestions = spec_suggestions + suggestions

    phrase = personality.phrase_next_step_short if compact else personality.phrase_next_step

    seen: set[str] = set()
    voiced: list[str] = []
    for s in suggestions:
        if s.workflow_name not in seen:
            seen.add(s.workflow_name)
            voiced.append(phrase(s.workflow_name, s.description))
        if len(voiced) >= max_steps:
            break

    return voiced


def _get_raw_suggestions(
    workflow_name: str,
    result: Any,
) -> list[NextAction]:
    """Get raw suggestions from the existing engine.

    Args:
        workflow_name: Completed workflow name.
        result: WorkflowResult.

    Returns:
        List of NextAction from the suggestion engine.

    """
    try:
        from attune.workflows.suggestions import generate_suggestions

        return generate_suggestions(workflow_name, result)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Suggestions are optional — never break output
        logger.debug("Suggestion engine unavailable", exc_info=True)
        return []


def _get_spec_suggestions(workflow_name: str) -> list[NextAction]:
    """Check for active spec and suggest the next lifecycle stage.

    Reads ``.claude/plans/*.md`` for specs with XML tasks and
    determines which stage should come next based on the workflow
    that just completed.

    Args:
        workflow_name: The workflow that just ran.

    Returns:
        List of spec-derived NextAction suggestions (0-1 items).

    """
    try:
        from attune.voice.spec_context import get_spec_next_action

        return get_spec_next_action(workflow_name)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Spec context is optional
        logger.debug("Spec context unavailable", exc_info=True)
        return []
