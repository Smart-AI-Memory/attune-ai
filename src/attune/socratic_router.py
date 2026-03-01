"""Socratic Router - Intent-based workflow discovery.

Routes user's natural language goals to AskUserQuestion options.
Used by the /attune command for Socratic discovery flow.

Two modes:
1. Quick routing: Simple intent classification -> AskUserQuestion
   options -> skill invocation
2. Deep discovery: Full SocraticWorkflowBuilder session for complex
   agent generation

Flow (Quick):
1. User runs /attune
2. Claude asks "What are you trying to accomplish?"
3. User responds naturally
4. classify_intent() detects category
5. AskUserQuestion presents 2-4 relevant options
6. User selects -> routes to skill

Flow (Deep):
1. User needs complex workflow generation
2. SocraticWorkflowBuilder creates multi-round Q&A session
3. form_to_ask_user_question() converts Forms to AskUserQuestion
4. Generates custom agent workflow

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Re-export discovery functions for backward compatibility
from attune.socratic_router_discovery import (
    continue_deep_discovery,
    form_to_ask_user_question,
    should_use_deep_discovery,
    start_deep_discovery,
)

# Re-export models for backward compatibility
from attune.socratic_router_models import (
    IntentCategory,
    IntentClassification,
    WorkflowOption,
)

# Re-export patterns for backward compatibility
from attune.socratic_router_patterns import INTENT_PATTERNS

if TYPE_CHECKING:
    from attune.socratic import SocraticSession


def classify_intent(user_response: str) -> IntentClassification:
    """Classify user's natural language response into intent category.

    Args:
        user_response: User's answer to "What are you trying to
            accomplish?"

    Returns:
        IntentClassification with category, options, and metadata

    """
    response_lower = user_response.lower()

    best_category = IntentCategory.UNKNOWN
    best_score = 0
    matched_keywords: list[str] = []

    # Score each category based on keyword matches
    for category, pattern in INTENT_PATTERNS.items():
        keywords = pattern["keywords"]
        score = 0
        matches = []

        for keyword in keywords:
            if keyword in response_lower:
                score += 1
                matches.append(keyword)

        if score > best_score:
            best_score = score
            best_category = category
            matched_keywords = matches

    # Calculate confidence
    if best_score == 0:
        confidence = 0.0
    elif best_score >= 3:
        confidence = 0.95
    elif best_score >= 2:
        confidence = 0.8
    else:
        confidence = 0.6

    # Get options for the category
    if best_category in INTENT_PATTERNS:
        pattern = INTENT_PATTERNS[best_category]
        return IntentClassification(
            category=best_category,
            confidence=confidence,
            keywords_matched=matched_keywords,
            suggested_question=pattern["question"],
            options=pattern["options"],
        )

    # Unknown intent - ask for clarification
    return IntentClassification(
        category=IntentCategory.UNKNOWN,
        confidence=0.0,
        keywords_matched=[],
        suggested_question=("Could you tell me more about what you're trying to do?"),
        options=[
            WorkflowOption(
                label="Fix something",
                description="Debug errors, fix bugs, resolve issues",
                skill="dev",
                args="debug",
            ),
            WorkflowOption(
                label="Improve code",
                description="Refactor, optimize, clean up",
                skill="dev",
                args="refactor",
            ),
            WorkflowOption(
                label="Validate work",
                description="Test, review, audit for security",
                skill="testing",
                args="run",
            ),
            WorkflowOption(
                label="Ship changes",
                description="Commit, create PR, release",
                skill="dev",
                args="commit",
            ),
        ],
    )


def get_ask_user_question_format(
    classification: IntentClassification,
) -> dict[str, Any]:
    """Convert classification to AskUserQuestion tool format.

    Args:
        classification: Result from classify_intent()

    Returns:
        Dict ready to pass to AskUserQuestion tool

    """
    return {
        "questions": [
            {
                "question": classification.suggested_question,
                "header": classification.category.value.title(),
                "options": [opt.to_ask_user_option() for opt in classification.options],
                "multiSelect": False,
            },
        ],
    }


def get_skill_for_selection(
    classification: IntentClassification,
    selected_label: str,
) -> tuple[str, str]:
    """Get skill and args for user's selection.

    Args:
        classification: The classification that was shown to user
        selected_label: The label the user selected

    Returns:
        Tuple of (skill, args) to invoke

    """
    for option in classification.options:
        if option.label == selected_label:
            return option.skill, option.args

    # Fallback to first option if not found
    if classification.options:
        return (
            classification.options[0].skill,
            classification.options[0].args,
        )

    return "attune", ""


# Convenience function for the /attune command
def process_socratic_response(
    user_response: str,
) -> dict[str, Any]:
    """Process user's response to Socratic question.

    This is the main entry point for the /attune command after
    asking "What are you trying to accomplish?"

    Args:
        user_response: User's natural language response

    Returns:
        Dict with:
            - classification: IntentClassification object
            - ask_user_format: Ready-to-use AskUserQuestion format
            - confidence: How confident we are in the classification

    """
    classification = classify_intent(user_response)

    return {
        "classification": classification,
        "ask_user_format": get_ask_user_question_format(classification),
        "confidence": classification.confidence,
        "category": classification.category.value,
    }


class AttuneRouter:
    """Unified router for /attune command.

    Handles both quick routing and deep discovery modes.

    Example (Claude Code /attune command):
        >>> router = AttuneRouter()
        >>>
        >>> # User says: "I need to fix a bug"
        >>> result = router.process("I need to fix a bug")
        >>>
        >>> if result["mode"] == "quick":
        >>>     # Use AskUserQuestion with result["ask_user_format"]
        >>>     # Then call router.route_selection(result, user_selection)
        >>>
        >>> elif result["mode"] == "deep":
        >>>     # Multi-round discovery session
        >>>     # Use AskUserQuestion, then router.continue_session(...)
    """

    def __init__(self) -> None:
        """Initialize the router."""
        self._sessions: dict[str, SocraticSession] = {}

    def process(self, user_response: str) -> dict[str, Any]:
        """Process user's response and determine routing mode.

        Args:
            user_response: User's answer to "What are you trying to
                accomplish?"

        Returns:
            Dict with:
                - mode: "quick" or "deep"
                - ask_user_format: Ready for AskUserQuestion tool
                - classification: (quick mode) IntentClassification
                - session: (deep mode) SocraticSession

        """
        classification = classify_intent(user_response)

        if should_use_deep_discovery(user_response, classification):
            session, ask_user_format = start_deep_discovery(user_response)
            self._sessions[session.session_id] = session

            return {
                "mode": "deep",
                "session_id": session.session_id,
                "ask_user_format": ask_user_format,
                "classification": classification,
            }
        return {
            "mode": "quick",
            "ask_user_format": get_ask_user_question_format(classification),
            "classification": classification,
            "category": classification.category.value,
        }

    def route_selection(
        self,
        process_result: dict[str, Any],
        selected_label: str,
    ) -> dict[str, Any]:
        """Route user's selection to skill invocation.

        Args:
            process_result: Result from process()
            selected_label: Label user selected in AskUserQuestion

        Returns:
            Dict with skill and args to invoke

        """
        classification = process_result.get("classification")

        if classification:
            skill, args = get_skill_for_selection(classification, selected_label)
        else:
            skill, args = "attune", ""

        return {
            "skill": skill,
            "args": args,
            "instruction": f"Use Skill tool with skill='{skill}'"
            + (f", args='{args}'" if args else ""),
        }

    def continue_session(
        self,
        session_id: str,
        answers: dict[str, Any],
    ) -> dict[str, Any]:
        """Continue a deep discovery session.

        Args:
            session_id: Session ID from process() result
            answers: User's answers to questions

        Returns:
            Dict with next questions or generated workflow

        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        session, next_questions = continue_deep_discovery(session, answers)
        self._sessions[session_id] = session

        if next_questions:
            return {
                "mode": "deep",
                "session_id": session_id,
                "ask_user_format": next_questions,
            }
        # Ready to generate
        from attune.socratic import SocraticWorkflowBuilder

        builder = SocraticWorkflowBuilder()
        builder._sessions[session_id] = session
        workflow = builder.generate_workflow(session)

        return {
            "mode": "complete",
            "session_id": session_id,
            "workflow": workflow,
            "summary": builder.get_session_summary(session),
        }


# Ensure all public names are importable from this module
__all__ = [
    "INTENT_PATTERNS",
    "AttuneRouter",
    "IntentCategory",
    "IntentClassification",
    "WorkflowOption",
    "classify_intent",
    "continue_deep_discovery",
    "form_to_ask_user_question",
    "get_ask_user_question_format",
    "get_skill_for_selection",
    "process_socratic_response",
    "should_use_deep_discovery",
    "start_deep_discovery",
]
