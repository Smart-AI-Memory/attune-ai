"""Socratic Router Discovery - Deep discovery via SocraticWorkflowBuilder.

Provides multi-round Q&A sessions for complex workflow generation,
bridging the Socratic system's Form objects with Claude Code's
AskUserQuestion tool.

Functions:
- form_to_ask_user_question: Convert Form to AskUserQuestion format
- should_use_deep_discovery: Decide quick vs deep routing
- start_deep_discovery: Begin a SocraticWorkflowBuilder session
- continue_deep_discovery: Continue session with user answers

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from attune.socratic_router_models import IntentClassification

if TYPE_CHECKING:
    from attune.socratic import Form, SocraticSession


def form_to_ask_user_question(form: Form) -> dict[str, Any]:
    """Convert a SocraticWorkflowBuilder Form to AskUserQuestion format.

    This bridges the Socratic system's Form objects with Claude Code's
    AskUserQuestion tool.

    Args:
        form: Form from SocraticWorkflowBuilder.get_next_questions()

    Returns:
        Dict ready to pass to AskUserQuestion tool

    Example:
        >>> from attune.socratic import SocraticWorkflowBuilder
        >>> builder = SocraticWorkflowBuilder()
        >>> session = builder.start_session("automate code reviews")
        >>> form = builder.get_next_questions(session)
        >>> ask_user_format = form_to_ask_user_question(form)

    """
    from attune.socratic.forms import FieldType

    questions = []

    for field in form.fields:
        # Convert field to question format
        question_data = {
            "question": field.label,
            "header": field.category.title() if field.category else "Question",
            "multiSelect": field.field_type == FieldType.MULTI_SELECT,
            "options": [],
        }

        # Convert options
        if field.options:
            for opt in field.options[:4]:  # AskUserQuestion max 4 options
                option_data = {
                    "label": opt.value,
                    "description": opt.description or opt.label,
                }
                if opt.recommended:
                    option_data["label"] += " (Recommended)"
                question_data["options"].append(option_data)
        else:
            # Text field - provide generic options
            question_data["options"] = [
                {
                    "label": "Continue",
                    "description": "Proceed with current settings",
                },
                {
                    "label": "Customize",
                    "description": "I want to specify details",
                },
            ]

        questions.append(question_data)

    # Limit to 4 questions per AskUserQuestion call
    return {"questions": questions[:4]}


def should_use_deep_discovery(user_response: str, classification: IntentClassification) -> bool:
    """Determine if we should use full SocraticWorkflowBuilder.

    Use deep discovery when:
    - Low confidence classification
    - User wants to create custom agents/workflows
    - Complex multi-step requirements

    Args:
        user_response: User's natural language response
        classification: Result from classify_intent()

    Returns:
        True if should use SocraticWorkflowBuilder, False for quick routing

    """
    # Low confidence - need more clarification
    if classification.confidence < 0.5:
        return True

    # Explicit agent/workflow creation keywords
    deep_keywords = [
        "create agent",
        "custom workflow",
        "build workflow",
        "automate",
        "automation",
        "generate agents",
        "multi-step",
        "pipeline",
    ]

    response_lower = user_response.lower()
    for keyword in deep_keywords:
        if keyword in response_lower:
            return True

    return False


def start_deep_discovery(
    goal: str,
) -> tuple[SocraticSession, dict[str, Any]]:
    """Start a full SocraticWorkflowBuilder session.

    Args:
        goal: User's goal statement

    Returns:
        Tuple of (session, ask_user_format)

    Example:
        >>> session, questions = start_deep_discovery(
        ...     "automate security reviews"
        ... )
        >>> # Use questions with AskUserQuestion tool
        >>> # Then call continue_deep_discovery(session, answers)

    """
    from attune.socratic import SocraticWorkflowBuilder

    builder = SocraticWorkflowBuilder()
    session = builder.start_session(goal)
    form = builder.get_next_questions(session)

    if form:
        ask_user_format = form_to_ask_user_question(form)
    else:
        # Session ready to generate
        ask_user_format = {
            "questions": [
                {
                    "question": ("Ready to generate your workflow. Proceed?"),
                    "header": "Generate",
                    "options": [
                        {
                            "label": "Generate",
                            "description": "Create the workflow now",
                        },
                        {
                            "label": "Add details",
                            "description": "I want to specify more",
                        },
                    ],
                    "multiSelect": False,
                },
            ],
        }

    return session, ask_user_format


def continue_deep_discovery(
    session: SocraticSession,
    answers: dict[str, Any],
) -> tuple[SocraticSession, dict[str, Any] | None]:
    """Continue a SocraticWorkflowBuilder session with answers.

    Args:
        session: Active session from start_deep_discovery
        answers: User's answers to previous questions

    Returns:
        Tuple of (updated_session, next_questions_or_None)

    """
    from attune.socratic import SocraticWorkflowBuilder

    builder = SocraticWorkflowBuilder()
    builder._sessions[session.session_id] = session

    session = builder.submit_answers(session, answers)

    if builder.is_ready_to_generate(session):
        return session, None

    form = builder.get_next_questions(session)
    if form:
        return session, form_to_ask_user_question(form)

    return session, None
