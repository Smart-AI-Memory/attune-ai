"""Workflow Pattern Registry.

Manages workflow patterns and provides pattern recommendation.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from typing import Any

from .behavior import CodeScannerPattern, ConditionalTierPattern, ConfigDrivenPattern
from .core import PatternCategory, WorkflowComplexity, WorkflowPattern
from .output import ResultDataclassPattern
from .structural import MultiStagePattern, SingleStagePattern


class WorkflowPatternRegistry:
    """Registry for workflow patterns."""

    def __init__(self):
        """Initialize pattern registry."""
        self._patterns: dict[str, WorkflowPattern] = {}
        self._register_default_patterns()

    def _register_default_patterns(self) -> None:
        """Register all default patterns."""
        patterns = [
            # Structural
            SingleStagePattern(),
            MultiStagePattern(),
            # Behavioral
            ConditionalTierPattern(),
            ConfigDrivenPattern(),
            CodeScannerPattern(),
            # Output
            ResultDataclassPattern(),
        ]

        for pattern in patterns:
            self._patterns[pattern.id] = pattern

    def register(self, pattern: WorkflowPattern) -> None:
        """Register a new pattern.

        Args:
            pattern: Pattern to register

        """
        self._patterns[pattern.id] = pattern

    def get(self, pattern_id: str) -> WorkflowPattern | None:
        """Get pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            WorkflowPattern or None if not found

        """
        return self._patterns.get(pattern_id)

    def list_all(self) -> list[WorkflowPattern]:
        """List all registered patterns.

        Returns:
            List of all patterns

        """
        return list(self._patterns.values())

    def list_by_category(self, category: PatternCategory) -> list[WorkflowPattern]:
        """List patterns by category.

        Args:
            category: Pattern category

        Returns:
            List of patterns in category

        """
        return [p for p in self._patterns.values() if p.category == category]

    def list_by_complexity(self, complexity: WorkflowComplexity) -> list[WorkflowPattern]:
        """List patterns by complexity.

        Args:
            complexity: Complexity level

        Returns:
            List of patterns with specified complexity

        """
        return [p for p in self._patterns.values() if p.complexity == complexity]

    def search(self, query: str) -> list[WorkflowPattern]:
        """Search patterns by name or description.

        Args:
            query: Search query

        Returns:
            List of matching patterns

        """
        query_lower = query.lower()
        results = []

        for pattern in self._patterns.values():
            if (
                query_lower in pattern.name.lower()
                or query_lower in pattern.description.lower()
                or any(query_lower in uc.lower() for uc in pattern.use_cases)
            ):
                results.append(pattern)

        return results

    def recommend_for_workflow(
        self,
        workflow_type: str,
        complexity: WorkflowComplexity | None = None,
    ) -> list[WorkflowPattern]:
        """Recommend patterns for a workflow type.

        Args:
            workflow_type: Type of workflow (e.g., "code-analysis", "multi-agent")
            complexity: Desired complexity level

        Returns:
            List of recommended patterns

        """
        recommendations = []

        # Type-based recommendations
        type_map = {
            "code-analysis": ["multi-stage", "code-scanner", "conditional-tier"],
            "simple": ["single-stage"],
            "multi-agent": ["crew-based", "result-dataclass"],
            "configurable": ["config-driven", "multi-stage"],
            "cost-optimized": ["conditional-tier", "multi-stage"],
        }

        pattern_ids = type_map.get(workflow_type.lower(), [])

        # Get patterns
        for pattern_id in pattern_ids:
            pattern = self.get(pattern_id)
            if pattern:
                if complexity is None or pattern.complexity == complexity:
                    recommendations.append(pattern)

        # Always include progress tracking and telemetry (built-in)
        # These are inherited from BaseWorkflow

        return recommendations

    def validate_pattern_combination(self, pattern_ids: list[str]) -> tuple[bool, str | None]:
        """Validate that pattern IDs can be used together.

        Args:
            pattern_ids: List of pattern IDs to validate

        Returns:
            Tuple of (is_valid, error_message)

        """
        patterns = []
        for pattern_id in pattern_ids:
            pattern = self.get(pattern_id)
            if not pattern:
                return False, f"Unknown pattern: {pattern_id}"
            patterns.append(pattern)

        # Check for conflicts
        for pattern in patterns:
            for other_pattern in patterns:
                if other_pattern.id in pattern.conflicts_with:
                    return False, f"Conflict: {pattern.id} conflicts with {other_pattern.id}"

        # Check for missing requirements
        for pattern in patterns:
            for required_id in pattern.requires:
                if required_id not in pattern_ids:
                    return False, f"{pattern.id} requires {required_id}"

        return True, None

    def get_total_risk_weight(self, pattern_ids: list[str]) -> float:
        """Calculate total risk weight for pattern combination.

        Args:
            pattern_ids: List of pattern IDs

        Returns:
            Total risk weight

        """
        total = 0.0
        for pattern_id in pattern_ids:
            pattern = self.get(pattern_id)
            if pattern:
                total += pattern.risk_weight
        return total

    def generate_code_sections(
        self,
        pattern_ids: list[str],
        context: dict[str, Any],
    ) -> dict[str, list[Any]]:
        """Generate all code sections from patterns.

        Args:
            pattern_ids: List of pattern IDs to use
            context: Context dictionary for code generation

        Returns:
            Dict mapping location to list of CodeSection objects

        """
        from collections import defaultdict

        sections_by_location = defaultdict(list)

        for pattern_id in pattern_ids:
            pattern = self.get(pattern_id)
            if pattern:
                sections = pattern.generate_code_sections(context)
                for section in sections:
                    sections_by_location[section.location].append(section)

        # Sort sections by priority within each location
        for location in sections_by_location:
            sections_by_location[location].sort(key=lambda s: -s.priority)

        return dict(sections_by_location)


# Global registry instance
_registry: WorkflowPatternRegistry | None = None


def get_workflow_pattern_registry() -> WorkflowPatternRegistry:
    """Get the global workflow pattern registry.

    Returns:
        WorkflowPatternRegistry instance

    """
    global _registry
    if _registry is None:
        _registry = WorkflowPatternRegistry()
    return _registry
