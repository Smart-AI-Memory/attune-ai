"""Socratic Router - Intent-based workflow discovery.

Routes user's natural language goals to AskUserQuestion options.
Used by the /attune command for Socratic discovery flow.

Two modes:
1. Quick routing: Simple intent classification → AskUserQuestion options → skill invocation
2. Deep discovery: Full SocraticWorkflowBuilder session for complex agent generation

Flow (Quick):
1. User runs /attune
2. Claude asks "What are you trying to accomplish?"
3. User responds naturally
4. classify_intent() detects category
5. AskUserQuestion presents 2-4 relevant options
6. User selects → routes to skill

Flow (Deep):
1. User needs complex workflow generation
2. SocraticWorkflowBuilder creates multi-round Q&A session
3. form_to_ask_user_question() converts Forms to AskUserQuestion
4. Generates custom agent workflow

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from attune.socratic import Form, SocraticSession


class IntentCategory(Enum):
    """High-level categories of user intent."""

    FIX = "fix"  # Debug, fix bugs, resolve errors
    IMPROVE = "improve"  # Refactor, optimize, clean up
    VALIDATE = "validate"  # Test, review, audit
    SHIP = "ship"  # Commit, PR, release
    UNDERSTAND = "understand"  # Explain, document, explore
    CREATE = "create"  # Build new wizards, agents, teams, workflows
    UNKNOWN = "unknown"  # Needs clarification


@dataclass
class WorkflowOption:
    """A workflow option for AskUserQuestion.

    Attributes:
        label: Short label for the option (1-5 words)
        description: What this option does
        skill: The skill to invoke
        args: Arguments for the skill
    """

    label: str
    description: str
    skill: str
    args: str = ""

    def to_ask_user_option(self) -> dict[str, str]:
        """Convert to AskUserQuestion option format."""
        return {"label": self.label, "description": self.description}


@dataclass
class IntentClassification:
    """Result of classifying user intent.

    Attributes:
        category: Primary intent category
        confidence: Confidence score (0-1)
        keywords_matched: Keywords that triggered this classification
        suggested_question: Question to ask via AskUserQuestion
        options: Workflow options to present
    """

    category: IntentCategory
    confidence: float
    keywords_matched: list[str]
    suggested_question: str
    options: list[WorkflowOption]


# Intent detection patterns
INTENT_PATTERNS: dict[IntentCategory, dict[str, Any]] = {
    IntentCategory.FIX: {
        "keywords": [
            "fix",
            "bug",
            "error",
            "broken",
            "crash",
            "fail",
            "issue",
            "problem",
            "debug",
            "wrong",
            "doesn't work",
            "not working",
            "exception",
            "traceback",
        ],
        "question": "What kind of issue are you dealing with?",
        "options": [
            WorkflowOption(
                label="Debug an error",
                description="Investigate exceptions, trace execution, find root cause",
                skill="dev",
                args="debug",
            ),
            WorkflowOption(
                label="Fix failing tests",
                description="Analyze test failures and fix the underlying code",
                skill="testing",
                args="run",
            ),
            WorkflowOption(
                label="Review for bugs",
                description="Code review focused on finding potential bugs",
                skill="dev",
                args="review",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe your specific issue",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.IMPROVE: {
        "keywords": [
            "refactor",
            "improve",
            "clean",
            "optimize",
            "simplify",
            "better",
            "performance",
            "speed",
            "faster",
            "memory",
            "too long",
            "complex",
            "messy",
            "ugly",
        ],
        "question": "What would you like to improve?",
        "options": [
            WorkflowOption(
                label="Refactor code",
                description="Improve structure, extract functions, simplify logic",
                skill="dev",
                args="refactor",
            ),
            WorkflowOption(
                label="Optimize performance",
                description="Find bottlenecks, improve speed and memory usage",
                skill="workflows",
                args="run perf-audit",
            ),
            WorkflowOption(
                label="Code review",
                description="Get feedback on code quality and patterns",
                skill="dev",
                args="review",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe what you want to improve",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.VALIDATE: {
        "keywords": [
            "test",
            "coverage",
            "security",
            "audit",
            "check",
            "verify",
            "validate",
            "review",
            "safe",
            "secure",
            "vulnerability",
        ],
        "question": "What would you like to validate?",
        "options": [
            WorkflowOption(
                label="Run tests",
                description="Execute test suite and see results",
                skill="testing",
                args="run",
            ),
            WorkflowOption(
                label="Check coverage",
                description="Analyze test coverage and identify gaps",
                skill="testing",
                args="coverage",
            ),
            WorkflowOption(
                label="Security audit",
                description="Scan for vulnerabilities and security issues",
                skill="workflows",
                args="run security-audit",
            ),
            WorkflowOption(
                label="Code review",
                description="Quality and pattern analysis",
                skill="dev",
                args="review",
            ),
        ],
    },
    IntentCategory.SHIP: {
        "keywords": [
            "commit",
            "push",
            "pr",
            "pull request",
            "merge",
            "release",
            "deploy",
            "ship",
            "publish",
            "done",
            "ready",
            "finished",
        ],
        "question": "What stage are you at?",
        "options": [
            WorkflowOption(
                label="Create commit",
                description="Stage changes and create a commit with message",
                skill="dev",
                args="commit",
            ),
            WorkflowOption(
                label="Create PR",
                description="Push branch and create pull request",
                skill="dev",
                args="pr",
            ),
            WorkflowOption(
                label="Prepare release",
                description="Version bump, changelog, security checks",
                skill="release",
                args="prep",
            ),
            WorkflowOption(
                label="Just push",
                description="Push current commits to remote",
                skill="dev",
                args="push",
            ),
        ],
    },
    IntentCategory.UNDERSTAND: {
        "keywords": [
            "explain",
            "understand",
            "how",
            "what",
            "why",
            "document",
            "docs",
            "readme",
            "learn",
            "show",
            "describe",
            "overview",
        ],
        "question": "What would you like to understand?",
        "options": [
            WorkflowOption(
                label="Explain code",
                description="Understand how specific code works",
                skill="docs",
                args="explain",
            ),
            WorkflowOption(
                label="Project overview",
                description="High-level architecture and structure",
                skill="docs",
                args="overview",
            ),
            WorkflowOption(
                label="Generate docs",
                description="Create or update documentation",
                skill="docs",
                args="generate",
            ),
            WorkflowOption(
                label="Something specific",
                description="Ask about a specific part of the codebase",
                skill="attune",
                args="",
            ),
        ],
    },
    IntentCategory.CREATE: {
        "keywords": [
            "create",
            "build",
            "new",
            "define",
            "custom",
            "wizard",
            "agent",
            "team",
            "scaffold",
            "generate agent",
            "make a",
            "set up",
        ],
        "question": "What would you like to create?",
        "options": [
            WorkflowOption(
                label="Create a wizard",
                description="Define a new custom guided workflow (YAML-based)",
                skill="wizard",
                args="create",
            ),
            WorkflowOption(
                label="Create an agent",
                description="Define a new specialized AI agent with role and tools",
                skill="agent",
                args="create",
            ),
            WorkflowOption(
                label="Create an agent team",
                description="Build a multi-agent collaboration pipeline",
                skill="agent",
                args="create-team",
            ),
            WorkflowOption(
                label="Something else",
                description="Describe what you want to create",
                skill="attune",
                args="",
            ),
        ],
    },
}


def classify_intent(user_response: str) -> IntentClassification:
    """Classify user's natural language response into intent category.

    Args:
        user_response: User's answer to "What are you trying to accomplish?"

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
        suggested_question="Could you tell me more about what you're trying to do?",
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


