"""Tests for attune.test_generator module.

Covers risk_analyzer.py, generator.py, cli.py, and __init__.py.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("jinja2", reason="jinja2 required for test_generator")

from attune.test_generator.risk_analyzer import RiskAnalysis, RiskAnalyzer  # noqa: E402


# ---------------------------------------------------------------------------
# RiskAnalysis dataclass tests
# ---------------------------------------------------------------------------
class TestRiskAnalysis:
    """Tests for the RiskAnalysis dataclass."""

    def test_defaults(self):
        """Test default field values."""
        ra = RiskAnalysis(workflow_id="test-wf", pattern_ids=["p1"])
        assert ra.workflow_id == "test-wf"
        assert ra.pattern_ids == ["p1"]
        assert ra.critical_paths == []
        assert ra.high_risk_inputs == []
        assert ra.validation_points == []
        assert ra.recommended_coverage == 80
        assert ra.test_priorities == {}

    def test_get_critical_test_cases_critical_paths(self):
        """Test test case generation from critical paths."""
        ra = RiskAnalysis(
            workflow_id="w",
            pattern_ids=[],
            critical_paths=["approval workflow", "step-sequence"],
        )
        cases = ra.get_critical_test_cases()
        assert "test_approval_workflow" in cases
        assert "test_step_sequence" in cases

    def test_get_critical_test_cases_high_risk_inputs(self):
        """Test test case generation from high-risk inputs."""
        ra = RiskAnalysis(
            workflow_id="w",
            pattern_ids=[],
            high_risk_inputs=["save without preview"],
        )
        cases = ra.get_critical_test_cases()
        assert "test_save_without_preview_validation" in cases

    def test_get_critical_test_cases_empty(self):
        """Test empty analysis produces no test cases."""
        ra = RiskAnalysis(workflow_id="w", pattern_ids=[])
        assert ra.get_critical_test_cases() == []

    def test_to_dict(self):
        """Test serialization to dict."""
        ra = RiskAnalysis(
            workflow_id="wf1",
            pattern_ids=["p1", "p2"],
            critical_paths=["cp"],
            high_risk_inputs=["hri"],
            validation_points=["vp"],
            recommended_coverage=90,
            test_priorities={"test_x": 1},
        )
        d = ra.to_dict()
        assert d["workflow_id"] == "wf1"
        assert d["pattern_ids"] == ["p1", "p2"]
        assert d["critical_paths"] == ["cp"]
        assert d["high_risk_inputs"] == ["hri"]
        assert d["validation_points"] == ["vp"]
        assert d["recommended_coverage"] == 90
        assert d["test_priorities"] == {"test_x": 1}


# ---------------------------------------------------------------------------
# RiskAnalyzer tests
# ---------------------------------------------------------------------------
class TestRiskAnalyzer:
    """Tests for the RiskAnalyzer class."""

    def test_analyze_empty_patterns(self):
        """Test analysis with no patterns."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", [])
        assert result.workflow_id == "wf"
        assert result.critical_paths == []
        assert result.recommended_coverage == 70  # base only

    def test_analyze_unknown_pattern(self):
        """Test analysis with non-existent pattern ID."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", ["nonexistent_pattern_xyz"])
        assert result.critical_paths == []

    def test_analyze_approval_pattern(self):
        """Test analysis recognizes approval patterns."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", ["approval"])
        assert "approval_workflow" in result.critical_paths
        assert "save_without_preview" in result.high_risk_inputs
        assert "save_without_approval" in result.high_risk_inputs
        assert "preview_generated" in result.validation_points
        assert "user_approved" in result.validation_points

    def test_analyze_step_validation_pattern(self):
        """Test analysis recognizes step validation patterns."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", ["step_validation"])
        assert "step_sequence_validation" in result.critical_paths
        assert "skip_step" in result.high_risk_inputs

    def test_analyze_phased_processing_pattern(self):
        """Test analysis recognizes phased processing patterns."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", ["phased_processing"])
        # Should have phases as critical paths
        assert len(result.critical_paths) > 0

    def test_coverage_calculation_caps_at_95(self):
        """Test that recommended coverage caps at 95%."""
        analyzer = RiskAnalyzer()
        # Many patterns should push coverage toward cap
        result = analyzer.analyze("wf", ["approval", "step_validation", "phased_processing"])
        assert result.recommended_coverage <= 95

    def test_coverage_calculation_base_is_70(self):
        """Test minimum coverage is 70% (base) with no patterns."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", [])
        assert result.recommended_coverage == 70

    def test_prioritize_tests(self):
        """Test that test priorities are assigned correctly."""
        analyzer = RiskAnalyzer()
        result = analyzer.analyze("wf", ["approval"])
        # Critical paths -> priority 1
        assert result.test_priorities.get("test_approval_workflow") == 1
        # High risk inputs -> priority 2
        assert result.test_priorities.get("test_save_without_preview_validation") == 2
        # Success/happy path -> priority 4
        assert result.test_priorities.get("test_success_path") == 4
        assert result.test_priorities.get("test_happy_path") == 4
        # Edge cases -> priority 5
        assert result.test_priorities.get("test_edge_cases") == 5


# ---------------------------------------------------------------------------
# TestGenerator tests
# ---------------------------------------------------------------------------
class TestTestGenerator:
    """Tests for the TestGenerator class."""

    def test_init_default_template_dir(self):
        """Test generator uses default template directory."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen.template_dir.name == "templates"

    def test_init_custom_template_dir(self, tmp_path):
        """Test generator with custom template directory."""
        from attune.test_generator.generator import TestGenerator

        # Create a minimal template
        template = tmp_path / "unit_test.py.jinja2"
        template.write_text("# generated test for {{ workflow_id }}")

        gen = TestGenerator(template_dir=tmp_path)
        assert gen.template_dir == tmp_path

    def test_infer_module_known_workflow(self):
        """Test module inference for known workflow IDs."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen._infer_module("soap_note") == "workflows.soap_note"
        assert gen._infer_module("sbar") == "workflows.sbar"
        assert gen._infer_module("care_plan") == "workflows.care_plan"

    def test_infer_module_unknown_workflow(self):
        """Test module inference for unknown workflow IDs."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen._infer_module("custom") == "workflows.custom_workflow"

    def test_infer_class_name(self):
        """Test class name inference from workflow ID."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen._infer_class_name("soap_note") == "SoapNoteWorkflow"
        assert gen._infer_class_name("care_plan") == "CarePlanWorkflow"
        assert gen._infer_class_name("debug") == "DebugWorkflow"

    def test_needs_integration_tests_true(self):
        """Test integration tests needed for multi-step workflows."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen._needs_integration_tests(["linear_flow"]) is True
        assert gen._needs_integration_tests(["phased_processing"]) is True

    def test_needs_integration_tests_false(self):
        """Test integration tests not needed for simple workflows."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        assert gen._needs_integration_tests(["approval"]) is False
        assert gen._needs_integration_tests([]) is False

    def test_generate_tests_basic(self):
        """Test end-to-end test generation."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        result = gen.generate_tests(
            workflow_id="soap_note",
            pattern_ids=["linear_flow", "approval"],
            workflow_module="workflows.soap_note",
            workflow_class="SOAPNoteWorkflow",
        )
        assert "unit" in result
        assert "integration" in result
        assert "fixtures" in result
        assert result["unit"]  # Non-empty
        assert result["integration"]  # Non-empty (linear_flow present)
        assert result["fixtures"]  # Non-empty

    def test_generate_tests_no_integration(self):
        """Test generation without integration tests."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        result = gen.generate_tests(
            workflow_id="simple",
            pattern_ids=["approval"],
            workflow_module="workflows.simple",
            workflow_class="SimpleWorkflow",
        )
        assert result["unit"]
        assert result["integration"] is None
        assert result["fixtures"]

    def test_generate_tests_infers_module_and_class(self):
        """Test that module and class are inferred when not provided."""
        from attune.test_generator.generator import TestGenerator

        gen = TestGenerator()
        result = gen.generate_tests(
            workflow_id="soap_note",
            pattern_ids=[],
        )
        assert result["unit"]
        assert "soap_note" in result["fixtures"]

    def test_get_default_template_dir(self):
        """Test the fallback template directory function."""
        from attune.test_generator.generator import _get_default_template_dir

        result = _get_default_template_dir()
        assert isinstance(result, Path)
        assert result.name == "templates"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------
class TestTestGeneratorCLI:
    """Tests for the test generator CLI."""

    def test_main_no_command_exits(self):
        """Test CLI exits with no command."""
        from attune.test_generator.cli import main

        with patch("sys.argv", ["test_generator"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_cmd_generate(self, tmp_path):
        """Test generate command writes files."""
        from attune.test_generator.cli import cmd_generate

        args = argparse.Namespace(
            workflow_id="soap_note",
            patterns="linear_flow,approval",
            module="workflows.soap_note",
            workflow_class="SOAPNoteWorkflow",
            output=str(tmp_path),
        )
        cmd_generate(args)

        # Verify files were written
        unit_file = tmp_path / "test_soap_note_workflow.py"
        fixtures_file = tmp_path / "fixtures_soap_note.py"
        assert unit_file.exists()
        assert fixtures_file.exists()

    def test_cmd_generate_with_integration(self, tmp_path):
        """Test generate command creates integration tests for multi-step."""
        from attune.test_generator.cli import cmd_generate

        # Create integration dir structure
        tests_dir = tmp_path / "unit" / "workflows"
        tests_dir.mkdir(parents=True)

        args = argparse.Namespace(
            workflow_id="soap_note",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(tests_dir),
        )
        cmd_generate(args)

        # Integration test file should exist in sibling dir
        integration_dir = tmp_path / "integration"
        assert integration_dir.exists()

    def test_cmd_analyze(self, capsys):
        """Test analyze command produces output."""
        from attune.test_generator.cli import cmd_analyze

        args = argparse.Namespace(
            workflow_id="test_wf",
            patterns="approval",
            json=False,
        )
        cmd_analyze(args)

        captured = capsys.readouterr()
        assert "Risk Analysis: test_wf" in captured.out
        assert "Recommended Test Coverage" in captured.out

    def test_cmd_analyze_json_output(self, tmp_path, capsys, monkeypatch):
        """Test analyze command with JSON output."""
        from attune.test_generator.cli import cmd_analyze

        monkeypatch.chdir(tmp_path)

        args = argparse.Namespace(
            workflow_id="test_wf",
            patterns="approval",
            json=True,
        )
        cmd_analyze(args)

        json_file = tmp_path / "test_wf_risk_analysis.json"
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data["workflow_id"] == "test_wf"

    def test_cmd_generate_empty_patterns(self, tmp_path):
        """Test generate command with no patterns."""
        from attune.test_generator.cli import cmd_generate

        args = argparse.Namespace(
            workflow_id="simple",
            patterns="",
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )
        cmd_generate(args)

        unit_file = tmp_path / "test_simple_workflow.py"
        assert unit_file.exists()


# ---------------------------------------------------------------------------
# __init__.py exports test
# ---------------------------------------------------------------------------
class TestTestGeneratorInit:
    """Tests for the test_generator __init__ exports."""

    def test_exports(self):
        """Test that __init__ exports expected names."""
        import attune.test_generator as tg

        assert hasattr(tg, "TestGenerator")
        assert hasattr(tg, "RiskAnalyzer")
        assert hasattr(tg, "RiskAnalysis")
        assert tg.__version__  # dynamic from importlib.metadata
