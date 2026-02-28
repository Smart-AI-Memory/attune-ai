"""Core workflow pattern definitions.

Defines Pydantic models for workflow patterns extracted from existing workflows.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PatternCategory(Enum):
    """Categories for workflow patterns."""

    STRUCTURAL = "structural"  # How workflow is organized
    TIER = "tier"  # Tier routing strategies
    INTEGRATION = "integration"  # External integrations
    OUTPUT = "output"  # Output formatting
    BEHAVIOR = "behavior"  # Behavioral patterns


class WorkflowComplexity(Enum):
    """Workflow complexity levels."""

    SIMPLE = "simple"  # Single stage, no conditions
    MODERATE = "moderate"  # Multiple stages, some conditions
    COMPLEX = "complex"  # Multiple stages, conditional routing, crews


@dataclass
class CodeSection:
    """A section of code to be generated."""

    location: str  # Where in the file (e.g., "imports", "class_body", "methods")
    code: str  # The code content
    priority: int = 0  # Higher priority sections are placed first


class WorkflowPattern(BaseModel):
    """Base model for workflow patterns."""

    id: str = Field(..., description="Unique pattern identifier")
    name: str = Field(..., description="Human-readable pattern name")
    category: PatternCategory = Field(..., description="Pattern category")
    description: str = Field(..., description="Pattern description")
    complexity: WorkflowComplexity = Field(..., description="Pattern complexity")
    use_cases: list[str] = Field(default_factory=list, description="When to use this pattern")
    examples: list[str] = Field(
        default_factory=list,
        description="Example workflows using this pattern",
    )
    conflicts_with: list[str] = Field(default_factory=list, description="Incompatible pattern IDs")
    requires: list[str] = Field(default_factory=list, description="Required pattern IDs")
    risk_weight: float = Field(
        default=1.0,
        ge=0.0,
        le=5.0,
        description="Risk factor for testing (1=low, 5=high)",
    )

    def generate_code_sections(self, context: dict[str, Any]) -> list[CodeSection]:
        """Generate code sections for this pattern.

        Args:
            context: Context dictionary with workflow metadata

        Returns:
            List of CodeSection objects to be merged

        """
        raise NotImplementedError("Subclasses must implement generate_code_sections")

    class Config:
        """Pydantic config."""

        use_enum_values = True
