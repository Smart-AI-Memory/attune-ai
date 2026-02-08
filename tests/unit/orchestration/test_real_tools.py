"""Tests for real_tools.py - Meta-Orchestration real tool implementations.

Sprint 1: v4.0 Core Coverage
Tests for:
- _validate_file_path security function
- RealCoverageAnalyzer
- RealTestGenerator
- RealTestValidator
- RealSecurityAuditor
- RealCodeQualityAnalyzer
- RealDocumentationAnalyzer

Coverage target: 80%+
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from attune.orchestration.real_tools import (
    REAL_TOOLS,
    CoverageReport,
    DocumentationReport,
    QualityReport,
    RealCodeQualityAnalyzer,
    RealCoverageAnalyzer,
    RealDocumentationAnalyzer,
    RealSecurityAuditor,
    RealTestGenerator,
    RealTestValidator,
    SecurityReport,
    _validate_file_path,
)


class Test_ValidateFilePath:
    """Tests for _validate_file_path security function."""

    def test_valid_path_returns_resolved_path(self, tmp_path):
        """Test that valid paths are resolved correctly."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = _validate_file_path(str(test_file))

        assert isinstance(result, Path)
        assert result == test_file.resolve()

    def test_empty_path_raises_value_error(self):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="path must be a non-empty string"):
            _validate_file_path("")

    def test_none_path_raises_value_error(self):
        """Test that None path raises ValueError."""
        with pytest.raises(ValueError, match="path must be a non-empty string"):
            _validate_file_path(None)

    def test_null_byte_in_path_raises_value_error(self):
        """Test that null bytes in path raise ValueError."""
        with pytest.raises(ValueError, match="path contains null bytes"):
            _validate_file_path("test\x00.txt")

    def test_system_directory_etc_raises_value_error(self):
        """Test that /etc directory is blocked."""
        # Note: On macOS, /etc is a symlink to /private/etc, so the resolved
        # path won't match the /etc check. This is a known limitation.
        # Skip this test on macOS and use /sys instead which exists directly
        import platform

        if platform.system() == "Darwin":
            pytest.skip(
                "/etc resolves to /private/etc on macOS - see test_system_directory_sys instead"
            )

        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/etc/passwd")

    def test_system_directory_sys_raises_value_error(self):
        """Test that /sys directory is blocked."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/sys/kernel/debug")

    def test_system_directory_proc_raises_value_error(self):
        """Test that /proc directory is blocked."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/proc/self/mem")

    def test_system_directory_dev_raises_value_error(self):
        """Test that /dev directory is blocked."""
        with pytest.raises(ValueError, match="Cannot write to system directory"):
            _validate_file_path("/dev/null")


class TestRealCoverageAnalyzer:
    """Tests for RealCoverageAnalyzer."""

    def test_init_resolves_project_root(self, tmp_path):
        """Test that project root is resolved during init."""
        analyzer = RealCoverageAnalyzer(str(tmp_path))

        assert analyzer.project_root == tmp_path.resolve()

    def test_analyze_with_existing_fresh_coverage_uses_cached(self, tmp_path, monkeypatch):
        """Test that fresh coverage.json is used without regeneration."""
        # Create fake coverage.json
        coverage_file = tmp_path / "coverage.json"
        coverage_data = {
            "totals": {"percent_covered": 85.5},
            "files": {"src/test.py": {"summary": {"percent_covered": 90.0}, "missing_lines": []}},
        }
        coverage_file.write_text(json.dumps(coverage_data))

        # Mock time to make file appear fresh (< 1 hour old)
        import time

        original_time = time.time
        monkeypatch.setattr(time, "time", lambda: original_time() + 10)

        analyzer = RealCoverageAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert result.total_coverage == 85.5
        assert result.files_analyzed == 1
        assert len(result.uncovered_files) == 0  # 90% is above 80% threshold

    def test_analyze_with_stale_coverage_regenerates(self, tmp_path, monkeypatch):
        """Test that stale coverage.json triggers regeneration."""
        # Create fake old coverage.json
        coverage_file = tmp_path / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 50.0}, "files": {}}
        coverage_file.write_text(json.dumps(coverage_data))

        # Mock time to make file appear stale (> 1 hour old)
        import time

        original_time = time.time
        monkeypatch.setattr(time, "time", lambda: original_time() + 7200)  # 2 hours

        # Mock subprocess to avoid actually running tests
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            analyzer = RealCoverageAnalyzer(str(tmp_path))
            # This should trigger regeneration, but fall back to reading the file
            result = analyzer.analyze()

        assert result.total_coverage == 50.0

    def test_analyze_missing_coverage_file_raises_runtime_error(self, tmp_path):
        """Test that missing coverage.json raises RuntimeError."""
        analyzer = RealCoverageAnalyzer(str(tmp_path))

        # Mock subprocess to not create the file
        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Coverage report not found"):
                analyzer.analyze(use_existing=False)

    def test_analyze_identifies_low_coverage_files(self, tmp_path):
        """Test that files below 80% coverage are identified."""
        coverage_file = tmp_path / "coverage.json"
        coverage_data = {
            "totals": {"percent_covered": 60.0},
            "files": {
                "src/low.py": {
                    "summary": {"percent_covered": 45.0},
                    "missing_lines": [10, 11, 12, 13, 14],
                },
                "src/high.py": {"summary": {"percent_covered": 95.0}, "missing_lines": []},
            },
        }
        coverage_file.write_text(json.dumps(coverage_data))

        analyzer = RealCoverageAnalyzer(str(tmp_path))
        result = analyzer.analyze()

        assert result.total_coverage == 60.0
        assert result.files_analyzed == 2
        assert len(result.uncovered_files) == 1
        assert result.uncovered_files[0]["path"] == "src/low.py"
        assert result.uncovered_files[0]["coverage"] == 45.0
        assert "src/low.py" in result.missing_lines


