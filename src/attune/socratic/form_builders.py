"""Pre-built form field factory functions.

Convenience builders that create commonly used FormField instances
with pre-configured options, validation, and metadata.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .forms import FieldOption, FieldType, FieldValidation, FormField


def create_language_field(
    id: str = "languages",
    required: bool = True,
) -> FormField:
    """Create a standard programming language selection field."""
    return FormField(
        id=id,
        field_type=FieldType.MULTI_SELECT,
        label="What programming languages does your team primarily use?",
        help_text="Select all that apply. This helps us customize analysis tools.",
        options=[
            FieldOption("python", "Python", icon="🐍", recommended=True),
            FieldOption("typescript", "TypeScript", icon="📘"),
            FieldOption("javascript", "JavaScript", icon="📒"),
            FieldOption("java", "Java", icon="☕"),
            FieldOption("go", "Go", icon="🐹"),
            FieldOption("rust", "Rust", icon="🦀"),
            FieldOption("csharp", "C#", icon="🎯"),
            FieldOption("cpp", "C++", icon="⚡"),
            FieldOption("ruby", "Ruby", icon="💎"),
            FieldOption("php", "PHP", icon="🐘"),
            FieldOption("other", "Other", icon="🔧"),
        ],
        validation=FieldValidation(required=required),
        category="technical",
    )


def create_quality_focus_field(
    id: str = "quality_focus",
    required: bool = True,
) -> FormField:
    """Create a quality focus area selection field."""
    return FormField(
        id=id,
        field_type=FieldType.MULTI_SELECT,
        label="What quality attributes are most important?",
        help_text="Select your top priorities. We'll optimize agents for these.",
        options=[
            FieldOption(
                "security",
                "Security",
                description="Vulnerability detection, secure coding practices",
                icon="🔒",
            ),
            FieldOption(
                "performance",
                "Performance",
                description="Speed, memory usage, scalability",
                icon="⚡",
            ),
            FieldOption(
                "maintainability",
                "Maintainability",
                description="Code clarity, documentation, modularity",
                icon="🧩",
            ),
            FieldOption(
                "reliability",
                "Reliability",
                description="Error handling, edge cases, stability",
                icon="🛡️",
            ),
            FieldOption(
                "testability",
                "Testability",
                description="Test coverage, test quality, mocking",
                icon="🧪",
            ),
        ],
        validation=FieldValidation(required=required),
        category="quality",
    )


def create_team_size_field(
    id: str = "team_size",
    required: bool = False,
) -> FormField:
    """Create a team size input field."""
    return FormField(
        id=id,
        field_type=FieldType.SINGLE_SELECT,
        label="How large is your development team?",
        help_text="This helps us calibrate review thoroughness.",
        options=[
            FieldOption("solo", "Solo developer", description="Just me"),
            FieldOption("small", "Small team (2-5)", description="Close collaboration"),
            FieldOption("medium", "Medium team (6-15)", description="Multiple reviewers"),
            FieldOption("large", "Large team (16+)", description="Formal review process"),
        ],
        validation=FieldValidation(required=required),
        category="context",
    )


def create_automation_level_field(
    id: str = "automation_level",
    required: bool = True,
) -> FormField:
    """Create an automation preference field."""
    return FormField(
        id=id,
        field_type=FieldType.SINGLE_SELECT,
        label="How much automation do you want?",
        help_text="Higher automation means less human intervention required.",
        options=[
            FieldOption(
                "advisory",
                "Advisory Only",
                description="Suggestions for humans to review and apply",
                icon="💡",
            ),
            FieldOption(
                "semi_auto",
                "Semi-Automated",
                description="Auto-fix simple issues, flag complex ones",
                icon="⚙️",
                recommended=True,
            ),
            FieldOption(
                "fully_auto",
                "Fully Automated",
                description="Auto-fix everything possible, minimal human review",
                icon="🤖",
            ),
        ],
        validation=FieldValidation(required=required),
        category="preferences",
    )


def create_goal_text_field(
    id: str = "goal",
    required: bool = True,
) -> FormField:
    """Create the initial goal capture field."""
    return FormField(
        id=id,
        field_type=FieldType.TEXT_AREA,
        label="What do you want to accomplish?",
        help_text=(
            "Describe your goal in your own words. Be as specific as you like - "
            "we'll ask clarifying questions if needed."
        ),
        placeholder="e.g., I want to automate code reviews to catch security issues...",
        validation=FieldValidation(
            required=required,
            min_length=10,
            max_length=2000,
        ),
        category="goal",
    )


def create_additional_context_field(
    id: str = "additional_context",
    required: bool = False,
) -> FormField:
    """Create an optional additional context field."""
    return FormField(
        id=id,
        field_type=FieldType.TEXT_AREA,
        label="Anything else we should know?",
        help_text="Optional: Share any additional context, constraints, or preferences.",
        placeholder="e.g., We use a monorepo, have strict SLAs, prefer verbose output...",
        validation=FieldValidation(max_length=1000),
        category="context",
    )
