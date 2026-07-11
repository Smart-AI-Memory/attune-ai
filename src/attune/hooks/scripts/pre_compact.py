"""Pre-Compact Hook Script

Saves collaboration state before context compaction occurs.
Ensures trust levels, patterns, and handoffs are preserved.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def run_pre_compact(context: dict[str, Any]) -> dict[str, Any]:
    """Execute pre-compaction state preservation.

    This hook is called before context compaction to save
    the current collaboration state for restoration after
    the context window resets.

    Args:
        context: Hook context containing:
            - collaboration_state: Current CollaborationState
            - context_manager: ContextManager instance
            - session_id: Current session identifier
            - current_phase: Current work phase (if any)
            - pending_work: Description of pending work (if any)

    Returns:
        Dict with:
            - state_saved: Whether state was successfully saved
            - saved_path: Path to saved state file
            - trust_level: Trust level that was preserved
            - patterns_count: Number of patterns preserved
            - has_handoff: Whether a handoff was saved
            - restoration_available: Whether restoration will be available
            - message: Human-readable summary

    """
    try:
        # Get required components from context
        collaboration_state = context.get("collaboration_state")
        context_manager = context.get("context_manager")

        if not collaboration_state:
            logger.warning("Pre-compact: No collaboration state provided")
            return {
                "state_saved": False,
                "saved_path": None,
                "trust_level": None,
                "patterns_count": 0,
                "has_handoff": False,
                "restoration_available": False,
                "message": "No collaboration state available to save",
            }

        # Initialize context manager if not provided
        if not context_manager:
            from attune.context import ContextManager

            context_manager = ContextManager()

        # Set session tracking if provided
        if session_id := context.get("session_id"):
            context_manager.session_id = session_id

        if current_phase := context.get("current_phase"):
            context_manager.current_phase = current_phase

        # Create structured work handoff for pending work if provided
        pending_work = context.get("pending_work")
        if pending_work:
            context_manager.set_handoff(
                situation=pending_work.get("situation", "Context compaction in progress"),
                background=pending_work.get("background", "Session state being preserved"),
                assessment=pending_work.get("assessment", "Work can continue after restoration"),
                recommendation=pending_work.get("recommendation", "Restore state and continue"),
                priority=pending_work.get("priority", "normal"),
            )

        # Save the state
        saved_path = context_manager.save_for_compaction(collaboration_state)

        # Extract the compact state for reporting
        compact_state = context_manager.extract_compact_state(collaboration_state)

        # Build success message
        patterns_count = len(compact_state.detected_patterns)
        message_parts = [
            "State preserved successfully.",
            f"Trust level: {compact_state.trust_level:.2f}",
            f"Empathy level: {compact_state.empathy_level}",
        ]

        if patterns_count > 0:
            message_parts.append(f"Patterns preserved: {patterns_count}")

        if compact_state.pending_handoff:
            message_parts.append(
                f"Handoff recorded ({compact_state.pending_handoff.priority} priority)",
            )

        logger.info(f"Pre-compact: Saved state to {saved_path}")

        return {
            "state_saved": True,
            "saved_path": str(saved_path),
            "trust_level": compact_state.trust_level,
            "empathy_level": compact_state.empathy_level,
            "patterns_count": patterns_count,
            "has_handoff": compact_state.pending_handoff is not None,
            "restoration_available": True,
            "saved_at": datetime.now().isoformat(),
            "message": " | ".join(message_parts),
        }

    except Exception as e:  # noqa: BLE001
        logger.exception(f"Pre-compact hook failed: {e}")
        return {
            "state_saved": False,
            "saved_path": None,
            "trust_level": None,
            "patterns_count": 0,
            "has_handoff": False,
            "restoration_available": False,
            "error": str(e),
            "message": f"Failed to save state: {e}",
        }


def generate_compaction_summary(
    collaboration_state: Any,
    include_patterns: bool = True,
    include_history: bool = False,
) -> str:
    """Generate a summary suitable for including in compacted context.

    This can be used to create a brief summary that gets included
    in the compacted context window.

    Args:
        collaboration_state: Current CollaborationState
        include_patterns: Whether to include pattern summaries
        include_history: Whether to include recent interaction summary

    Returns:
        Formatted summary string

    """
    lines = [
        "## Session Context Summary",
        "",
        f"**User**: {collaboration_state.user_id}",
        f"**Trust**: {collaboration_state.trust_level:.2f}",
        f"**Empathy Level**: {collaboration_state.current_level}",
        f"**Interactions**: {len(collaboration_state.interactions)}",
        "",
    ]

    if include_patterns and collaboration_state.detected_patterns:
        lines.append("### Known Patterns")
        for pattern in collaboration_state.detected_patterns[:5]:
            confidence_pct = int(pattern.confidence * 100)
            lines.append(f"- {pattern.trigger} → {pattern.action} ({confidence_pct}%)")
        lines.append("")

    if include_history and collaboration_state.interactions:
        lines.append("### Recent Context")
        # Get last few exchanges
        recent = collaboration_state.interactions[-6:]
        for interaction in recent:
            role = interaction.role.capitalize()
            content = interaction.content[:100]
            if len(interaction.content) > 100:
                content += "..."
            lines.append(f"- **{role}**: {content}")
        lines.append("")

    # Add preferences summary
    if collaboration_state.preferences:
        lines.append("### Preferences")
        for key, value in list(collaboration_state.preferences.items())[:5]:
            lines.append(f"- **{key}**: {value}")
        lines.append("")

    return "\n".join(lines)


# Main entry point for hook execution
if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    # Example usage for testing
    print("Pre-compact hook script")
    print("This script is called before context compaction")
    print()
    print("Required context keys:")
    print("  - collaboration_state: CollaborationState object")
    print("  - context_manager: ContextManager instance (optional)")
    print("  - session_id: Current session ID (optional)")
    print("  - current_phase: Current work phase (optional)")
    print("  - pending_work: Dict with handoff fields (optional)")