class TestRealSecurityAuditor:
    """Tests for RealSecurityAuditor."""

    def test_init_resolves_project_root(self, tmp_path):
        """Test that project root is resolved during init."""
        auditor = RealSecurityAuditor(str(tmp_path))

        assert auditor.project_root == tmp_path.resolve()

    def test_audit_with_no_issues_returns_clean_report(self, tmp_path):
        """Test that clean code returns SecurityReport with no issues."""
        # Mock Bandit to return clean results
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "metrics": {
                    "_totals": {"SEVERITY.HIGH": 0, "SEVERITY.MEDIUM": 0, "SEVERITY.LOW": 0}
                },
                "results": [],
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            auditor = RealSecurityAuditor(str(tmp_path))
            report = auditor.audit()

        assert isinstance(report, SecurityReport)
        assert report.critical_count == 0
        assert report.high_count == 0
        assert report.medium_count == 0
        assert report.total_issues == 0
        assert report.passed is True

    def test_audit_with_high_severity_issues_returns_correct_count(self, tmp_path):
        """Test that high severity issues are counted correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "HIGH",
                        "issue_confidence": "HIGH",
                        "issue_text": "Possible SQL injection",
                        "filename": "src/test.py",
                        "line_number": 42,
                        "test_id": "B608",
                    },
                    {
                        "issue_severity": "HIGH",
                        "issue_confidence": "MEDIUM",
                        "issue_text": "Use of eval() detected",
                        "filename": "src/bad.py",
                        "line_number": 10,
                        "test_id": "B307",
                    },
                ]
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            auditor = RealSecurityAuditor(str(tmp_path))
            report = auditor.audit()

        assert report.critical_count == 0
        assert report.high_count == 2
        assert report.medium_count == 0
        assert report.total_issues == 2

    def test_audit_without_bandit_raises_runtime_error(self, tmp_path):
        """Test that missing Bandit raises RuntimeError."""
        # Mock subprocess to raise FileNotFoundError (bandit not installed)
        with patch("subprocess.run", side_effect=FileNotFoundError("bandit not found")):
            auditor = RealSecurityAuditor(str(tmp_path))

            with pytest.raises(RuntimeError, match="Security audit failed"):
                auditor.audit()


class TestRealCodeQualityAnalyzer:
    """Tests for RealCodeQualityAnalyzer."""

    def test_init_resolves_project_root(self, tmp_path):
        """Test that project root is resolved during init."""
        analyzer = RealCodeQualityAnalyzer(str(tmp_path))

        assert analyzer.project_root == tmp_path.resolve()

    def test_analyze_with_clean_code_returns_perfect_score(self, tmp_path):
        """Test that clean code returns high quality score."""
        # Mock Ruff (no issues)
        ruff_result = Mock()
        ruff_result.returncode = 0
        ruff_result.stdout = "All checks passed!"

        # Mock MyPy (no errors)
        mypy_result = Mock()
        mypy_result.returncode = 0
        mypy_result.stdout = "Success: no issues found"

        with patch("subprocess.run", side_effect=[ruff_result, mypy_result]):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            report = analyzer.analyze()

        assert isinstance(report, QualityReport)
        assert report.quality_score == 10.0
        assert report.ruff_issues == 0
        assert report.mypy_issues == 0

    def test_analyze_with_linting_issues_reduces_score(self, tmp_path):
        """Test that linting issues reduce quality score."""
        # Mock Ruff with JSON issues (--output-format=json returns array)
        ruff_result = Mock()
        ruff_result.returncode = 1
        ruff_result.stdout = json.dumps(
            [
                {
                    "code": "F401",
                    "message": "'os' imported but unused",
                    "location": {"row": 10, "column": 5},
                    "filename": "src/test.py",
                },
                {
                    "code": "E302",
                    "message": "expected 2 blank lines",
                    "location": {"row": 15, "column": 1},
                    "filename": "src/test.py",
                },
            ]
        )

        # Mock MyPy (no errors)
        mypy_result = Mock()
        mypy_result.returncode = 0
        mypy_result.stdout = "Success: no issues found"

        with patch("subprocess.run", side_effect=[ruff_result, mypy_result]):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            report = analyzer.analyze()

        assert report.quality_score < 10.0
        assert report.ruff_issues == 2
        assert report.mypy_issues == 0

    def test_analyze_without_tools_returns_fallback_score(self, tmp_path):
        """Test that missing tools return fallback quality score."""
        # Mock subprocess to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError("ruff not found")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            report = analyzer.analyze()

        # Should still return a report with fallback score
        assert isinstance(report, QualityReport)
        assert report.quality_score >= 0.0


class TestRealDocumentationAnalyzer:
    """Tests for RealDocumentationAnalyzer."""

    def test_init_resolves_project_root(self, tmp_path):
        """Test that project root is resolved during init."""
        analyzer = RealDocumentationAnalyzer(str(tmp_path))

        assert analyzer.project_root == tmp_path.resolve()

    def test_analyze_with_fully_documented_code_returns_100_percent(self, tmp_path):
        """Test that fully documented Python files return 100% score."""
        # Create Python file with full documentation
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text(
            '''"""Module docstring."""

def documented_function():
    """Function docstring."""
    pass

class DocumentedClass:
    """Class docstring."""

    def method(self):
        """Method docstring."""
        pass
'''
        )

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze()

        assert isinstance(report, DocumentationReport)
        assert report.completeness_percentage == 100.0
        assert len(report.missing_docstrings) == 0

    def test_analyze_with_missing_docstrings_returns_lower_score(self, tmp_path):
        """Test that missing docstrings reduce documentation score."""
        # Create Python file with missing docstrings
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.py"
        test_file.write_text(
            """def undocumented_function():
    pass

