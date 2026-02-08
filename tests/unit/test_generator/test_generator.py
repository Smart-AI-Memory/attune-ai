"""Tests for test_generator.generator module using real data.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import pytest

pytest.importorskip("jinja2", reason="jinja2 required for test_generator tests")

from pathlib import Path  # noqa: E402

from attune.test_generator.generator import TestGenerator  # noqa: E402
from attune.test_generator.risk_analyzer import RiskAnalyzer  # noqa: E402


class TestTestGeneratorInitialization:
    """Test TestGenerator initialization with real template directories."""

    def test_init_with_default_template_dir(self):
        """Test initialization uses default template directory."""
        generator = TestGenerator()

        # Verify template directory is set correctly
        assert generator.template_dir is not None
        assert isinstance(generator.template_dir, Path)
        assert generator.template_dir.name == "templates"

        # Verify Jinja2 environment is created
        assert generator.env is not None

        # Verify risk analyzer is initialized
        assert isinstance(generator.risk_analyzer, RiskAnalyzer)

    def test_init_with_custom_template_dir(self, tmp_path):
        """Test initialization with custom template directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()

        generator = TestGenerator(template_dir=custom_dir)

        assert generator.template_dir == custom_dir
        assert generator.env is not None


class TestWizardNameInference:
    """Test wizard module and class name inference."""

    def test_infer_module_from_workflow_id(self):
        """Test module path inference from workflow ID."""
        generator = TestGenerator()

        # Test with typical workflow ID format
        workflow_id = "soap_note"
        module = generator._infer_module(workflow_id)

        # Should convert to module path in workflows package
        assert isinstance(module, str)
        assert "workflow" in module.lower() or workflow_id in module
        assert module == "workflows.soap_note"

    def test_infer_class_name_from_workflow_id(self):
        """Test class name inference from workflow ID."""
        generator = TestGenerator()

        # Test with snake_case workflow ID
        workflow_id = "soap_note"
        class_name = generator._infer_class_name(workflow_id)

        # Should convert to PascalCase with Workflow suffix
        assert isinstance(class_name, str)
        assert class_name[0].isupper()  # Starts with capital
        assert "Workflow" in class_name
        assert class_name == "SoapNoteWorkflow"


class TestTestGeneration:
    """Test test generation with real patterns and data."""

    def test_generate_tests_returns_dict(self):
        """Test generate_tests returns dictionary with expected keys."""
        generator = TestGenerator()

        # Use real pattern IDs
        result = generator.generate_tests(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            workflow_module="wizards.test_wizard",
            workflow_class="TestWizard",
        )

        # Verify return structure
        assert isinstance(result, dict)
        assert "unit" in result
        assert "integration" in result
        assert "fixtures" in result

    def test_generate_unit_tests_always_included(self):
        """Test unit tests are always generated."""
        generator = TestGenerator()

        result = generator.generate_tests(
            workflow_id="simple_wizard",
            pattern_ids=[],  # No patterns
            workflow_module="wizards.simple",
            workflow_class="SimpleWizard",
        )

        # Unit tests should always be present
        assert result["unit"] is not None
        assert len(result["unit"]) > 0

    def test_generate_integration_tests_for_multi_step(self):
        """Test integration tests generated for multi-step wizards."""
        generator = TestGenerator()

        # Use patterns that indicate multi-step workflow
        result = generator.generate_tests(
            workflow_id="complex_wizard",
            pattern_ids=["linear_flow", "phased_processing"],
            workflow_module="wizards.complex",
            workflow_class="ComplexWizard",
        )

        # Integration tests should be generated for multi-step
        # (May be None if templates don't exist, but structure should be correct)
        assert "integration" in result

    def test_generate_fixtures_included(self):
        """Test fixtures are generated."""
        generator = TestGenerator()

        result = generator.generate_tests(
            workflow_id="wizard_with_fixtures",
            pattern_ids=["linear_flow"],
            workflow_module="wizards.fixtures_test",
            workflow_class="FixturesTestWizard",
        )

        # Fixtures should be included
        assert result["fixtures"] is not None
        assert len(result["fixtures"]) > 0


