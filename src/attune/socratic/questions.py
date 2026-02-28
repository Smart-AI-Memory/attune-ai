"""Question Generation for Socratic Engine

Generates initial and follow-up question forms based on goal analysis
and session state.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .forms import (
    FieldOption,
    FieldType,
    FieldValidation,
    Form,
    FormField,
    create_additional_context_field,
    create_automation_level_field,
    create_language_field,
    create_quality_focus_field,
    create_team_size_field,
)
from .session import GoalAnalysis, SocraticSession


def generate_initial_questions(
    goal_analysis: GoalAnalysis,
    session: SocraticSession,
) -> Form:
    """Generate the first round of questions based on goal analysis.

    Args:
        goal_analysis: Analyzed goal with domain and ambiguities
        session: Current Socratic session

    Returns:
        Form with initial questions

    """
    fields: list[FormField] = []

    # Always ask about languages if not detected
    if "Programming language not specified" in goal_analysis.ambiguities:
        fields.append(create_language_field(required=True))

    # Ask about quality focus
    fields.append(create_quality_focus_field(required=True))

    # Domain-specific questions
    if goal_analysis.domain == "code_review":
        fields.append(
            FormField(
                id="review_scope",
                field_type=FieldType.SINGLE_SELECT,
                label="What scope of review do you need?",
                options=[
                    FieldOption(
                        "pr",
                        "Pull Request/Diff",
                        description="Review specific changes",
                        recommended=True,
                    ),
                    FieldOption("file", "Single File", description="Deep review of one file"),
                    FieldOption(
                        "directory",
                        "Directory/Module",
                        description="Review entire module",
                    ),
                    FieldOption(
                        "project",
                        "Full Project",
                        description="Comprehensive codebase review",
                    ),
                ],
                validation=FieldValidation(required=True),
                category="scope",
            ),
        )

    if goal_analysis.domain == "security":
        fields.append(
            FormField(
                id="security_focus",
                field_type=FieldType.MULTI_SELECT,
                label="What security aspects are most important?",
                options=[
                    FieldOption("owasp", "OWASP Top 10", description="Common web vulnerabilities"),
                    FieldOption("injection", "Injection Attacks", description="SQL, command, XSS"),
                    FieldOption(
                        "auth",
                        "Authentication/Authorization",
                        description="Access control issues",
                    ),
                    FieldOption(
                        "crypto",
                        "Cryptography",
                        description="Encryption, hashing, secrets",
                    ),
                    FieldOption("deps", "Dependencies", description="Vulnerable dependencies"),
                ],
                validation=FieldValidation(required=True),
                category="security",
            ),
        )

    if goal_analysis.domain == "testing":
        fields.append(
            FormField(
                id="test_type",
                field_type=FieldType.MULTI_SELECT,
                label="What types of tests do you need?",
                options=[
                    FieldOption(
                        "unit",
                        "Unit Tests",
                        description="Test individual functions",
                        recommended=True,
                    ),
                    FieldOption(
                        "integration",
                        "Integration Tests",
                        description="Test component interactions",
                    ),
                    FieldOption("e2e", "End-to-End Tests", description="Test full user flows"),
                    FieldOption("edge", "Edge Cases", description="Test boundary conditions"),
                ],
                validation=FieldValidation(required=True),
                category="testing",
            ),
        )

    # Automation level (always relevant)
    fields.append(create_automation_level_field())

    # Team context (helps calibration)
    fields.append(create_team_size_field())

    # Additional context (optional)
    fields.append(create_additional_context_field())

    return Form(
        id=f"round_{session.current_round + 1}",
        title="Help Us Understand Your Needs",
        description=f'Based on your goal: "{goal_analysis.raw_goal[:100]}..."',
        fields=fields,
        round_number=session.current_round + 1,
        progress=0.3,
    )


def generate_followup_questions(
    session: SocraticSession,
) -> Form | None:
    """Generate follow-up questions based on previous answers.

    Args:
        session: Current Socratic session

    Returns:
        Form with follow-up questions, or None if ready to generate

    """
    # Check if we need more clarification
    if session.requirements.completeness_score() >= 0.8:
        return None  # Ready to generate

    if session.current_round >= session.max_rounds:
        return None  # Max rounds reached

    fields: list[FormField] = []

    # Check what's still missing
    reqs = session.requirements

    # If no must-haves, ask for priorities
    if not reqs.must_have:
        fields.append(
            FormField(
                id="priorities",
                field_type=FieldType.TEXT_AREA,
                label="What are your top 3 priorities for this workflow?",
                help_text="Be as specific as possible about what success looks like.",
                validation=FieldValidation(required=True, min_length=20),
                category="priorities",
            ),
        )

    # If technical constraints missing
    if not reqs.technical_constraints.get("languages"):
        fields.append(create_language_field(required=True))

    # Domain-specific follow-ups
    if session.goal_analysis and session.goal_analysis.domain == "code_review":
        if (
            "review_depth" not in [r.get("id") for r in session.question_rounds[-1]["questions"]]
            if session.question_rounds
            else True
        ):
            fields.append(
                FormField(
                    id="review_depth",
                    field_type=FieldType.SINGLE_SELECT,
                    label="How thorough should the review be?",
                    options=[
                        FieldOption(
                            "quick",
                            "Quick Scan",
                            description="Fast, surface-level review",
                        ),
                        FieldOption(
                            "standard",
                            "Standard",
                            description="Balanced depth",
                            recommended=True,
                        ),
                        FieldOption("deep", "Deep Dive", description="Thorough, detailed analysis"),
                    ],
                    category="depth",
                ),
            )

    if not fields:
        return None

    return Form(
        id=f"round_{session.current_round + 1}",
        title="A Few More Questions",
        description="Help us fine-tune your workflow.",
        fields=fields,
        round_number=session.current_round + 1,
        progress=0.3 + (session.current_round * 0.2),
    )