class UndocumentedClass:
    def method(self):
        pass
"""
        )

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze()

        assert report.completeness_percentage < 100.0
        assert len(report.missing_docstrings) > 0

    def test_analyze_empty_project_returns_100_percent(self, tmp_path):
        """Test that project with no Python files returns 100%."""
        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze()

        # No files = no missing docs = 100%
        assert report.completeness_percentage == 100.0
        assert report.total_functions == 0
        assert len(report.missing_docstrings) == 0


class TestDataclasses:
    """Tests for dataclass instantiation and attributes."""

    def test_coverage_report_creation(self):
        """Test CoverageReport dataclass creation."""
        report = CoverageReport(
            total_coverage=85.5,
            files_analyzed=100,
            uncovered_files=[{"path": "test.py", "coverage": 45.0}],
            missing_lines={"test.py": [10, 11, 12]},
        )

        assert report.total_coverage == 85.5
        assert report.files_analyzed == 100
        assert len(report.uncovered_files) == 1
        assert "test.py" in report.missing_lines

    def test_security_report_creation(self):
        """Test SecurityReport dataclass creation."""
        report = SecurityReport(
            total_issues=17,
            critical_count=0,
            high_count=2,
            medium_count=5,
            low_count=10,
            issues_by_file={"src/test.py": [{"severity": "HIGH", "issue_text": "SQL injection"}]},
            passed=False,
        )

        assert report.critical_count == 0
        assert report.high_count == 2
        assert report.total_issues == 17
        assert len(report.issues_by_file) == 1

    def test_quality_report_creation(self):
        """Test QualityReport dataclass creation."""
        report = QualityReport(
            quality_score=9.5,
            ruff_issues=3,
            mypy_issues=1,
            total_files=10,
            issues_by_category={"unused-import": 2, "type-error": 1, "line-too-long": 1},
            passed=True,
        )

        assert report.quality_score == 9.5
        assert report.ruff_issues == 3
        assert report.mypy_issues == 1
        assert len(report.issues_by_category) == 3

    def test_documentation_report_creation(self):
        """Test DocumentationReport dataclass creation."""
        report = DocumentationReport(
            completeness_percentage=88.5,
            total_functions=50,
            documented_functions=40,
            total_classes=10,
            documented_classes=8,
            missing_docstrings=["function1", "function2"],
            passed=False,
        )

        assert report.completeness_percentage == 88.5
        assert report.total_functions == 50
        assert report.documented_functions == 40
        assert len(report.missing_docstrings) == 2


class TestRealTestGenerator:
    """Tests for RealTestGenerator - LLM-powered test generation."""

    def test_init_creates_output_directory(self, tmp_path):
        """Test that output directory is created on init."""
        output_dir = tmp_path / "tests" / "generated"

        generator = RealTestGenerator(
            project_root=str(tmp_path), output_dir="tests/generated", use_llm=False
        )

        assert generator.project_root == tmp_path.resolve()
        assert generator.output_dir.exists()
        assert generator.output_dir == output_dir

    def test_init_without_api_key_disables_llm(self, tmp_path, monkeypatch):
        """Test that missing API key disables LLM mode."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Mock anthropic import to succeed but no key
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args: (
                __import__(name, *args) if name != "anthropic" else Mock()
            ),
        ):
            generator = RealTestGenerator(
                project_root=str(tmp_path),
                api_key=None,
                use_llm=True,  # Request LLM but no key
            )

        assert generator.use_llm is False  # Should fallback to template mode

    def test_init_with_api_key_enables_llm(self, tmp_path, monkeypatch):
        """Test that API key enables LLM mode."""
        # Mock the Anthropic import
        mock_anthropic_module = Mock()
        mock_client = Mock()
        mock_anthropic_class = Mock(return_value=mock_client)
        mock_anthropic_module.Anthropic = mock_anthropic_class

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            generator = RealTestGenerator(
                project_root=str(tmp_path), api_key="test-key-123", use_llm=True
            )

            assert generator.use_llm is True
            assert generator._llm == mock_client
            mock_anthropic_class.assert_called_once_with(api_key="test-key-123")

    def test_init_with_missing_anthropic_package_disables_llm(self, tmp_path):
        """Test that missing anthropic package disables LLM."""
        # Temporarily remove anthropic from sys.modules if it exists
        import sys

        anthropic_backup = sys.modules.pop("anthropic", None)

        try:
            # Mock import to raise ImportError
            def mock_import(name, *args, **kwargs):
                if name == "anthropic":
                    raise ImportError("No module named 'anthropic'")
                return __import__(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                generator = RealTestGenerator(
                    project_root=str(tmp_path), api_key="test-key", use_llm=True
                )

            assert generator.use_llm is False  # Should fallback
        finally:
            if anthropic_backup:
                sys.modules["anthropic"] = anthropic_backup

    def test_generate_basic_test_template(self, tmp_path):
        """Test basic template generation (no LLM)."""
        # Create source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "example.py"
        source_file.write_text(
            """
def add(a: int, b: int) -> int:
    return a + b
"""
        )

        generator = RealTestGenerator(project_root=str(tmp_path), use_llm=False)

        test_path = generator.generate_tests_for_file(
            str(source_file.relative_to(tmp_path)), missing_lines=[3, 4]
        )

        assert test_path.exists()
        test_content = test_path.read_text()
        assert "import pytest" in test_content
        assert "TestGeneratedCoverage" in test_content
        assert "test_module_imports" in test_content

    def test_generate_tests_for_nonexistent_file_raises_error(self, tmp_path):
        """Test that generating tests for missing file raises RuntimeError."""
        generator = RealTestGenerator(project_root=str(tmp_path), use_llm=False)

        with pytest.raises(RuntimeError, match="Cannot read source file"):
            generator.generate_tests_for_file("nonexistent.py", missing_lines=[1, 2, 3])

    def test_generate_tests_validates_output_path(self, tmp_path):
        """Test that output path is validated for security."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "test.py"
        source_file.write_text("# test")

        generator = RealTestGenerator(project_root=str(tmp_path), use_llm=False)

        # Should not allow writing to system directories
        # The validation happens in _validate_file_path
        test_path = generator.generate_tests_for_file(
            str(source_file.relative_to(tmp_path)), missing_lines=[1]
        )

        # Should generate in output_dir, not system dir
        assert str(test_path).startswith(str(tmp_path))

    def test_generate_llm_tests_with_successful_response(self, tmp_path):
        """Test LLM test generation with successful API call."""
        # Setup mock LLM response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text="""
import pytest

def test_example():
    assert True
"""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        # Mock the Anthropic import
        mock_anthropic_module = Mock()
        mock_anthropic_class = Mock(return_value=mock_client)
        mock_anthropic_module.Anthropic = mock_anthropic_class

        # Create source file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "example.py"
        source_file.write_text("def foo(): pass")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            generator = RealTestGenerator(
                project_root=str(tmp_path), api_key="test-key", use_llm=True
            )

            test_path = generator.generate_tests_for_file(
                str(source_file.relative_to(tmp_path)), missing_lines=[1]
            )

        assert test_path.exists()
        test_content = test_path.read_text()
        assert "import pytest" in test_content
        assert "test_example" in test_content

    def test_generate_llm_tests_with_markdown_wrapped_response(self, tmp_path):
        """Test that LLM response with markdown fences is cleaned."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [
            Mock(
                text="""```python
import pytest

def test_example():
    assert True
```"""
            )
        ]
        mock_client.messages.create.return_value = mock_response

        # Mock the Anthropic import
        mock_anthropic_module = Mock()
        mock_anthropic_class = Mock(return_value=mock_client)
        mock_anthropic_module.Anthropic = mock_anthropic_class

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "example.py"
        source_file.write_text("def foo(): pass")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            generator = RealTestGenerator(
                project_root=str(tmp_path), api_key="test-key", use_llm=True
            )

            test_path = generator.generate_tests_for_file(
                str(source_file.relative_to(tmp_path)), missing_lines=[1]
            )

        test_content = test_path.read_text()
        # Should strip markdown fences
        assert "```python" not in test_content
        assert "import pytest" in test_content

    def test_generate_llm_tests_fallback_on_api_error(self, tmp_path):
        """Test that API errors fallback to template generation."""
        mock_client = Mock()
        # All models fail
        mock_client.messages.create.side_effect = Exception("API Error")

        # Mock the Anthropic import
        mock_anthropic_module = Mock()
        mock_anthropic_class = Mock(return_value=mock_client)
        mock_anthropic_module.Anthropic = mock_anthropic_class

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source_file = src_dir / "example.py"
        source_file.write_text("def foo(): pass")

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            generator = RealTestGenerator(
                project_root=str(tmp_path), api_key="test-key", use_llm=True
            )

            test_path = generator.generate_tests_for_file(
                str(source_file.relative_to(tmp_path)), missing_lines=[1]
            )

        # Should fallback to template
        test_content = test_path.read_text()
        assert "Auto-generated tests" in test_content
        assert "TestGeneratedCoverage" in test_content

    def test_extract_api_docs_with_valid_code(self, tmp_path):
        """Test API extraction from source code."""
        generator = RealTestGenerator(project_root=str(tmp_path), use_llm=False)

        source_code = """
class MyClass:
    def __init__(self, value: int):
        self.value = value

    def process(self) -> str:
        return str(self.value)

def my_function(x: int, y: int) -> int:
    return x + y
"""

        # This should not raise
        api_docs = generator._extract_api_docs(source_code)

        # Should return formatted docs or fallback message
        assert isinstance(api_docs, str)

    def test_extract_api_docs_with_invalid_code(self, tmp_path):
        """Test API extraction with syntax errors returns fallback."""
        generator = RealTestGenerator(project_root=str(tmp_path), use_llm=False)

        invalid_code = "def invalid syntax:"

        api_docs = generator._extract_api_docs(invalid_code)

        # Should return fallback message
        assert "API extraction failed" in api_docs or "use source code carefully" in api_docs


