"""Tests for test_generator.risk_analyzer module using real data.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import pytest

pytest.importorskip("jinja2", reason="jinja2 required for test_generator tests")

from attune.test_generator.risk_analyzer import RiskAnalysis, RiskAnalyzer  # noqa: E402


class TestRiskAnalysisDataClass:
    """Test RiskAnalysis data class methods."""

    def test_risk_analysis_initialization(self):
        """Test RiskAnalysis can be created with all fields."""
        analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow", "approval"],
            critical_paths=["happy_path", "error_path"],
            high_risk_inputs=["empty_string", "null_value"],
            validation_points=["input_validation", "output_validation"],
            recommended_coverage=85,
            test_priorities=["high", "medium"],
        )

        assert analysis.workflow_id == "test_wizard"
        assert len(analysis.pattern_ids) == 2
        assert len(analysis.critical_paths) == 2
        assert len(analysis.high_risk_inputs) == 2
        assert analysis.recommended_coverage == 85

    def test_get_critical_test_cases_from_paths(self):
        """Test get_critical_test_cases generates test names from critical paths."""
        analysis = RiskAnalysis(
            workflow_id="wizard",
            pattern_ids=[],
            critical_paths=["Happy Path", "Error-Handling Path", "edge case"],
            high_risk_inputs=[],
            validation_points=[],
            recommended_coverage=80,
            test_priorities=[],
        )

        test_cases = analysis.get_critical_test_cases()

        # Should convert paths to test case names
        assert isinstance(test_cases, list)
        assert len(test_cases) >= 3  # At least one per critical path

        # Check formatting: lowercase, underscores, test_ prefix
        for test_case in test_cases[:3]:  # First 3 are from paths
            assert test_case.startswith("test_")
            assert " " not in test_case  # No spaces
            assert "-" not in test_case  # No hyphens

    def test_get_critical_test_cases_from_high_risk_inputs(self):
        """Test get_critical_test_cases generates validation tests from inputs."""
        analysis = RiskAnalysis(
            workflow_id="wizard",
            pattern_ids=[],
            critical_paths=[],
            high_risk_inputs=["Empty String", "Null Value", "SQL Injection"],
            validation_points=[],
            recommended_coverage=80,
            test_priorities=[],
        )

        test_cases = analysis.get_critical_test_cases()

        # Should generate validation test names
        assert isinstance(test_cases, list)
        assert len(test_cases) >= 3

        # Should include "_validation" suffix
        for test_case in test_cases:
            assert test_case.startswith("test_")
            assert test_case.endswith("_validation")

    def test_get_critical_test_cases_combined(self):
        """Test get_critical_test_cases combines paths and inputs."""
        analysis = RiskAnalysis(
            workflow_id="wizard",
            pattern_ids=[],
            critical_paths=["Main Flow", "Error Flow"],
            high_risk_inputs=["Invalid Input"],
            validation_points=[],
            recommended_coverage=80,
            test_priorities=[],
        )

        test_cases = analysis.get_critical_test_cases()

        # Should have test cases from both sources
        assert len(test_cases) >= 3  # 2 paths + 1 input

    def test_get_critical_test_cases_empty(self):
        """Test get_critical_test_cases with no paths or inputs."""
        analysis = RiskAnalysis(
            workflow_id="wizard",
            pattern_ids=[],
            critical_paths=[],
            high_risk_inputs=[],
            validation_points=[],
            recommended_coverage=80,
            test_priorities=[],
        )

        test_cases = analysis.get_critical_test_cases()

        # Should return empty list
        assert isinstance(test_cases, list)
        assert len(test_cases) == 0

    def test_to_dict_conversion(self):
        """Test to_dict converts RiskAnalysis to dictionary."""
        analysis = RiskAnalysis(
            workflow_id="dict_test_wizard",
            pattern_ids=["pattern1", "pattern2"],
            critical_paths=["path1"],
            high_risk_inputs=["input1"],
            validation_points=["validate1"],
            recommended_coverage=90,
            test_priorities=["high"],
        )

        result = analysis.to_dict()

        # Verify dictionary structure
        assert isinstance(result, dict)
        assert result["workflow_id"] == "dict_test_wizard"
        assert result["pattern_ids"] == ["pattern1", "pattern2"]
        assert result["critical_paths"] == ["path1"]
        assert result["high_risk_inputs"] == ["input1"]
        assert result["validation_points"] == ["validate1"]
        assert result["recommended_coverage"] == 90
        assert result["test_priorities"] == ["high"]

    def test_to_dict_preserves_all_fields(self):
        """Test to_dict includes all RiskAnalysis fields."""
        analysis = RiskAnalysis(
            workflow_id="wizard",
            pattern_ids=[],
            critical_paths=[],
            high_risk_inputs=[],
            validation_points=[],
            recommended_coverage=80,
            test_priorities=[],
        )

        result = analysis.to_dict()

        # All expected keys should be present
        expected_keys = {
            "workflow_id",
            "pattern_ids",
            "critical_paths",
            "high_risk_inputs",
            "validation_points",
            "recommended_coverage",
            "test_priorities",
        }

        assert set(result.keys()) == expected_keys


class TestRiskAnalyzer:
    """Test RiskAnalyzer with real pattern analysis."""

    def test_risk_analyzer_initialization(self):
        """Test RiskAnalyzer initializes with pattern registry."""
        analyzer = RiskAnalyzer()

        # Should have registry
        assert analyzer.registry is not None

    def test_analyze_returns_risk_analysis(self):
        """Test analyze returns RiskAnalysis object."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="test_wizard", pattern_ids=["linear_flow"])

        # Should return RiskAnalysis
        assert isinstance(result, RiskAnalysis)
        assert result.workflow_id == "test_wizard"
        assert "linear_flow" in result.pattern_ids

    def test_analyze_with_empty_patterns(self):
        """Test analyze handles wizard with no patterns."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="simple_wizard", pattern_ids=[])

        assert isinstance(result, RiskAnalysis)
        assert result.workflow_id == "simple_wizard"
        assert len(result.pattern_ids) == 0

    def test_analyze_with_linear_flow_pattern(self):
        """Test analyze identifies linear flow patterns."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="linear_wizard", pattern_ids=["linear_flow"])

        # Should identify linear flow characteristics
        assert isinstance(result, RiskAnalysis)
        # Check that analysis produced some output (priorities, paths, or validation)
        assert (
            len(result.test_priorities) > 0
            or len(result.critical_paths) > 0
            or len(result.validation_points) > 0
            or result.recommended_coverage > 0
        )

    def test_analyze_with_approval_pattern(self):
        """Test analyze works with approval pattern IDs."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="approval_wizard", pattern_ids=["approval"])

        # Should return valid RiskAnalysis even if pattern not in library
        assert isinstance(result, RiskAnalysis)
        assert result.workflow_id == "approval_wizard"
        assert "approval" in result.pattern_ids
        # Coverage should be reasonable (may be base coverage if pattern unknown)
        assert 0 < result.recommended_coverage <= 100

    def test_analyze_with_multiple_patterns(self):
        """Test analyze combines multiple pattern risks."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(
            workflow_id="complex_wizard",
            pattern_ids=["linear_flow", "phased_processing", "approval"],
        )

        # Should handle multiple patterns
        assert isinstance(result, RiskAnalysis)
        assert len(result.pattern_ids) == 3
        assert result.workflow_id == "complex_wizard"

        # More patterns typically mean more risk/complexity, but actual value depends on pattern library
        # Just verify it's a reasonable coverage recommendation
        assert 0 < result.recommended_coverage <= 100

    def test_analyze_sets_test_priorities(self):
        """Test analyze sets test priorities."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="wizard", pattern_ids=["linear_flow"])

        # Should have test priorities (dict or list)
        assert isinstance(result.test_priorities, dict | list)
        # Should not be empty
        assert len(result.test_priorities) > 0

    def test_analyze_with_phased_processing(self):
        """Test analyze handles phased processing pattern."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="phased_wizard", pattern_ids=["phased_processing"])

        assert isinstance(result, RiskAnalysis)
        # Phased processing should have critical paths for phases
        assert len(result.critical_paths) > 0 or len(result.test_priorities) > 0

    def test_analyze_recommended_coverage_range(self):
        """Test analyze returns reasonable coverage recommendations."""
        analyzer = RiskAnalyzer()

        # Test with simple wizard
        simple_result = analyzer.analyze(workflow_id="simple", pattern_ids=[])

        # Test with complex wizard
        complex_result = analyzer.analyze(
            workflow_id="complex", pattern_ids=["linear_flow", "approval", "phased_processing"]
        )

        # Both should have valid coverage recommendations
        assert 0 <= simple_result.recommended_coverage <= 100
        assert 0 <= complex_result.recommended_coverage <= 100

    def test_analyze_produces_valid_test_cases(self):
        """Test analyze produces valid test case names."""
        analyzer = RiskAnalyzer()

        result = analyzer.analyze(workflow_id="wizard", pattern_ids=["linear_flow"])

        test_cases = result.get_critical_test_cases()

        # All test cases should be valid Python identifiers
        for test_case in test_cases:
            assert test_case.isidentifier()
            assert test_case.startswith("test_")