def get_ask_user_question_format(classification: IntentClassification) -> dict[str, Any]:
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
            }
        ]
    }


def get_skill_for_selection(
    classification: IntentClassification, selected_label: str
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
        return classification.options[0].skill, classification.options[0].args

    return "attune", ""


# Convenience function for the /attune command
def process_socratic_response(user_response: str) -> dict[str, Any]:
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


# =============================================================================
# DEEP DISCOVERY - SocraticWorkflowBuilder Integration
# =============================================================================


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
                option_data = {"label": opt.value, "description": opt.description or opt.label}
                if opt.recommended:
                    option_data["label"] += " (Recommended)"
                question_data["options"].append(option_data)
        else:
            # Text field - provide generic options
            question_data["options"] = [
                {"label": "Continue", "description": "Proceed with current settings"},
                {"label": "Customize", "description": "I want to specify details"},
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


def start_deep_discovery(goal: str) -> tuple[SocraticSession, dict[str, Any]]:
    """Start a full SocraticWorkflowBuilder session.

    Args:
        goal: User's goal statement

    Returns:
        Tuple of (session, ask_user_format)

    Example:
        >>> session, questions = start_deep_discovery("automate security reviews")
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
                    "question": "Ready to generate your workflow. Proceed?",
                    "header": "Generate",
                    "options": [
                        {"label": "Generate", "description": "Create the workflow now"},
                        {"label": "Add details", "description": "I want to specify more"},
                    ],
                    "multiSelect": False,
                }
            ]
        }

    return session, ask_user_format


def continue_deep_discovery(
    session: SocraticSession, answers: dict[str, Any]
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


# =============================================================================
# UNIFIED ENTRY POINT
# =============================================================================


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

    def __init__(self):
        """Initialize the router."""
        self._sessions: dict[str, SocraticSession] = {}

    def process(self, user_response: str) -> dict[str, Any]:
        """Process user's response and determine routing mode.

        Args:
            user_response: User's answer to "What are you trying to accomplish?"

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
        else:
            return {
                "mode": "quick",
                "ask_user_format": get_ask_user_question_format(classification),
                "classification": classification,
                "category": classification.category.value,
            }

    def route_selection(
        self, process_result: dict[str, Any], selected_label: str
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

    def continue_session(self, session_id: str, answers: dict[str, Any]) -> dict[str, Any]:
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
        else:
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