class TestRealTestValidator:
    """Tests for RealTestValidator - validates generated tests."""

    def test_init_resolves_project_root(self, tmp_path):
        """Test that project root is resolved during init."""
        validator = RealTestValidator(str(tmp_path))

        assert validator.project_root == tmp_path.resolve()

    def test_validate_tests_with_passing_tests(self, tmp_path):
        """Test validation of passing tests."""
        # Create a simple passing test
        test_file = tmp_path / "test_example.py"
        test_file.write_text(
            """
import pytest

def test_passes():
    assert True
"""
        )

        mock_result = Mock()
        mock_result.returncode = 0  # Success
        mock_result.stdout = "test_example.py::test_passes PASSED"

        with patch("subprocess.run", return_value=mock_result):
            validator = RealTestValidator(str(tmp_path))
            result = validator.validate_tests([test_file])

        assert result["all_passed"] is True
        assert result["passed_count"] == 1
        assert result["failed_count"] == 0

    def test_validate_tests_with_failing_tests(self, tmp_path):
        """Test validation detects failing tests."""
        test_file = tmp_path / "test_fail.py"
        test_file.write_text(
            """
def test_fails():
    assert False
"""
        )

        mock_result = Mock()
        mock_result.returncode = 1  # Failure
        mock_result.stdout = "test_fail.py::test_fails FAILED"

        with patch("subprocess.run", return_value=mock_result):
            validator = RealTestValidator(str(tmp_path))
            result = validator.validate_tests([test_file])

        assert result["all_passed"] is False
        assert result["passed_count"] == 0
        assert result["failed_count"] == 1

    def test_validate_tests_timeout_raises_runtime_error(self, tmp_path):
        """Test that validation timeout raises RuntimeError."""
        test_file = tmp_path / "test_slow.py"
        test_file.write_text("def test_x(): pass")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 300)):
            validator = RealTestValidator(str(tmp_path))

            with pytest.raises(RuntimeError, match="Test validation timed out"):
                validator.validate_tests([test_file])

    def test_validate_tests_subprocess_error_raises_runtime_error(self, tmp_path):
        """Test that subprocess errors are handled."""
        test_file = tmp_path / "test_error.py"
        test_file.write_text("def test_x(): pass")

        with patch("subprocess.run", side_effect=OSError("Command failed")):
            validator = RealTestValidator(str(tmp_path))

            with pytest.raises(RuntimeError, match="Test validation failed"):
                validator.validate_tests([test_file])

    def test_validate_tests_limits_output_size(self, tmp_path):
        """Test that output is limited to prevent memory issues."""
        test_file = tmp_path / "test_large.py"
        test_file.write_text("def test_x(): pass")

        # Create large output (>1000 chars)
        large_output = "x" * 2000
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = large_output

        with patch("subprocess.run", return_value=mock_result):
            validator = RealTestValidator(str(tmp_path))
            result = validator.validate_tests([test_file])

        # Output should be limited
        assert len(result["output"]) <= 1000


