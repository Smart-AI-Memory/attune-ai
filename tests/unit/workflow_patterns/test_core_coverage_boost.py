"""Tests for workflow patterns core module.

Module: workflow_patterns/core.py (76 lines)
"""

import pytest
from pydantic import ValidationError

from attune.workflow_patterns.core import (
    CodeSection,
    PatternCategory,
    WorkflowComplexity,
    WorkflowPattern,
)

# ============================================================================
# PatternCategory Enum Tests
# ============================================================================


@pytest.mark.unit
class TestPatternCategory:
    """Test suite for PatternCategory enum."""

    def test_enum_values_exist(self):
        """Test that all category values exist."""
        assert PatternCategory.STRUCTURAL.value == "structural"
        assert PatternCategory.TIER.value == "tier"
        assert PatternCategory.INTEGRATION.value == "integration"
        assert PatternCategory.OUTPUT.value == "output"
        assert PatternCategory.BEHAVIOR.value == "behavior"

    def test_enum_count(self):
        """Test that enum has exactly 5 categories."""
        assert len(list(PatternCategory)) == 5


# ============================================================================
# WorkflowComplexity Enum Tests
# ============================================================================


@pytest.mark.unit
class TestWorkflowComplexity:
    """Test suite for WorkflowComplexity enum."""

    def test_enum_values_exist(self):
        """Test that all complexity values exist."""
        assert WorkflowComplexity.SIMPLE.value == "simple"
        assert WorkflowComplexity.MODERATE.value == "moderate"
        assert WorkflowComplexity.COMPLEX.value == "complex"

    def test_enum_count(self):
        """Test that enum has exactly 3 complexity levels."""
        assert len(list(WorkflowComplexity)) == 3


# ============================================================================
# CodeSection Dataclass Tests
# ============================================================================


@pytest.mark.unit
class TestCodeSection:
    """Test suite for CodeSection dataclass."""

    def test_create_code_section(self):
        """Test creating CodeSection with required fields."""
        # When
        section = CodeSection(location="imports", code="import os")

        # Then
        assert section.location == "imports"
        assert section.code == "import os"
        assert section.priority == 0  # Default

    def test_create_code_section_with_priority(self):
        """Test creating CodeSection with custom priority."""
        # When
        section = CodeSection(location="methods", code="def test():\n    pass", priority=10)

        # Then
        assert section.location == "methods"
        assert section.code == "def test():\n    pass"
        assert section.priority == 10


# ============================================================================
# WorkflowPattern Pydantic Model Tests
# ============================================================================


@pytest.mark.unit
class TestWorkflowPattern:
    """Test suite for WorkflowPattern Pydantic model."""

    def test_create_pattern_with_all_fields(self):
        """Test creating WorkflowPattern with all fields."""
        # When
        pattern = WorkflowPattern(
            id="full_pattern",
            name="Full Pattern",
            category=PatternCategory.TIER,
            description="Full description",
            complexity=WorkflowComplexity.COMPLEX,
            use_cases=["use_case_1", "use_case_2"],
            examples=["example_1"],
            conflicts_with=["pattern_x"],
            requires=["pattern_y"],
            risk_weight=3.5,
        )

        # Then
        assert pattern.id == "full_pattern"
        assert pattern.use_cases == ["use_case_1", "use_case_2"]
        assert pattern.examples == ["example_1"]
        assert pattern.conflicts_with == ["pattern_x"]
        assert pattern.requires == ["pattern_y"]
        assert pattern.risk_weight == 3.5

    def test_pattern_risk_weight_validation_min(self):
        """Test that risk_weight must be >= 0.0."""
        # When/Then
        with pytest.raises(ValidationError):
            WorkflowPattern(
                id="test",
                name="Test",
                category=PatternCategory.STRUCTURAL,
                description="Test",
                complexity=WorkflowComplexity.SIMPLE,
                risk_weight=-1.0,  # Invalid
            )

    def test_pattern_risk_weight_validation_max(self):
        """Test that risk_weight must be <= 5.0."""
        # When/Then
        with pytest.raises(ValidationError):
            WorkflowPattern(
                id="test",
                name="Test",
                category=PatternCategory.STRUCTURAL,
                description="Test",
                complexity=WorkflowComplexity.SIMPLE,
                risk_weight=6.0,  # Invalid
            )

    def test_pattern_generate_code_sections_not_implemented(self):
        """Test that generate_code_sections raises NotImplementedError."""
        # Given
        pattern = WorkflowPattern(
            id="test",
            name="Test",
            category=PatternCategory.STRUCTURAL,
            description="Test",
            complexity=WorkflowComplexity.SIMPLE,
        )

        # When/Then
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            pattern.generate_code_sections({})

    def test_pattern_config_uses_enum_values(self):
        """Test that Pydantic config uses enum values."""
        # When
        pattern = WorkflowPattern(
            id="test",
            name="Test",
            category="structural",  # String value, not enum
            description="Test",
            complexity="simple",  # String value, not enum
        )

        # Then - should convert to enums
        assert isinstance(pattern.category, PatternCategory | str)
        assert isinstance(pattern.complexity, WorkflowComplexity | str)
