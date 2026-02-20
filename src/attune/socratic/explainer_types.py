"""Types and constants for the Workflow Explainer.

Defines enums, the Explanation dataclass, and role description
mappings used by the explainer classes.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .blueprint import AgentRole

# =============================================================================
# EXPLANATION LEVELS
# =============================================================================


class AudienceLevel(Enum):
    """Target audience for explanations."""

    TECHNICAL = "technical"  # Developers, engineers
    BUSINESS = "business"  # Managers, stakeholders
    BEGINNER = "beginner"  # New users learning the system


class DetailLevel(Enum):
    """Level of detail in explanations."""

    BRIEF = "brief"  # One-liner summary
    STANDARD = "standard"  # Normal explanation
    DETAILED = "detailed"  # Full technical details


class OutputFormat(Enum):
    """Output format for explanations."""

    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class Explanation:
    """A generated explanation."""

    title: str
    summary: str
    sections: list[dict[str, str]]
    audience: AudienceLevel
    detail_level: DetailLevel

    def to_text(self) -> str:
        """Convert to plain text."""
        lines = [self.title, "=" * len(self.title), "", self.summary, ""]

        for section in self.sections:
            lines.append(section["heading"])
            lines.append("-" * len(section["heading"]))
            lines.append(section["content"])
            lines.append("")

        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Convert to markdown."""
        lines = [f"# {self.title}", "", self.summary, ""]

        for section in self.sections:
            lines.append(f"## {section['heading']}")
            lines.append("")
            lines.append(section["content"])
            lines.append("")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Convert to HTML."""
        html = [
            "<article class='workflow-explanation'>",
            f"<h1>{self.title}</h1>",
            f"<p class='summary'>{self.summary}</p>",
        ]

        for section in self.sections:
            html.append("<section>")
            html.append(f"<h2>{section['heading']}</h2>")
            html.append(f"<p>{section['content']}</p>")
            html.append("</section>")

        html.append("</article>")
        return "\n".join(html)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": self.sections,
            "audience": self.audience.value,
            "detail_level": self.detail_level.value,
        }


# =============================================================================
# ROLE DESCRIPTIONS
# =============================================================================


ROLE_DESCRIPTIONS = {
    AudienceLevel.TECHNICAL: {
        AgentRole.ANALYZER: "performs static analysis and data extraction",
        AgentRole.REVIEWER: "evaluates code quality and adherence to standards",
        AgentRole.AUDITOR: "conducts security and compliance audits",
        AgentRole.GENERATOR: "generates new code, tests, or documentation",
        AgentRole.FIXER: "automatically remediate identified issues",
        AgentRole.ORCHESTRATOR: "coordinates multi-agent workflows",
        AgentRole.RESEARCHER: "gathers information and context",
        AgentRole.VALIDATOR: "validates outputs against specifications",
    },
    AudienceLevel.BUSINESS: {
        AgentRole.ANALYZER: "examines the codebase to find patterns and issues",
        AgentRole.REVIEWER: "checks code quality and best practices",
        AgentRole.AUDITOR: "verifies security and compliance requirements",
        AgentRole.GENERATOR: "creates new content automatically",
        AgentRole.FIXER: "automatically corrects problems",
        AgentRole.ORCHESTRATOR: "manages the overall process",
        AgentRole.RESEARCHER: "collects relevant information",
        AgentRole.VALIDATOR: "ensures outputs meet requirements",
    },
    AudienceLevel.BEGINNER: {
        AgentRole.ANALYZER: "looks at your code to understand what it does",
        AgentRole.REVIEWER: "checks if your code follows good practices",
        AgentRole.AUDITOR: "makes sure your code is safe and follows the rules",
        AgentRole.GENERATOR: "writes new code or documentation for you",
        AgentRole.FIXER: "fixes problems it finds",
        AgentRole.ORCHESTRATOR: "manages all the other helpers",
        AgentRole.RESEARCHER: "finds information you need",
        AgentRole.VALIDATOR: "double-checks that everything is correct",
    },
}
