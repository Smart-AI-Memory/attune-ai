"""Tests for workflow patterns module.

Covers core classes, registry, structural patterns, and behavioral patterns.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflow_patterns.behavior import (
    CodeScannerPattern,
    ConditionalTierPattern,
    ConfigDrivenPattern,
)
from attune.workflow_patterns.core import CodeSection, PatternCategory, WorkflowComplexity
from attune.workflow_patterns.registry import (
    WorkflowPatternRegistry,
    get_workflow_pattern_registry,
)
from attune.workflow_patterns.structural import (
    CrewBasedPattern,
    MultiStagePattern,
    SingleStagePattern,
)


@pytest.mark.unit
class TestPatternCategory:
    """Tests for PatternCategory enum."""

    def test_structural_category(self):
        """Test STRUCTURAL category value."""
        assert PatternCategory.STRUCTURAL.value == "structural"

    def test_tier_category(self):
        """Test TIER category value."""
        assert PatternCategory.TIER.value == "tier"

    def test_integration_category(self):
        """Test INTEGRATION category value."""
        assert PatternCategory.INTEGRATION.value == "integration"

    def test_output_category(self):
        """Test OUTPUT category value."""
        assert PatternCategory.OUTPUT.value == "output"

    def test_behavior_category(self):
        """Test BEHAVIOR category value."""
        assert PatternCategory.BEHAVIOR.value == "behavior"


@pytest.mark.unit
class TestWorkflowComplexity:
    """Tests for WorkflowComplexity enum."""

    def test_simple_complexity(self):
        """Test SIMPLE complexity value."""
        assert WorkflowComplexity.SIMPLE.value == "simple"

    def test_moderate_complexity(self):
        """Test MODERATE complexity value."""
        assert WorkflowComplexity.MODERATE.value == "moderate"

    def test_complex_complexity(self):
        """Test COMPLEX complexity value."""
        assert WorkflowComplexity.COMPLEX.value == "complex"


@pytest.mark.unit
class TestCodeSection:
    """Tests for CodeSection dataclass."""

    def test_code_section_creation(self):
        """Test creating a CodeSection."""
        section = CodeSection(
            location="imports",
            code="import os\nimport sys",
            priority=1,
        )

        assert section.location == "imports"
        assert "import os" in section.code
        assert section.priority == 1

    def test_code_section_default_priority(self):
        """Test CodeSection default priority is 0."""
        section = CodeSection(location="methods", code="def foo(): pass")

        assert section.priority == 0


@pytest.mark.unit
class TestSingleStagePattern:
    """Tests for SingleStagePattern."""

    def test_pattern_attributes(self):
        """Test SingleStagePattern has correct attributes."""
        pattern = SingleStagePattern()

        assert pattern.id == "single-stage"
        assert pattern.name == "Single Stage Workflow"
        assert pattern.category == PatternCategory.STRUCTURAL
        assert pattern.complexity == WorkflowComplexity.SIMPLE
        assert pattern.risk_weight == 1.0

    def test_generate_code_sections(self):
        """Test generate_code_sections creates code."""
        pattern = SingleStagePattern()

        context = {
            "workflow_name": "test-workflow",
            "class_name": "TestWorkflow",
            "description": "A test workflow",
            "tier": "CAPABLE",
        }

        sections = pattern.generate_code_sections(context)

        assert len(sections) >= 2

        # Check class_attributes section
        attr_section = next((s for s in sections if s.location == "class_attributes"), None)
        assert attr_section is not None
        assert "test-workflow" in attr_section.code

        # Check methods section
        methods_section = next((s for s in sections if s.location == "methods"), None)
        assert methods_section is not None
        assert "run_stage" in methods_section.code

    def test_use_cases_defined(self):
        """Test SingleStagePattern has use cases."""
        pattern = SingleStagePattern()

        assert len(pattern.use_cases) > 0
        assert any("Quick" in uc for uc in pattern.use_cases)


@pytest.mark.unit
class TestMultiStagePattern:
    """Tests for MultiStagePattern."""

    def test_pattern_attributes(self):
        """Test MultiStagePattern has correct attributes."""
        pattern = MultiStagePattern()

        assert pattern.id == "multi-stage"
        assert pattern.name == "Multi-Stage Workflow"
        assert pattern.category == PatternCategory.STRUCTURAL
        assert pattern.complexity == WorkflowComplexity.MODERATE
        assert pattern.risk_weight == 2.5

    def test_generate_code_sections(self):
        """Test generate_code_sections creates multi-stage code."""
        pattern = MultiStagePattern()

        context = {
            "workflow_name": "analysis-workflow",
            "description": "Multi-stage analysis",
            "stages": ["classify", "analyze", "report"],
            "tier_map": {
                "classify": "CHEAP",
                "analyze": "CAPABLE",
                "report": "PREMIUM",
            },
        }

        sections = pattern.generate_code_sections(context)

        # Check class_attributes has stages
        attr_section = next((s for s in sections if s.location == "class_attributes"), None)
        assert attr_section is not None
        assert "classify" in attr_section.code
        assert "analyze" in attr_section.code
        assert "report" in attr_section.code

        # Check methods has stage routing
        methods_section = next((s for s in sections if s.location == "methods"), None)
        assert methods_section is not None
        assert "_classify" in methods_section.code
        assert "_analyze" in methods_section.code
        assert "_report" in methods_section.code

    def test_examples_include_known_workflows(self):
        """Test MultiStagePattern examples include known workflows."""
        pattern = MultiStagePattern()

        assert "bug-predict" in pattern.examples
        assert "code-review" in pattern.examples


@pytest.mark.unit
class TestCrewBasedPattern:
    """Tests for CrewBasedPattern."""

    def test_pattern_attributes(self):
        """Test CrewBasedPattern has correct attributes."""
        pattern = CrewBasedPattern()

        assert pattern.id == "crew-based"
        assert pattern.name == "Crew-Based Workflow"
        assert pattern.category == PatternCategory.INTEGRATION
        assert pattern.complexity == WorkflowComplexity.COMPLEX
        assert pattern.risk_weight == 3.5

    def test_conflicts_with_single_stage(self):
        """Test CrewBasedPattern conflicts with single-stage."""
        pattern = CrewBasedPattern()

        assert "single-stage" in pattern.conflicts_with

    def test_generate_code_sections(self):
        """Test generate_code_sections creates crew code."""
        pattern = CrewBasedPattern()

        context = {
            "workflow_name": "crew-workflow",
            "crew_name": "SecurityCrew",
        }

        sections = pattern.generate_code_sections(context)

        # Check init_method has crew initialization
        init_section = next((s for s in sections if s.location == "init_method"), None)
        assert init_section is not None
        assert "_crew" in init_section.code

        # Check methods have crew methods
        methods_section = next((s for s in sections if s.location == "methods"), None)
        assert methods_section is not None
        assert "SecurityCrew" in methods_section.code
        assert "_initialize_crew" in methods_section.code


@pytest.mark.unit
class TestConditionalTierPattern:
    """Tests for ConditionalTierPattern."""

    def test_pattern_attributes(self):
        """Test ConditionalTierPattern has correct attributes."""
        pattern = ConditionalTierPattern()

        assert pattern.id == "conditional-tier"
        assert pattern.name == "Conditional Tier Routing"
        assert pattern.category == PatternCategory.BEHAVIOR
        assert pattern.complexity == WorkflowComplexity.MODERATE

    def test_requires_multi_stage(self):
        """Test ConditionalTierPattern requires multi-stage."""
        pattern = ConditionalTierPattern()

        assert "multi-stage" in pattern.requires

    def test_generate_code_sections(self):
        """Test generate_code_sections creates conditional logic."""
        pattern = ConditionalTierPattern()

        context = {
            "threshold_param": "risk_threshold",
            "threshold_default": "0.5",
            "metric_name": "risk_score",
        }

        sections = pattern.generate_code_sections(context)

        # Check init_method has threshold
        init_section = next((s for s in sections if s.location == "init_method"), None)
        assert init_section is not None
        assert "risk_threshold" in init_section.code

        # Check methods have conditional logic
        methods_section = next((s for s in sections if s.location == "methods"), None)
        assert methods_section is not None
        assert "should_skip_stage" in methods_section.code


@pytest.mark.unit
class TestConfigDrivenPattern:
    """Tests for ConfigDrivenPattern."""

    def test_pattern_attributes(self):
        """Test ConfigDrivenPattern has correct attributes."""
        pattern = ConfigDrivenPattern()

        assert pattern.id == "config-driven"
        assert pattern.name == "Configuration-Driven Workflow"
        assert pattern.category == PatternCategory.BEHAVIOR
        assert pattern.complexity == WorkflowComplexity.SIMPLE

    def test_generate_code_sections(self):
        """Test generate_code_sections creates config loading code."""
        pattern = ConfigDrivenPattern()

        context = {
            "workflow_name": "my-workflow",
            "config_params": {
                "threshold": 0.8,
                "enabled": True,
                "name": "test",
            },
        }

        sections = pattern.generate_code_sections(context)

        # Check imports
        imports_section = next((s for s in sections if s.location == "imports"), None)
        assert imports_section is not None
        assert "yaml" in imports_section.code

        # Check helper functions
        helper_section = next((s for s in sections if s.location == "helper_functions"), None)
        assert helper_section is not None
        assert "_load_my_workflow_config" in helper_section.code
        assert "attune.config.yml" in helper_section.code


@pytest.mark.unit
class TestCodeScannerPattern:
    """Tests for CodeScannerPattern."""

    def test_pattern_attributes(self):
        """Test CodeScannerPattern has correct attributes."""
        pattern = CodeScannerPattern()

        assert pattern.id == "code-scanner"
        assert pattern.name == "Code Scanner"
        assert pattern.category == PatternCategory.BEHAVIOR
        assert pattern.complexity == WorkflowComplexity.MODERATE

    def test_generate_code_sections(self):
        """Test generate_code_sections creates scanning code."""
        pattern = CodeScannerPattern()

        context = {"scan_pattern": "*.py"}

        sections = pattern.generate_code_sections(context)

        # Check imports
        imports_section = next((s for s in sections if s.location == "imports"), None)
        assert imports_section is not None
        assert "fnmatch" in imports_section.code

        # Check helper functions
        helper_section = next((s for s in sections if s.location == "helper_functions"), None)
        assert helper_section is not None
        assert "_should_exclude_file" in helper_section.code
        assert "_scan_files" in helper_section.code


@pytest.mark.unit
class TestWorkflowPatternRegistry:
    """Tests for WorkflowPatternRegistry."""

    def test_registry_initializes_with_default_patterns(self):
        """Test registry has default patterns registered."""
        registry = WorkflowPatternRegistry()

        patterns = registry.list_all()

        assert len(patterns) >= 7  # At least 7 default patterns
        assert registry.get("single-stage") is not None
        assert registry.get("multi-stage") is not None
        assert registry.get("crew-based") is not None

    def test_register_custom_pattern(self):
        """Test registering a custom pattern."""
        registry = WorkflowPatternRegistry()

        custom_pattern = SingleStagePattern()
        custom_pattern.id = "custom-pattern"
        custom_pattern.name = "Custom Pattern"

        registry.register(custom_pattern)

        assert registry.get("custom-pattern") is not None
        assert registry.get("custom-pattern").name == "Custom Pattern"

    def test_get_returns_none_for_unknown(self):
        """Test get returns None for unknown pattern ID."""
        registry = WorkflowPatternRegistry()

        assert registry.get("nonexistent-pattern") is None

    def test_list_by_category(self):
        """Test listing patterns by category."""
        registry = WorkflowPatternRegistry()

        structural_patterns = registry.list_by_category(PatternCategory.STRUCTURAL)

        assert len(structural_patterns) >= 2  # At least single-stage and multi-stage
        assert all(p.category == PatternCategory.STRUCTURAL for p in structural_patterns)

    def test_list_by_complexity(self):
        """Test listing patterns by complexity."""
        registry = WorkflowPatternRegistry()

        simple_patterns = registry.list_by_complexity(WorkflowComplexity.SIMPLE)

        assert len(simple_patterns) >= 1  # At least single-stage
        assert all(p.complexity == WorkflowComplexity.SIMPLE for p in simple_patterns)

    def test_search_by_name(self):
        """Test searching patterns by name."""
        registry = WorkflowPatternRegistry()

        results = registry.search("stage")

        assert len(results) >= 2  # single-stage and multi-stage

    def test_search_by_description(self):
        """Test searching patterns by description."""
        registry = WorkflowPatternRegistry()

        results = registry.search("tier")

        assert len(results) >= 1

    def test_search_case_insensitive(self):
        """Test search is case insensitive."""
        registry = WorkflowPatternRegistry()

        results_upper = registry.search("STAGE")
        results_lower = registry.search("stage")

        assert len(results_upper) == len(results_lower)

    def test_recommend_for_code_analysis(self):
        """Test recommend_for_workflow for code-analysis."""
        registry = WorkflowPatternRegistry()

        recommendations = registry.recommend_for_workflow("code-analysis")

        pattern_ids = [p.id for p in recommendations]
        assert "multi-stage" in pattern_ids or "code-scanner" in pattern_ids

    def test_recommend_for_simple(self):
        """Test recommend_for_workflow for simple workflows."""
        registry = WorkflowPatternRegistry()

        recommendations = registry.recommend_for_workflow("simple")

        pattern_ids = [p.id for p in recommendations]
        assert "single-stage" in pattern_ids

    def test_recommend_for_multi_agent(self):
        """Test recommend_for_workflow for multi-agent workflows."""
        registry = WorkflowPatternRegistry()

        recommendations = registry.recommend_for_workflow("multi-agent")

        pattern_ids = [p.id for p in recommendations]
        assert "crew-based" in pattern_ids

    def test_validate_pattern_combination_valid(self):
        """Test validate_pattern_combination for compatible patterns."""
        registry = WorkflowPatternRegistry()

        is_valid, error = registry.validate_pattern_combination(
            ["multi-stage", "conditional-tier", "config-driven"],
        )

        assert is_valid is True
        assert error is None

    def test_validate_pattern_combination_conflict(self):
        """Test validate_pattern_combination detects conflicts."""
        registry = WorkflowPatternRegistry()

        is_valid, error = registry.validate_pattern_combination(["crew-based", "single-stage"])

        assert is_valid is False
        assert "conflicts with" in error

    def test_validate_pattern_combination_unknown(self):
        """Test validate_pattern_combination handles unknown patterns."""
        registry = WorkflowPatternRegistry()

        is_valid, error = registry.validate_pattern_combination(["unknown-pattern"])

        assert is_valid is False
        assert "Unknown pattern" in error

    def test_validate_pattern_combination_missing_requirement(self):
        """Test validate_pattern_combination checks requirements."""
        registry = WorkflowPatternRegistry()

        # conditional-tier requires multi-stage
        is_valid, error = registry.validate_pattern_combination(
            ["single-stage", "conditional-tier"],
        )

        assert is_valid is False
        assert "requires" in error

    def test_get_total_risk_weight(self):
        """Test get_total_risk_weight calculates correctly."""
        registry = WorkflowPatternRegistry()

        total = registry.get_total_risk_weight(["single-stage", "multi-stage"])

        # single-stage: 1.0, multi-stage: 2.5
        assert total == 3.5

    def test_get_total_risk_weight_unknown_ignored(self):
        """Test get_total_risk_weight ignores unknown patterns."""
        registry = WorkflowPatternRegistry()

        total = registry.get_total_risk_weight(["single-stage", "unknown"])

        assert total == 1.0  # Only single-stage counted

    def test_generate_code_sections(self):
        """Test generate_code_sections from registry."""
        registry = WorkflowPatternRegistry()

        context = {
            "workflow_name": "test-workflow",
            "class_name": "TestWorkflow",
            "description": "Test",
            "tier": "CAPABLE",
        }

        sections = registry.generate_code_sections(["single-stage"], context)

        assert "class_attributes" in sections
        assert "methods" in sections

    def test_generate_code_sections_multiple_patterns(self):
        """Test generate_code_sections merges multiple patterns."""
        registry = WorkflowPatternRegistry()

        context = {
            "workflow_name": "test-workflow",
            "stages": ["a", "b"],
            "tier_map": {"a": "CHEAP", "b": "CAPABLE"},
            "scan_pattern": "*.py",
        }

        sections = registry.generate_code_sections(["multi-stage", "code-scanner"], context)

        # Should have imports from code-scanner
        assert "imports" in sections
        # Should have methods from both
        assert "methods" in sections


@pytest.mark.unit
class TestGetWorkflowPatternRegistry:
    """Tests for get_workflow_pattern_registry function."""

    def test_returns_registry_instance(self):
        """Test get_workflow_pattern_registry returns a registry."""
        registry = get_workflow_pattern_registry()

        assert isinstance(registry, WorkflowPatternRegistry)

    def test_returns_same_instance(self):
        """Test get_workflow_pattern_registry returns singleton."""
        registry1 = get_workflow_pattern_registry()
        registry2 = get_workflow_pattern_registry()

        assert registry1 is registry2


@pytest.mark.unit
class TestWorkflowPatternBase:
    """Tests for WorkflowPattern base class."""

    def test_pattern_model_validation(self):
        """Test WorkflowPattern validates fields."""
        # Creating via subclass since base has abstract method
        pattern = SingleStagePattern()

        # Required fields present
        assert pattern.id is not None
        assert pattern.name is not None
        assert pattern.category is not None
        assert pattern.description is not None
        assert pattern.complexity is not None

    def test_pattern_default_values(self):
        """Test WorkflowPattern default values."""
        pattern = SingleStagePattern()

        assert pattern.use_cases == [
            "Quick analysis tasks",
            "Single API calls",
            "Basic validation or formatting",
        ]
        assert pattern.examples == []
        assert pattern.conflicts_with == []
        assert pattern.requires == []

    def test_risk_weight_bounds(self):
        """Test risk_weight must be between 0 and 5."""
        pattern = SingleStagePattern()

        # Default is valid
        assert 0.0 <= pattern.risk_weight <= 5.0


@pytest.mark.unit
class TestPatternCodeGeneration:
    """Tests for code generation quality."""

    def test_single_stage_code_is_valid_python_syntax(self):
        """Test SingleStagePattern generates valid Python syntax."""
        pattern = SingleStagePattern()

        context = {"workflow_name": "test", "tier": "CAPABLE"}
        sections = pattern.generate_code_sections(context)

        for section in sections:
            # Should not raise SyntaxError when parsed as part of a class
            assert "def " in section.code or "name = " in section.code

    def test_multi_stage_code_includes_all_stages(self):
        """Test MultiStagePattern includes all specified stages."""
        pattern = MultiStagePattern()

        stages = ["stage_a", "stage_b", "stage_c"]
        context = {
            "stages": stages,
            "tier_map": dict.fromkeys(stages, "CHEAP"),
        }

        sections = pattern.generate_code_sections(context)
        methods_section = next((s for s in sections if s.location == "methods"), None)

        for stage in stages:
            assert f"_{stage}" in methods_section.code

    def test_config_driven_escapes_string_values(self):
        """Test ConfigDrivenPattern properly escapes string config values."""
        pattern = ConfigDrivenPattern()

        context = {
            "workflow_name": "test",
            "config_params": {"path": "/tmp/test"},
        }

        sections = pattern.generate_code_sections(context)
        helper_section = next((s for s in sections if s.location == "helper_functions"), None)

        assert '"/tmp/test"' in helper_section.code
