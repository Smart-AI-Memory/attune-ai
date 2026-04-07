"""Document generation configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DocGenConfig:
    """Configuration for the document generation pipeline.

    Attributes:
        doc_type: Type of documentation to generate
            (e.g., "api-reference", "guide", "readme").
        audience: Target audience (e.g., "developers",
            "beginners", "ops").
        model: Anthropic model ID for generation.
        max_outline_tokens: Max tokens for outline stage.
        max_write_tokens: Max tokens for write stage.
        max_review_tokens: Max tokens for review stage.
        sections_per_chunk: Sections per chunk for large docs.
        section_focus: Specific sections to generate (or all).
    """

    doc_type: str = "api-reference"
    audience: str = "developers"
    model: str = "claude-sonnet-4-20250514"
    max_outline_tokens: int = 1000
    max_write_tokens: int = 8000
    max_review_tokens: int = 8000
    sections_per_chunk: int = 4
    section_focus: list[str] = field(default_factory=list)
