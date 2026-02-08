"""Comprehensive tests for test_generator.cli module.

Tests cover:
- Command parsing (argparse)
- Test generation workflows
- Coverage analysis commands
- Template selection
- File I/O operations
- Error handling
- Edge cases (invalid code, missing files, etc.)

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import argparse
import json
from unittest.mock import MagicMock, Mock, patch

import pytest

pytest.importorskip("jinja2", reason="jinja2 required for test_generator tests")

from attune.test_generator.cli import cmd_analyze, cmd_generate, main  # noqa: E402
from attune.test_generator.risk_analyzer import RiskAnalysis  # noqa: E402


@pytest.mark.unit
class TestCommandParsing:
    """Test argparse command line parsing."""

    def test_main_no_args_shows_help(self, capsys):
        """Test that running without arguments shows help and exits."""
        with patch("sys.argv", ["cli.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            # Check help was printed
            captured = capsys.readouterr()
            assert "Test Generator for Attune Workflow Factory" in captured.out

    def test_generate_command_parsing(self):
        """Test parsing generate command with all arguments."""
        test_args = [
            "cli.py",
            "generate",
            "test_wizard",
            "--patterns",
            "linear_flow,approval",
            "--module",
            "workflows.test_wizard",
            "--class",
            "TestWizard",
            "--output",
            "tests/custom/",
        ]

        with patch("sys.argv", test_args):
            with patch("attune.test_generator.cli.cmd_generate") as mock_cmd:
                main()

                # Verify command was called
                mock_cmd.assert_called_once()

                # Check parsed arguments
                args = mock_cmd.call_args[0][0]
                assert args.workflow_id == "test_wizard"
                assert args.patterns == "linear_flow,approval"
                assert args.module == "workflows.test_wizard"
                assert args.workflow_class == "TestWizard"
                assert args.output == "tests/custom/"

    def test_generate_command_minimal_args(self):
        """Test generate command with minimal required arguments."""
        test_args = [
            "cli.py",
            "generate",
            "my_wizard",
            "--patterns",
            "linear_flow",
        ]

        with patch("sys.argv", test_args):
            with patch("attune.test_generator.cli.cmd_generate") as mock_cmd:
                main()

                args = mock_cmd.call_args[0][0]
                assert args.workflow_id == "my_wizard"
                assert args.patterns == "linear_flow"
                assert args.module is None
                assert args.workflow_class is None
                assert args.output is None

    def test_generate_command_missing_patterns_fails(self):
        """Test that generate command fails without --patterns."""
        test_args = [
            "cli.py",
            "generate",
            "my_wizard",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit):
                main()

    def test_analyze_command_parsing(self):
        """Test parsing analyze command with all arguments."""
        test_args = [
            "cli.py",
            "analyze",
            "test_wizard",
            "--patterns",
            "risk_assessment,code_analysis",
            "--json",
        ]

        with patch("sys.argv", test_args):
            with patch("attune.test_generator.cli.cmd_analyze") as mock_cmd:
                main()

                mock_cmd.assert_called_once()

                args = mock_cmd.call_args[0][0]
                assert args.workflow_id == "test_wizard"
                assert args.patterns == "risk_assessment,code_analysis"
                assert args.json is True

    def test_analyze_command_minimal_args(self):
        """Test analyze command without --json flag."""
        test_args = [
            "cli.py",
            "analyze",
            "my_wizard",
            "--patterns",
            "linear_flow",
        ]

        with patch("sys.argv", test_args):
            with patch("attune.test_generator.cli.cmd_analyze") as mock_cmd:
                main()

                args = mock_cmd.call_args[0][0]
                assert args.workflow_id == "my_wizard"
                assert args.patterns == "linear_flow"
                assert args.json is False

    def test_invalid_command_shows_help(self, capsys):
        """Test that invalid command shows help."""
        test_args = ["cli.py", "invalid_command"]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # argparse exits with 2 for invalid arguments
            assert exc_info.value.code == 2

            captured = capsys.readouterr()
            assert "invalid choice" in captured.err


@pytest.mark.unit
class TestGenerateCommand:
    """Test cmd_generate function and test generation workflow."""

    def test_generate_creates_unit_tests(self, tmp_path):
        """Test that generate command creates unit test file."""
        # Arrange
        output_dir = tmp_path / "tests" / "unit" / "workflows"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow,approval",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {
            "unit": "# Unit tests\ndef test_example(): pass",
            "integration": "",
            "fixtures": "# Fixtures\n@pytest.fixture\ndef example(): return {}",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            # Act
            cmd_generate(args)

            # Assert
            unit_test_file = output_dir / "test_test_wizard_workflow.py"
            fixtures_file = output_dir / "fixtures_test_wizard.py"

            assert unit_test_file.exists()
            assert fixtures_file.exists()
            assert "# Unit tests" in unit_test_file.read_text()
            assert "# Fixtures" in fixtures_file.read_text()

    def test_generate_creates_integration_tests_when_provided(self, tmp_path):
        """Test that integration tests are created when available."""
        output_dir = tmp_path / "tests" / "unit" / "workflows"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {
            "unit": "# Unit tests",
            "integration": "# Integration tests\ndef test_integration(): pass",
            "fixtures": "# Fixtures",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            integration_file = (
                tmp_path / "tests" / "integration" / "test_test_wizard_integration.py"
            )
            assert integration_file.exists()
            assert "# Integration tests" in integration_file.read_text()

    def test_generate_no_integration_tests_when_empty(self, tmp_path):
        """Test that integration test file is not created when empty."""
        output_dir = tmp_path / "tests" / "unit" / "workflows"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {
            "unit": "# Unit tests",
            "integration": "",  # Empty
            "fixtures": "# Fixtures",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            integration_file = (
                tmp_path / "tests" / "integration" / "test_test_wizard_integration.py"
            )
            assert not integration_file.exists()

    def test_generate_uses_default_output_dir(self):
        """Test that default output directory is used when not specified."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=None,  # No output specified
        )

        mock_tests = {
            "unit": "# Unit tests",
            "integration": "",
            "fixtures": "# Fixtures",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            with patch("builtins.open", create=True) as mock_open:
                cmd_generate(args)

                # Check that default path was used
                calls = mock_open.call_args_list
                assert any("tests/unit/workflows" in str(call) for call in calls)

    def test_generate_parses_pattern_ids_correctly(self):
        """Test that comma-separated pattern IDs are parsed correctly."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow,approval,structured_fields",
            module="workflows.test_wizard",
            workflow_class="TestWizard",
            output=None,
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            with patch("builtins.open", create=True):
                cmd_generate(args)

                # Verify generate_tests was called with correct pattern_ids
                call_args = mock_generator.generate_tests.call_args
                assert call_args[1]["pattern_ids"] == [
                    "linear_flow",
                    "approval",
                    "structured_fields",
                ]

    def test_generate_passes_module_and_class(self):
        """Test that module and class names are passed to generator."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module="workflows.custom.test_wizard",
            workflow_class="CustomTestWizard",
            output=None,
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            with patch("builtins.open", create=True):
                cmd_generate(args)

                call_args = mock_generator.generate_tests.call_args
                assert call_args[1]["workflow_module"] == "workflows.custom.test_wizard"
                assert call_args[1]["workflow_class"] == "CustomTestWizard"

    def test_generate_creates_output_directory_if_missing(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new" / "nested" / "path"
        assert not output_dir.exists()

        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            assert output_dir.exists()

    def test_generate_prints_success_message(self, tmp_path, capsys):
        """Test that success message is printed after generation."""
        output_dir = tmp_path / "tests"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir / "unit" / "workflows"),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            captured = capsys.readouterr()
            assert "🎉 Test generation complete!" in captured.out
            assert "Generated files:" in captured.out
            assert "Next steps:" in captured.out


@pytest.mark.unit
class TestAnalyzeCommand:
    """Test cmd_analyze function and risk analysis workflow."""

    def test_analyze_displays_risk_analysis(self, capsys):
        """Test that analyze command displays risk analysis results."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow,risk_assessment",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow", "risk_assessment"],
            critical_paths=["initialization", "data_processing", "cleanup"],
            high_risk_inputs=["user_code", "file_path", "sql_query"],
            validation_points=["input_validation", "output_sanitization"],
            recommended_coverage=85,
            test_priorities={
                "test_initialization": 1,
                "test_user_code_validation": 1,
                "test_data_processing": 2,
                "test_cleanup": 3,
            },
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()

            # Check output contains expected sections
            assert "Risk Analysis: test_wizard" in captured.out
            assert "Patterns Used: 2" in captured.out
            assert "linear_flow" in captured.out
            assert "risk_assessment" in captured.out
            assert "Critical Paths: 3" in captured.out
            assert "initialization" in captured.out
            assert "High-Risk Inputs: 3" in captured.out
            assert "user_code" in captured.out
            assert "Validation Points: 2" in captured.out
            assert "Recommended Test Coverage: 85%" in captured.out

    def test_analyze_displays_test_priorities(self, capsys):
        """Test that test priorities are displayed correctly."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            test_priorities={
                "test_critical_path": 1,
                "test_high_priority": 2,
                "test_medium_priority": 3,
                "test_low_priority": 4,
                "test_optional": 5,
            },
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()

            # Check priority labels are displayed
            assert "CRITICAL" in captured.out
            assert "HIGH" in captured.out
            assert "MEDIUM" in captured.out
            assert "LOW" in captured.out
            assert "OPTIONAL" in captured.out
            assert "test_critical_path" in captured.out

    def test_analyze_limits_displayed_items(self, capsys):
        """Test that only top 5 items are displayed for long lists."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        # Create analysis with many items
        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            high_risk_inputs=[f"input_{i}" for i in range(20)],
            validation_points=[f"validation_{i}" for i in range(15)],
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()

            # Should show "High-Risk Inputs: 20" but only display first 5
            assert "High-Risk Inputs: 20" in captured.out
            assert "input_0" in captured.out
            assert "input_4" in captured.out
            # input_10 and beyond should not be shown
            assert "input_10" not in captured.out

    def test_analyze_outputs_json_file_when_requested(self, tmp_path):
        """Test that JSON file is created when --json flag is used."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=True,
        )

        mock_analysis_dict = {
            "wizard_id": "test_wizard",
            "pattern_ids": ["linear_flow"],
            "critical_paths": ["path1", "path2"],
            "recommended_coverage": 80,
        }

        mock_analysis = Mock(spec=RiskAnalysis)
        mock_analysis.wizard_id = "test_wizard"
        mock_analysis.pattern_ids = ["linear_flow"]
        mock_analysis.critical_paths = ["path1", "path2"]
        mock_analysis.high_risk_inputs = []
        mock_analysis.validation_points = []
        mock_analysis.recommended_coverage = 80
        mock_analysis.test_priorities = {}
        mock_analysis.to_dict.return_value = mock_analysis_dict

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            # Change to tmp_path directory for JSON output
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                cmd_analyze(args)

                # Check JSON file was created
                json_file = tmp_path / "test_wizard_risk_analysis.json"
                assert json_file.exists()

                # Verify JSON content
                with open(json_file) as f:
                    data = json.load(f)
                    assert data["wizard_id"] == "test_wizard"
                    assert data["pattern_ids"] == ["linear_flow"]
                    assert data["recommended_coverage"] == 80
            finally:
                os.chdir(original_cwd)

    def test_analyze_parses_pattern_ids_correctly(self):
        """Test that comma-separated pattern IDs are parsed correctly."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="pattern1,pattern2,pattern3",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["pattern1", "pattern2", "pattern3"],
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            # Verify analyzer was called with correct pattern_ids
            call_args = mock_analyzer.analyze.call_args
            assert call_args[0][1] == ["pattern1", "pattern2", "pattern3"]


@pytest.mark.unit
class TestFileOperations:
    """Test file I/O operations and path handling."""

    def test_generate_writes_utf8_encoded_files(self, tmp_path):
        """Test that generated files are UTF-8 encoded."""
        output_dir = tmp_path / "tests"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir / "unit" / "workflows"),
        )

        # Include unicode characters in test content
        mock_tests = {
            "unit": "# Tests with unicode: ✓ 🎉 → ←",
            "integration": "",
            "fixtures": "# Fixtures: café naïve résumé",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            # Verify files can be read back with UTF-8
            unit_file = output_dir / "unit" / "workflows" / "test_test_wizard_workflow.py"
            content = unit_file.read_text(encoding="utf-8")
            assert "✓ 🎉" in content

            fixtures_file = output_dir / "unit" / "workflows" / "fixtures_test_wizard.py"
            content = fixtures_file.read_text(encoding="utf-8")
            assert "café naïve" in content

    def test_generate_overwrites_existing_files(self, tmp_path):
        """Test that existing test files are overwritten."""
        output_dir = tmp_path / "tests" / "unit" / "workflows"
        output_dir.mkdir(parents=True)

        # Create existing file with old content
        unit_file = output_dir / "test_test_wizard_workflow.py"
        unit_file.write_text("# Old content")

        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {
            "unit": "# New content",
            "integration": "",
            "fixtures": "# Fixtures",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            # Verify file was overwritten
            assert unit_file.read_text() == "# New content"

    def test_generate_handles_nested_output_paths(self, tmp_path):
        """Test that deeply nested output paths are handled correctly."""
        output_dir = tmp_path / "a" / "b" / "c" / "d" / "tests"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            assert output_dir.exists()
            assert (output_dir / "test_test_wizard_workflow.py").exists()


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling for various failure scenarios."""

    def test_generate_handles_generator_exception(self, tmp_path, capsys):
        """Test that generator exceptions are properly handled."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.side_effect = ValueError("Template not found")
            mock_gen_class.return_value = mock_generator

            with pytest.raises(ValueError, match="Template not found"):
                cmd_generate(args)

    def test_analyze_handles_analyzer_exception(self, capsys):
        """Test that analyzer exceptions are properly handled."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="invalid_pattern",
            json=False,
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.side_effect = KeyError("Pattern not found")
            mock_analyzer_class.return_value = mock_analyzer

            with pytest.raises(KeyError, match="Pattern not found"):
                cmd_analyze(args)

    def test_generate_handles_file_write_permission_error(self, tmp_path):
        """Test handling of permission errors during file write."""
        output_dir = tmp_path / "readonly"
        output_dir.mkdir()

        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            # Make directory read-only on Unix-like systems
            import os

            if os.name != "nt":  # Skip on Windows
                output_dir.chmod(0o444)

                try:
                    with pytest.raises(PermissionError):
                        cmd_generate(args)
                finally:
                    # Restore permissions for cleanup
                    output_dir.chmod(0o755)

    def test_analyze_handles_json_write_error(self, tmp_path):
        """Test handling of errors when writing JSON output."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=True,
        )

        mock_analysis = RiskAnalysis(workflow_id="test_wizard", pattern_ids=["linear_flow"])

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            # Mock json.dump to raise an error
            with patch("json.dump") as mock_dump:
                mock_dump.side_effect = TypeError("Object not JSON serializable")

                with pytest.raises(TypeError):
                    cmd_analyze(args)


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_generate_with_empty_pattern_string(self, tmp_path):
        """Test generation with empty pattern string."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="",  # Empty string
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            # Empty string should result in empty list after split
            call_args = mock_generator.generate_tests.call_args
            assert call_args[1]["pattern_ids"] == []

    def test_generate_with_special_characters_in_wizard_id(self, tmp_path):
        """Test generation with special characters in wizard ID."""
        args = argparse.Namespace(
            workflow_id="test-wizard_v2.0",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            # Files should be created with wizard_id in name
            expected_file = tmp_path / "test_test-wizard_v2.0_workflow.py"
            assert expected_file.exists()

    def test_analyze_with_no_test_priorities(self, capsys):
        """Test analyze when risk analysis has no test priorities."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            test_priorities={},  # Empty priorities
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()
            # Should still show "Test Priorities:" header
            assert "Test Priorities:" in captured.out

    def test_analyze_with_all_empty_lists(self, capsys):
        """Test analyze when all analysis lists are empty."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=[],
            critical_paths=[],
            high_risk_inputs=[],
            validation_points=[],
            test_priorities={},
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()
            # Should show counts of 0
            assert "Patterns Used: 0" in captured.out
            assert "Critical Paths: 0" in captured.out
            assert "High-Risk Inputs: 0" in captured.out

    def test_generate_with_very_long_wizard_id(self, tmp_path):
        """Test generation with very long wizard ID."""
        long_id = "a" * 200
        args = argparse.Namespace(
            workflow_id=long_id,
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            # File should be created (filesystem will handle length limits)
            files = list(tmp_path.glob("test_*.py"))
            assert len(files) > 0


@pytest.mark.unit
class TestIntegrationWithDependencies:
    """Test integration with TestGenerator and RiskAnalyzer."""

    def test_generate_calls_test_generator_with_correct_params(self):
        """Test that cmd_generate correctly calls TestGenerator.generate_tests."""
        args = argparse.Namespace(
            workflow_id="my_wizard",
            patterns="pattern1,pattern2",
            module="workflows.my_wizard",
            workflow_class="MyWizard",
            output=None,
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            with patch("builtins.open", create=True):
                cmd_generate(args)

                # Verify TestGenerator was instantiated
                mock_gen_class.assert_called_once()

                # Verify generate_tests was called with correct parameters
                mock_generator.generate_tests.assert_called_once_with(
                    workflow_id="my_wizard",
                    pattern_ids=["pattern1", "pattern2"],
                    workflow_module="workflows.my_wizard",
                    workflow_class="MyWizard",
                )

    def test_analyze_calls_risk_analyzer_with_correct_params(self):
        """Test that cmd_analyze correctly calls RiskAnalyzer.analyze."""
        args = argparse.Namespace(
            workflow_id="my_wizard",
            patterns="pattern1,pattern2",
            json=False,
        )

        mock_analysis = RiskAnalysis(workflow_id="my_wizard", pattern_ids=["pattern1", "pattern2"])

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            # Verify RiskAnalyzer was instantiated
            mock_analyzer_class.assert_called_once()

            # Verify analyze was called with correct parameters
            mock_analyzer.analyze.assert_called_once_with("my_wizard", ["pattern1", "pattern2"])


@pytest.mark.unit
class TestLogging:
    """Test logging behavior."""

    def test_generate_logs_wizard_info(self, tmp_path, caplog):
        """Test that generate command logs wizard information."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow,approval",
            module=None,
            workflow_class=None,
            output=str(tmp_path),
        )

        mock_tests = {"unit": "# Tests", "integration": "", "fixtures": "# Fixtures"}

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            import logging

            with caplog.at_level(logging.INFO):
                cmd_generate(args)

                # Check log messages
                assert "Generating tests for workflow: test_wizard" in caplog.text
                assert "Patterns: linear_flow, approval" in caplog.text

    def test_analyze_logs_wizard_info(self, caplog):
        """Test that analyze command logs wizard information."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        mock_analysis = RiskAnalysis(workflow_id="test_wizard", pattern_ids=["linear_flow"])

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            import logging

            with caplog.at_level(logging.INFO):
                cmd_analyze(args)

                assert "Analyzing workflow: test_wizard" in caplog.text


@pytest.mark.unit
class TestOutputFormatting:
    """Test output formatting and display."""

    def test_generate_displays_file_paths(self, tmp_path, capsys):
        """Test that generated file paths are displayed."""
        output_dir = tmp_path / "tests" / "unit" / "workflows"
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            module=None,
            workflow_class=None,
            output=str(output_dir),
        )

        mock_tests = {
            "unit": "# Tests",
            "integration": "# Integration",
            "fixtures": "# Fixtures",
        }

        with patch("attune.test_generator.cli.TestGenerator") as mock_gen_class:
            mock_generator = MagicMock()
            mock_generator.generate_tests.return_value = mock_tests
            mock_gen_class.return_value = mock_generator

            cmd_generate(args)

            captured = capsys.readouterr()

            # Check that file paths are shown
            assert "test_test_wizard_workflow.py" in captured.out
            assert "test_test_wizard_integration.py" in captured.out
            assert "fixtures_test_wizard.py" in captured.out

    def test_analyze_formats_priority_labels_correctly(self, capsys):
        """Test that priority labels are formatted with consistent width."""
        args = argparse.Namespace(
            workflow_id="test_wizard",
            patterns="linear_flow",
            json=False,
        )

        mock_analysis = RiskAnalysis(
            workflow_id="test_wizard",
            pattern_ids=["linear_flow"],
            test_priorities={
                "test_a": 1,  # CRITICAL
                "test_b": 2,  # HIGH
                "test_c": 3,  # MEDIUM
                "test_d": 4,  # LOW
                "test_e": 5,  # OPTIONAL
            },
        )

        with patch("attune.test_generator.cli.RiskAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = mock_analysis
            mock_analyzer_class.return_value = mock_analyzer

            cmd_analyze(args)

            captured = capsys.readouterr()

            # Priority labels should be formatted with consistent width (8 chars)
            lines = captured.out.split("\n")
            priority_lines = [line for line in lines if "[" in line and "]" in line]

            # Check that labels are properly formatted
            for line in priority_lines:
                # Extract priority label (between [ and ])
                if "[" in line and "]" in line:
                    start = line.index("[") + 1
                    end = line.index("]")
                    label = line[start:end]
                    # Label should be 8 characters (padded with spaces)
                    assert len(label) == 8
