"""Evaluate Session Hook Script

Evaluates sessions at end for learning potential and extracts patterns.
Called during SessionEnd hook to enable continuous learning.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_evaluate_session(context: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a session for learning potential.

    This hook is called at session end to:
    1. Evaluate if the session has learning value
    2. Extract patterns if valuable
    3. Store patterns for future use

    Args:
        context: Hook context containing:
            - collaboration_state: CollaborationState
            - user_id: User identifier
            - session_id: Session identifier
            - storage_dir: Optional storage directory
            - min_score: Optional minimum score for extraction

    Returns:
        Dict with:
            - evaluated: Whether evaluation completed
            - quality: Session quality rating
            - score: Numeric score (0.0-1.0)
            - patterns_extracted: Number of patterns extracted
            - patterns_stored: Number of patterns stored
            - learnable_topics: List of identified topics
            - reasoning: Human-readable evaluation reasoning
            - error: Error message if failed

    """
    try:
        collaboration_state = context.get("collaboration_state")
        user_id = context.get("user_id")
        session_id = context.get("session_id", "")
        storage_dir = context.get("storage_dir", ".attune/learned_skills")
        min_score = context.get("min_score", 0.4)

        if not collaboration_state:
            return {
                "evaluated": False,
                "error": "No collaboration state provided",
            }

        if not user_id:
            user_id = collaboration_state.user_id

        # Import learning components
        from attune.learning import (
            LearnedSkillsStorage,
            PatternExtractor,
            SessionEvaluator,
        )

        # Evaluate the session
        evaluator = SessionEvaluator(min_score_for_extraction=min_score)
        evaluation = evaluator.evaluate(collaboration_state)

        result = {
            "evaluated": True,
            "quality": evaluation.quality.value,
            "score": evaluation.score,
            "learnable_topics": evaluation.learnable_topics,
            "reasoning": evaluation.reasoning,
            "patterns_extracted": 0,
            "patterns_stored": 0,
        }

        # Extract patterns if recommended
        if evaluation.recommended_extraction:
            extractor = PatternExtractor()
            patterns = extractor.extract_patterns(collaboration_state, session_id)

            result["patterns_extracted"] = len(patterns)

            if patterns:
                # Store patterns
                storage = LearnedSkillsStorage(storage_dir=storage_dir)
                stored_ids = storage.save_patterns(user_id, patterns)
                result["patterns_stored"] = len(stored_ids)

                # Include pattern summaries
                result["pattern_summaries"] = [
                    {
                        "id": p.pattern_id,
                        "category": p.category.value,
                        "trigger": p.trigger[:50],
                        "confidence": p.confidence,
                    }
                    for p in patterns[:5]  # Top 5
                ]

                logger.info(
                    f"Extracted {len(patterns)} patterns, stored {len(stored_ids)} "
                    f"for user {user_id}",
                )
        else:
            logger.debug(f"Session not recommended for extraction (score: {evaluation.score:.2f})")

        return result

    except Exception as e:  # noqa: BLE001
        logger.exception(f"Session evaluation failed: {e}")
        return {
            "evaluated": False,
            "error": str(e),
        }


def get_learning_summary(context: dict[str, Any]) -> dict[str, Any]:
    """Get learning summary for a user.

    Args:
        context: Context with user_id and optional storage_dir

    Returns:
        Learning summary dictionary

    """
    try:
        user_id = context.get("user_id")
        storage_dir = context.get("storage_dir", ".attune/learned_skills")

        if not user_id:
            return {"error": "No user_id provided"}

        from attune.learning import LearnedSkillsStorage

        storage = LearnedSkillsStorage(storage_dir=storage_dir)
        return storage.get_summary(user_id)

    except Exception as e:  # noqa: BLE001
        logger.exception(f"Failed to get learning summary: {e}")
        return {"error": str(e)}


def apply_learned_patterns(context: dict[str, Any]) -> str:
    """Generate context injection from learned patterns.

    Args:
        context: Context with user_id, max_patterns, and optional filters

    Returns:
        Formatted markdown for context injection

    """
    try:
        user_id = context.get("user_id")
        max_patterns = context.get("max_patterns", 5)
        storage_dir = context.get("storage_dir", ".attune/learned_skills")

        if not user_id:
            return ""

        from attune.learning import LearnedSkillsStorage, PatternCategory

        # Parse category filter if provided
        categories = None
        if cat_filter := context.get("categories"):
            categories = [PatternCategory(c) for c in cat_filter]

        storage = LearnedSkillsStorage(storage_dir=storage_dir)
        return storage.format_patterns_for_context(
            user_id,
            max_patterns=max_patterns,
            categories=categories,
        )

    except Exception as e:  # noqa: BLE001
        logger.exception(f"Failed to apply learned patterns: {e}")
        return ""


# Entry point for hook execution
if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    print("Evaluate Session Hook Script")
    print("This script is called at session end to evaluate learning potential")
    print()
    print("Required context keys:")
    print("  - collaboration_state: CollaborationState object")
    print("  - user_id: User identifier (optional, uses state.user_id)")
    print()
    print("Optional context keys:")
    print("  - session_id: Session identifier")
    print("  - storage_dir: Storage directory path")
    print("  - min_score: Minimum score for extraction (default: 0.4)")