class TestRealCoverageAnalyzerEdgeCases:
    """Additional edge case tests for RealCoverageAnalyzer."""

    def test_analyze_timeout_uses_partial_results(self, tmp_path):
        """Test that timeout allows using partial coverage.json."""
        # Create coverage.json first
        coverage_file = tmp_path / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 75.0}, "files": {}}
        coverage_file.write_text(json.dumps(coverage_data))

        # Mock subprocess to timeout
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 600)):
            analyzer = RealCoverageAnalyzer(str(tmp_path))
            result = analyzer.analyze(use_existing=False)

        # Should use existing file despite timeout
        assert result.total_coverage == 75.0

    def test_analyze_json_decode_error_raises_runtime_error(self, tmp_path):
        """Test that invalid JSON raises RuntimeError."""
        coverage_file = tmp_path / "coverage.json"
        coverage_file.write_text("invalid json{{{")

        analyzer = RealCoverageAnalyzer(str(tmp_path))

        with pytest.raises(RuntimeError, match="Coverage analysis failed"):
            analyzer.analyze()


class TestRealSecurityAuditorEdgeCases:
    """Additional edge case tests for RealSecurityAuditor."""

    def test_audit_with_invalid_json_returns_clean_report(self, tmp_path):
        """Test that invalid Bandit JSON returns clean report (graceful fallback)."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        with patch("subprocess.run", return_value=mock_result):
            auditor = RealSecurityAuditor(str(tmp_path))
            report = auditor.audit()

        # Should return clean report as fallback
        assert report.total_issues == 0
        assert report.passed is True

    def test_audit_timeout_raises_runtime_error(self, tmp_path):
        """Test that audit timeout raises RuntimeError."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("bandit", 300)):
            auditor = RealSecurityAuditor(str(tmp_path))

            with pytest.raises(RuntimeError, match="Security audit timed out"):
                auditor.audit()

    def test_audit_with_critical_severity_issues(self, tmp_path):
        """Test that CRITICAL severity issues are counted."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "CRITICAL",
                        "issue_confidence": "HIGH",
                        "issue_text": "Critical security flaw",
                        "filename": "src/bad.py",
                        "line_number": 10,
                        "test_id": "B501",
                    }
                ]
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            auditor = RealSecurityAuditor(str(tmp_path))
            report = auditor.audit()

        assert report.critical_count == 1
        assert report.passed is False  # Critical issues fail

    def test_audit_groups_issues_by_file(self, tmp_path):
        """Test that issues are grouped by filename."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "MEDIUM",
                        "filename": "src/file1.py",
                        "line_number": 10,
                        "test_id": "B101",
                        "issue_text": "Issue 1",
                        "issue_confidence": "HIGH",
                    },
                    {
                        "issue_severity": "MEDIUM",
                        "filename": "src/file1.py",
                        "line_number": 20,
                        "test_id": "B102",
                        "issue_text": "Issue 2",
                        "issue_confidence": "MEDIUM",
                    },
                    {
                        "issue_severity": "LOW",
                        "filename": "src/file2.py",
                        "line_number": 5,
                        "test_id": "B103",
                        "issue_text": "Issue 3",
                        "issue_confidence": "LOW",
                    },
                ]
            }
        )

        with patch("subprocess.run", return_value=mock_result):
            auditor = RealSecurityAuditor(str(tmp_path))
            report = auditor.audit()

        assert len(report.issues_by_file) == 2
        assert len(report.issues_by_file["src/file1.py"]) == 2
        assert len(report.issues_by_file["src/file2.py"]) == 1


