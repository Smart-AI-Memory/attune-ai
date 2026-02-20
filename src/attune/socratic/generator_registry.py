"""Agent templates and tool registry for the generator.

Provides AgentTemplate dataclass, TOOL_REGISTRY, and
AGENT_TEMPLATES for use by the AgentGenerator.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .blueprint import (
    AgentRole,
    AgentSpec,
    ToolCategory,
    ToolSpec,
)


@dataclass
class AgentTemplate:
    """Template for generating specialized agents.

    Templates provide pre-configured agent specifications that can be
    customized based on Socratic questioning results.
    """

    id: str
    name: str
    role: AgentRole
    base_goal: str
    base_backstory: str
    default_tools: list[str]
    quality_focus: list[str]
    languages: list[str]  # Empty = all languages
    model_tier: str = "capable"
    custom_instructions: list[str] = field(default_factory=list)

    def create_spec(
        self,
        customizations: dict[str, Any] | None = None,
    ) -> AgentSpec:
        """Create an AgentSpec from this template.

        Args:
            customizations: Override template defaults

        Returns:
            AgentSpec with customizations applied
        """
        customizations = customizations or {}

        # Build goal with customizations
        goal = customizations.get("goal", self.base_goal)
        if "goal_suffix" in customizations:
            goal = f"{goal} {customizations['goal_suffix']}"

        # Build backstory with customizations
        backstory = customizations.get("backstory", self.base_backstory)
        if "expertise" in customizations:
            backstory = f"{backstory} Specialized in: {', '.join(customizations['expertise'])}."

        # Merge languages
        languages = customizations.get("languages", self.languages)

        # Merge quality focus
        quality = list(self.quality_focus)
        if "quality_focus" in customizations:
            quality.extend(customizations["quality_focus"])
            quality = list(dict.fromkeys(quality))  # Dedupe preserving order

        # Build tools
        tools = self._build_tools(customizations.get("tools", []))

        return AgentSpec(
            id=customizations.get("id", self.id),
            name=customizations.get("name", self.name),
            role=self.role,
            goal=goal,
            backstory=backstory,
            tools=tools,
            quality_focus=quality,
            model_tier=customizations.get("model_tier", self.model_tier),
            custom_instructions=self.custom_instructions + customizations.get("instructions", []),
            languages=languages,
        )

    def _build_tools(self, additional_tools: list[str]) -> list[ToolSpec]:
        """Build tool specifications."""
        tools = []
        all_tool_ids = list(dict.fromkeys(self.default_tools + additional_tools))

        for tool_id in all_tool_ids:
            tool_spec = TOOL_REGISTRY.get(tool_id)
            if tool_spec:
                tools.append(tool_spec)

        return tools


# =============================================================================
# TOOL REGISTRY
# =============================================================================


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "grep_code": ToolSpec(
        id="grep_code",
        name="Code Search",
        category=ToolCategory.CODE_SEARCH,
        description="Search codebase for patterns using regex",
        parameters={
            "pattern": {"type": "string", "required": True},
            "file_glob": {"type": "string", "required": False},
            "case_sensitive": {"type": "boolean", "default": False},
        },
    ),
    "read_file": ToolSpec(
        id="read_file",
        name="Read File",
        category=ToolCategory.CODE_ANALYSIS,
        description="Read file contents",
        parameters={
            "path": {"type": "string", "required": True},
            "start_line": {"type": "integer", "required": False},
            "end_line": {"type": "integer", "required": False},
        },
    ),
    "analyze_ast": ToolSpec(
        id="analyze_ast",
        name="AST Analysis",
        category=ToolCategory.CODE_ANALYSIS,
        description="Parse and analyze code abstract syntax tree",
        parameters={
            "code": {"type": "string", "required": True},
            "language": {"type": "string", "required": True},
        },
    ),
    "security_scan": ToolSpec(
        id="security_scan",
        name="Security Scanner",
        category=ToolCategory.SECURITY,
        description="Run security vulnerability scanner",
        parameters={
            "path": {"type": "string", "required": True},
            "rules": {"type": "array", "required": False},
        },
        cost_tier="moderate",
    ),
    "run_linter": ToolSpec(
        id="run_linter",
        name="Run Linter",
        category=ToolCategory.LINTING,
        description="Run code linter and return issues",
        parameters={
            "path": {"type": "string", "required": True},
            "config": {"type": "string", "required": False},
        },
    ),
    "run_tests": ToolSpec(
        id="run_tests",
        name="Run Tests",
        category=ToolCategory.TESTING,
        description="Execute test suite and return results",
        parameters={
            "path": {"type": "string", "required": False},
            "coverage": {"type": "boolean", "default": True},
        },
        cost_tier="moderate",
    ),
    "edit_file": ToolSpec(
        id="edit_file",
        name="Edit File",
        category=ToolCategory.CODE_MODIFICATION,
        description="Make targeted edits to a file",
        parameters={
            "path": {"type": "string", "required": True},
            "old_text": {"type": "string", "required": True},
            "new_text": {"type": "string", "required": True},
        },
        is_mutating=True,
        requires_confirmation=True,
    ),
    "query_patterns": ToolSpec(
        id="query_patterns",
        name="Query Pattern Library",
        category=ToolCategory.KNOWLEDGE,
        description="Search learned patterns for similar issues",
        parameters={
            "query": {"type": "string", "required": True},
            "limit": {"type": "integer", "default": 5},
        },
    ),
    "complexity_analysis": ToolSpec(
        id="complexity_analysis",
        name="Complexity Analysis",
        category=ToolCategory.CODE_ANALYSIS,
        description="Calculate code complexity metrics",
        parameters={
            "path": {"type": "string", "required": True},
        },
    ),
}


# =============================================================================
# AGENT TEMPLATE REGISTRY
# =============================================================================


AGENT_TEMPLATES: dict[str, AgentTemplate] = {
    "security_reviewer": AgentTemplate(
        id="security_reviewer",
        name="Security Reviewer",
        role=AgentRole.AUDITOR,
        base_goal="Identify security vulnerabilities and recommend mitigations",
        base_backstory=(
            "Expert security analyst with deep knowledge of OWASP Top 10, "
            "secure coding practices, and common vulnerability patterns."
        ),
        default_tools=["grep_code", "read_file", "security_scan", "query_patterns"],
        quality_focus=["security"],
        languages=[],
        model_tier="capable",
        custom_instructions=[
            "Prioritize critical and high severity issues",
            "Provide specific code locations for each finding",
            "Include remediation recommendations",
        ],
    ),
    "code_quality_reviewer": AgentTemplate(
        id="code_quality_reviewer",
        name="Code Quality Reviewer",
        role=AgentRole.REVIEWER,
        base_goal="Assess code quality, maintainability, and adherence to best practices",
        base_backstory=(
            "Experienced code reviewer with expertise in clean code principles, "
            "design patterns, and maintainability best practices."
        ),
        default_tools=["grep_code", "read_file", "run_linter", "complexity_analysis"],
        quality_focus=["maintainability", "reliability"],
        languages=[],
        model_tier="capable",
    ),
    "performance_analyzer": AgentTemplate(
        id="performance_analyzer",
        name="Performance Analyzer",
        role=AgentRole.ANALYZER,
        base_goal="Identify performance bottlenecks and optimization opportunities",
        base_backstory=(
            "Performance optimization specialist with expertise in algorithmic "
            "complexity, memory management, and scalability patterns."
        ),
        default_tools=["grep_code", "read_file", "complexity_analysis", "analyze_ast"],
        quality_focus=["performance"],
        languages=[],
        model_tier="capable",
    ),
    "test_generator": AgentTemplate(
        id="test_generator",
        name="Test Generator",
        role=AgentRole.GENERATOR,
        base_goal="Generate comprehensive test cases for untested code",
        base_backstory=(
            "Testing expert skilled in unit testing, integration testing, "
            "and test-driven development methodologies."
        ),
        default_tools=["read_file", "analyze_ast", "run_tests", "edit_file"],
        quality_focus=["testability", "reliability"],
        languages=[],
        model_tier="capable",
        custom_instructions=[
            "Generate both happy path and edge case tests",
            "Follow the existing test patterns in the codebase",
            "Ensure tests are deterministic and isolated",
        ],
    ),
    "documentation_writer": AgentTemplate(
        id="documentation_writer",
        name="Documentation Writer",
        role=AgentRole.GENERATOR,
        base_goal="Generate clear, comprehensive documentation",
        base_backstory=(
            "Technical writer with expertise in API documentation, "
            "code comments, and developer guides."
        ),
        default_tools=["read_file", "analyze_ast", "grep_code"],
        quality_focus=["maintainability"],
        languages=[],
        model_tier="cheap",
    ),
    "style_enforcer": AgentTemplate(
        id="style_enforcer",
        name="Style Enforcer",
        role=AgentRole.REVIEWER,
        base_goal="Ensure code follows team style guidelines",
        base_backstory=(
            "Code style expert with knowledge of language-specific "
            "conventions and formatting standards."
        ),
        default_tools=["run_linter", "read_file"],
        quality_focus=["maintainability"],
        languages=[],
        model_tier="cheap",
    ),
    "result_synthesizer": AgentTemplate(
        id="result_synthesizer",
        name="Result Synthesizer",
        role=AgentRole.REPORTER,
        base_goal="Synthesize findings into clear, actionable reports",
        base_backstory=(
            "Technical communicator skilled at translating complex "
            "findings into understandable recommendations."
        ),
        default_tools=["query_patterns"],
        quality_focus=[],
        languages=[],
        model_tier="cheap",
    ),
}