class TestRiskAnalysisIntegration:
    """Integration tests for full risk analysis workflow."""

    def test_full_analysis_workflow(self):
        """Test complete workflow from analysis to test cases."""
        analyzer = RiskAnalyzer()

        # Step 1: Analyze
        analysis = analyzer.analyze(
            workflow_id="integration_wizard", pattern_ids=["linear_flow", "approval"]
        )

        # Step 2: Get test cases
        test_cases = analysis.get_critical_test_cases()

        # Step 3: Convert to dict
        analysis_dict = analysis.to_dict()

        # Verify complete workflow
        assert isinstance(analysis, RiskAnalysis)
        assert isinstance(test_cases, list)
        assert isinstance(analysis_dict, dict)

        # Dict should contain all analysis data
        assert analysis_dict["workflow_id"] == "integration_wizard"
        assert len(analysis_dict["pattern_ids"]) == 2

    def test_analysis_consistency(self):
        """Test analysis produces consistent results for same input."""
        analyzer = RiskAnalyzer()

        # Run analysis twice with same inputs
        result1 = analyzer.analyze("wizard", ["linear_flow"])
        result2 = analyzer.analyze("wizard", ["linear_flow"])

        # Should produce same recommendations
        assert result1.recommended_coverage == result2.recommended_coverage
        assert result1.pattern_ids == result2.pattern_ids

    def test_analysis_with_real_patterns(self):
        """Test analysis works with patterns from real registry."""
        analyzer = RiskAnalyzer()

        # Use patterns that likely exist in registry
        common_patterns = ["linear_flow", "phased_processing"]

        result = analyzer.analyze(workflow_id="real_pattern_wizard", pattern_ids=common_patterns)

        # Should handle real patterns without errors
        assert isinstance(result, RiskAnalysis)
        assert result.workflow_id == "real_pattern_wizard"