class TestRealCodeQualityAnalyzerEdgeCases:
    """Additional edge case tests for RealCodeQualityAnalyzer."""

    def test_analyze_counts_python_files(self, tmp_path):
        """Test that analyzer counts Python files in target."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "file1.py").write_text("# file1")
        (src_dir / "file2.py").write_text("# file2")
        (src_dir / "file3.py").write_text("# file3")

        # Mock Ruff and MyPy
        with patch("subprocess.run", return_value=Mock(returncode=0, stdout="[]")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            report = analyzer.analyze(target_path="src")

        assert report.total_files == 3

    def test_run_ruff_with_file_not_found_returns_zero(self, tmp_path):
        """Test that missing Ruff returns 0 issues."""
        with patch("subprocess.run", side_effect=FileNotFoundError("ruff not found")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            issues = analyzer._run_ruff("src")

        assert issues == 0

    def test_run_ruff_with_exception_returns_zero(self, tmp_path):
        """Test that Ruff exceptions are handled gracefully."""
        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            issues = analyzer._run_ruff("src")

        assert issues == 0

    def test_run_mypy_with_file_not_found_returns_zero(self, tmp_path):
        """Test that missing MyPy returns 0 issues."""
        with patch("subprocess.run", side_effect=FileNotFoundError("mypy not found")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            issues = analyzer._run_mypy("src")

        assert issues == 0

    def test_run_mypy_with_exception_returns_zero(self, tmp_path):
        """Test that MyPy exceptions are handled gracefully."""
        with patch("subprocess.run", side_effect=Exception("Unexpected error")):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            issues = analyzer._run_mypy("src")

        assert issues == 0

    def test_run_mypy_counts_error_lines(self, tmp_path):
        """Test that MyPy error lines are counted correctly."""
        mock_result = Mock()
        mock_result.stdout = """
