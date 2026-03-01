"""Output formatting patterns.

Patterns for structured workflow results.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .core import CodeSection, PatternCategory, WorkflowComplexity, WorkflowPattern


class ResultDataclassPattern(WorkflowPattern):
    """Structured output with dataclass.

    Use for: Type-safe, structured workflow results.
    Examples: health-check, release-prep.
    """

    id: str = "result-dataclass"
    name: str = "Result Dataclass"
    category: PatternCategory = PatternCategory.OUTPUT
    description: str = "Structured output format with dataclass"
    complexity: WorkflowComplexity = WorkflowComplexity.SIMPLE
    use_cases: list[str] = [
        "Type-safe results",
        "Structured output",
        "API integration",
    ]
    examples: list[str] = ["health-check", "release-prep"]
    risk_weight: float = 1.0

    def generate_code_sections(self, context: dict[str, Any]) -> list[CodeSection]:
        """Generate code for result dataclass."""
        context.get("workflow_name", "my-workflow")
        class_name = context.get("class_name", "MyWorkflow")
        result_class_name = f"{class_name}Result"

        # Get custom fields from context
        custom_fields = context.get("result_fields", [])

        # Generate custom fields code
        custom_fields_code = ""
        if custom_fields:
            for field in custom_fields:
                field_name = field.get("name", "custom_field")
                field_type = field.get("type", "Any")
                field_desc = field.get("description", "Custom field")
                custom_fields_code += f"    {field_name}: {field_type}  # {field_desc}\n"

        return [
            CodeSection(
                location="imports",
                code="from dataclasses import dataclass, field",
                priority=1,
            ),
            CodeSection(
                location="dataclasses",
                code=f'''@dataclass
class {result_class_name}:
    """Result from {class_name} execution."""

    success: bool
    {custom_fields_code or "    # Add custom fields here"}duration_seconds: float
    cost: float
    metadata: dict = field(default_factory=dict)''',
                priority=1,
            ),
            CodeSection(
                location="methods",
                code=f'''    def _create_result(
        self,
        success: bool,
        duration: float,
        cost: float,
        **kwargs: Any,
    ) -> {result_class_name}:
        """Create structured result.

        Args:
            success: Whether workflow succeeded
            duration: Execution duration in seconds
            cost: Total cost in USD
            **kwargs: Additional result fields

        Returns:
            {result_class_name} instance

        """
        return {result_class_name}(
            success=success,
            duration_seconds=duration,
            cost=cost,
            **kwargs,
        )''',
                priority=2,
            ),
        ]