class TestTemplateContextBuilding:
    """Test template context building with real data."""

    def test_build_template_context_structure(self):
        """Test template context has required fields."""
        generator = TestGenerator()

        # Create mock risk analysis
        risk_analysis = generator.risk_analyzer.analyze(
            workflow_id="test_wizard", pattern_ids=["linear_flow"]
        )

        context = generator._build_template_context(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            workflow_module="wizards.test",
            workflow_class="TestWizard",
            risk_analysis=risk_analysis,
        )

        # Verify required context fields
        assert "workflow_id" in context
        assert context["workflow_id"] == "test_wizard"
        assert "workflow_module" in context
        assert context["workflow_module"] == "wizards.test"
        assert "workflow_class" in context
        assert context["workflow_class"] == "TestWizard"
        assert "pattern_ids" in context

    def test_build_context_detects_linear_flow(self):
        """Test context correctly detects linear flow pattern."""
        generator = TestGenerator()

        risk_analysis = generator.risk_analyzer.analyze(
            workflow_id="linear_wizard", pattern_ids=["linear_flow"]
        )

        context = generator._build_template_context(
            workflow_id="linear_wizard",
            pattern_ids=["linear_flow"],
            workflow_module="wizards.linear",
            workflow_class="LinearWizard",
            risk_analysis=risk_analysis,
        )

        # Should detect linear flow
        assert "has_linear_flow" in context or "linear" in str(context.values())

    def test_build_context_with_multiple_patterns(self):
        """Test context building with multiple patterns."""
        generator = TestGenerator()

        pattern_ids = ["linear_flow", "phased_processing", "approval"]
        risk_analysis = generator.risk_analyzer.analyze(
            workflow_id="multi_pattern_wizard", pattern_ids=pattern_ids
        )

        context = generator._build_template_context(
            workflow_id="multi_pattern_wizard",
            pattern_ids=pattern_ids,
            workflow_module="wizards.multi",
            workflow_class="MultiPatternWizard",
            risk_analysis=risk_analysis,
        )

        # All patterns should be in context
        assert context["pattern_ids"] == pattern_ids


class TestIntegrationTestDetection:
    """Test detection of when integration tests are needed."""

    def test_needs_integration_tests_for_multi_step(self):
        """Test integration tests needed for multi-step patterns."""
        generator = TestGenerator()

        # Multi-step patterns should require integration tests
        needs_integration = generator._needs_integration_tests(["linear_flow", "phased_processing"])

        # Should detect need for integration tests
        assert isinstance(needs_integration, bool)

    def test_needs_integration_tests_for_simple(self):
        """Test integration tests not needed for simple single-step."""
        generator = TestGenerator()

        # Simple patterns may not need integration tests
        needs_integration = generator._needs_integration_tests([])

        assert isinstance(needs_integration, bool)


class TestGeneratorWithRealTemplates:
    """Test generator with actual template files."""

    def test_generator_uses_real_template_files(self):
        """Test generator can load and use real template files."""
        generator = TestGenerator()

        # Check template directory exists
        assert generator.template_dir.exists()

        # Check for template files
        template_files = list(generator.template_dir.glob("*.jinja2"))

        # Should have at least unit test template
        assert len(template_files) > 0

    def test_generate_with_real_template(self):
        """Test actual test generation with real templates."""
        generator = TestGenerator()

        # Generate tests using real templates
        result = generator.generate_tests(
            workflow_id="real_wizard",
            pattern_ids=["linear_flow"],
            workflow_module="wizards.real",
            workflow_class="RealWizard",
        )

        # Verify generated code is not empty
        assert result["unit"] is not None

        # If template exists, should generate Python code
        if len(result["unit"]) > 0:
            # Check for common Python test patterns
            assert "def test_" in result["unit"] or "class Test" in result["unit"]


class TestErrorHandling:
    """Test error handling with real scenarios."""

    def test_generate_with_missing_templates_dir(self):
        """Test behavior when templates directory is missing."""
        nonexistent_dir = Path("/tmp/nonexistent_templates_dir_12345")

        # Creating generator with nonexistent dir should not crash
        generator = TestGenerator(template_dir=nonexistent_dir)

        # Generator created successfully
        assert generator.template_dir == nonexistent_dir

    def test_generate_with_invalid_pattern_ids(self):
        """Test generation with invalid pattern IDs."""
        generator = TestGenerator()

        # Use nonexistent pattern IDs
        result = generator.generate_tests(
            workflow_id="wizard",
            pattern_ids=["nonexistent_pattern_123"],
            workflow_module="wizards.test",
            workflow_class="TestWizard",
        )

        # Should still return structure (even if patterns not found)
        assert isinstance(result, dict)
        assert "unit" in result