src/file1.py:10: error: Type mismatch
src/file1.py:20: error: Missing return type
src/file2.py:5: error: Incompatible types
"""

        with patch("subprocess.run", return_value=mock_result):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            issues = analyzer._run_mypy("src")

        assert issues == 3  # Three ": error:" lines

    def test_quality_score_calculation(self, tmp_path):
        """Test quality score calculation formula."""
        # Create a test file to count
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "test.py").write_text("# test")

        # Mock 300 ruff issues (to hit cap) and 100 mypy issues (to hit cap)
        ruff_result = Mock(returncode=1, stdout=json.dumps([{"code": "E501"}] * 300))
        # MyPy counts lines with ": error:" - provide 100 such lines
        mypy_output = "\n".join([f"file.py:{i}: error: test" for i in range(100)])
        mypy_result = Mock(returncode=1, stdout=mypy_output)

        with patch("subprocess.run", side_effect=[ruff_result, mypy_result]):
            analyzer = RealCodeQualityAnalyzer(str(tmp_path))
            report = analyzer.analyze()

        # Score starts at 10.0
        # -3.0 for ruff (capped at 3.0: min(300 * 0.01, 3.0) = min(3.0, 3.0))
        # -2.0 for mypy (capped at 2.0: min(100 * 0.02, 2.0) = min(2.0, 2.0))
        # = 10.0 - 3.0 - 2.0 = 5.0
        assert report.quality_score == 5.0
        assert report.ruff_issues == 300
        assert report.mypy_issues == 100
        assert report.passed is False  # < 7.0


class TestRealDocumentationAnalyzerEdgeCases:
    """Additional edge case tests for RealDocumentationAnalyzer."""

    def test_analyze_skips_dunder_files(self, tmp_path):
        """Test that __init__.py and __main__.py are skipped."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "__init__.py").write_text(
            """
def public_function():
    pass
"""
        )
        (src_dir / "__main__.py").write_text(
            """
def main():
    pass
"""
        )

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze(target_path="src")

        # Should skip both files
        assert report.total_functions == 0

    def test_analyze_handles_parse_errors_gracefully(self, tmp_path):
        """Test that syntax errors in files are handled gracefully."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "broken.py").write_text("def invalid syntax:")
        (src_dir / "valid.py").write_text(
            """
def valid_function():
    '''Documented'''
    pass
"""
        )

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze(target_path="src")

        # Should process valid.py and skip broken.py
        assert report.total_functions == 1
        assert report.documented_functions == 1

    def test_analyze_counts_private_vs_public(self, tmp_path):
        """Test that private functions/classes are not counted."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "test.py").write_text(
            """
def public_function():
    pass

def _private_function():
    pass

class PublicClass:
    pass

class _PrivateClass:
    pass
"""
        )

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze(target_path="src")

        # Should only count public items
        assert report.total_functions == 1  # Only public_function
        assert report.total_classes == 1  # Only PublicClass

    def test_analyze_limits_missing_docstrings_to_10(self, tmp_path):
        """Test that missing docstrings are limited to first 10."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create file with 20 undocumented functions
        functions = "\n".join([f"def func{i}(): pass" for i in range(20)])
        (src_dir / "many.py").write_text(functions)

        analyzer = RealDocumentationAnalyzer(str(tmp_path))
        report = analyzer.analyze(target_path="src")

        assert report.total_functions == 20
        assert len(report.missing_docstrings) == 10  # Limited to 10


class TestToolRegistry:
    """Tests for REAL_TOOLS registry."""

    def test_all_tools_are_registered(self):
        """Test that all tool classes are in the registry."""
        expected_tools = {
            "coverage_analyzer",
            "test_generator",
            "test_validator",
            "security_auditor",
            "code_quality_analyzer",
            "documentation_analyzer",
        }

        assert set(REAL_TOOLS.keys()) == expected_tools

    def test_all_registered_tools_are_callable(self):
        """Test that all registered tools can be instantiated."""
        for _tool_name, tool_class in REAL_TOOLS.items():
            # Should be callable
            assert callable(tool_class)

            # Should be able to instantiate (will use current dir)
            instance = tool_class()
            assert instance is not None
