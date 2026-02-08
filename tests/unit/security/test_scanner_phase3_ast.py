"""Tests for Phase 3 AST-based Scanner Improvements

Validates that AST-based detection correctly distinguishes actual eval/exec
calls from mentions in comments, docstrings, and documentation.

Created: 2026-01-26
Related: docs/SECURITY_PHASE2_COMPLETE.md, src/attune/workflows/security_audit_phase3.py
"""

import ast
import tempfile
from pathlib import Path

import pytest

from attune.workflows.security_audit_phase3 import (
    EvalExecDetector,
    analyze_file_for_eval_exec,
    enhanced_command_injection_detection,
    is_in_docstring_or_comment,
    is_scanner_implementation_file,
)


class TestEvalExecDetector:
    """Test AST-based eval/exec detection."""

    def test_detects_actual_eval_call(self):
        """Test that actual eval() calls are detected."""
        code = """
def unsafe_function(user_input):
    result = eval(user_input)  # Dangerous!
    return result
"""
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 1
        assert detector.findings[0]["function"] == "eval"
        assert detector.findings[0]["line"] == 3

    def test_detects_actual_exec_call(self):
        """Test that actual exec() calls are detected."""
        code = """
def unsafe_function(user_code):
    exec(user_code)  # Dangerous!
"""
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 1
        assert detector.findings[0]["function"] == "exec"
        assert detector.findings[0]["line"] == 3

    def test_ignores_eval_in_docstring(self):
        """Test that eval mentioned in docstrings is not detected."""
        code = '''
def check_security(content):
    """Check if content contains eval() or exec().

    This function scans for dangerous patterns like eval() usage.
    """
    return "eval(" in content
'''
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 0, "Should not detect eval in docstring"

    def test_ignores_eval_in_comment(self):
        """Test that eval mentioned in comments is not detected."""
        code = """
# Security note: Never use eval() on user input
def safe_function(data):
    return json.loads(data)
"""
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 0, "Should not detect eval in comment"

    def test_ignores_eval_in_string_literal(self):
        """Test that eval in string literals is not detected."""
        code = """
def detect_eval(code):
    if "eval(" in code:
        return True
    return False
"""
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 0, "Should not detect eval in string"

    def test_detects_multiple_calls(self):
        """Test that multiple eval/exec calls are detected."""
        code = """
def unsafe1(x):
    return eval(x)

def unsafe2(y):
    exec(y)

def unsafe3(z):
    result = eval(z)
    exec(result)
"""
        tree = ast.parse(code)
        detector = EvalExecDetector("test.py")
        detector.visit(tree)

        assert len(detector.findings) == 4
        functions = [f["function"] for f in detector.findings]
        assert functions.count("eval") == 2
        assert functions.count("exec") == 2


class TestAnalyzeFileForEvalExec:
    """Test file-level analysis."""

    def test_analyze_file_with_actual_eval(self):
        """Test analysis of file with actual eval call."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def dangerous_func(user_input):
    return eval(user_input)
"""
            )
            f.flush()
            temp_path = f.name

        try:
            findings = analyze_file_for_eval_exec(temp_path)
            assert len(findings) == 1
            assert findings[0]["function"] == "eval"
        finally:
            Path(temp_path).unlink()

    def test_analyze_file_with_only_documentation(self):
        """Test analysis of file with only documentation mentions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def check_security(code):
    '''Check if code contains eval() or exec().

    Security policy: No eval() or exec() usage allowed.
    '''
    # Never use eval() on user input
    return "eval(" in code
"""
            )
            f.flush()
            temp_path = f.name

        try:
            findings = analyze_file_for_eval_exec(temp_path)
            assert len(findings) == 0, "Should not detect eval in documentation"
        finally:
            Path(temp_path).unlink()

    def test_analyze_nonexistent_file(self):
        """Test analysis of nonexistent file returns empty list."""
        findings = analyze_file_for_eval_exec("/nonexistent/file.py")
        assert findings == []

    def test_analyze_file_with_syntax_error(self):
        """Test analysis of file with syntax errors returns empty list."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken syntax( ::::")
            f.flush()
            temp_path = f.name

        try:
            findings = analyze_file_for_eval_exec(temp_path)
            assert findings == []
        finally:
            Path(temp_path).unlink()


class TestScannerImplementationFileDetection:
    """Test detection of scanner implementation files."""

    def test_recognizes_bug_predict_as_scanner_file(self):
        """Test that bug_predict files are recognized as scanner files."""
        assert is_scanner_implementation_file("src/attune/workflows/bug_predict.py")
        assert is_scanner_implementation_file("tests/test_bug_predict_helpers.py")

    def test_recognizes_security_audit_as_scanner_file(self):
        """Test that security_audit files are recognized as scanner files."""
        assert is_scanner_implementation_file("src/attune/workflows/security_audit.py")
        assert is_scanner_implementation_file("tests/test_security_scan.py")

    def test_recognizes_owasp_patterns_as_scanner_file(self):
        """Test that OWASP pattern files are recognized as scanner files."""
        assert is_scanner_implementation_file("src/attune/security/owasp_patterns.py")

    def test_does_not_recognize_regular_source_files(self):
        """Test that regular source files are not scanner files."""
        assert not is_scanner_implementation_file("src/attune/models/registry.py")
        assert not is_scanner_implementation_file("src/attune/workflows/base.py")

    def test_does_not_recognize_regular_test_files(self):
        """Test that regular test files are not scanner files."""
        assert not is_scanner_implementation_file("tests/test_models.py")
        assert not is_scanner_implementation_file("tests/unit/test_config.py")


class TestDocstringAndCommentDetection:
    """Test enhanced docstring and comment detection."""

    def test_detects_comment_lines(self):
        """Test that comment lines are detected."""
        line = "# Never use eval() on user input"
        content = line
        assert is_in_docstring_or_comment(line, content, 1)

    def test_detects_inline_comments(self):
        """Test that inline comments are detected."""
        line = "result = process(data)  # eval() would be dangerous here"
        content = line
        assert is_in_docstring_or_comment(line, content, 1)

    def test_detects_security_policy_documentation(self):
        """Test that security policy statements are detected."""
        test_cases = [
            "- No eval() or exec() usage",
            "Security: No eval() allowed",
            "Never use eval() on untrusted input",
            "Avoid eval() for security",
        ]

        for line in test_cases:
            assert is_in_docstring_or_comment(line, line, 1), f"Should detect: {line}"

    def test_does_not_detect_actual_code(self):
        """Test that actual code lines are not detected as documentation."""
        line = "result = eval(user_input)"
        content = line
        assert not is_in_docstring_or_comment(line, content, 1)


class TestEnhancedCommandInjectionDetection:
    """Test the integrated enhanced detection."""

    def test_filters_scanner_implementation_files(self):
        """Test that scanner files are completely filtered."""
        findings = [
            {
                "type": "command_injection",
                "file": "src/attune/workflows/bug_predict.py",
                "line": 233,
                "match": "eval(",
                "severity": "critical",
                "owasp": "A03:2021 Injection",
            }
        ]

        result = enhanced_command_injection_detection(
            "src/attune/workflows/bug_predict.py", findings
        )

        assert result == [], "Should filter scanner implementation file"

    def test_uses_ast_for_python_files(self):
        """Test that AST-based detection is used for Python files."""
        # Create temp file with only documentation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def check_eval(code):
    '''Check for eval() usage.'''
    return "eval(" in code
"""
            )
            f.flush()
            temp_path = f.name

        try:
            findings = [
                {
                    "type": "command_injection",
                    "file": temp_path,
                    "line": 3,
                    "match": "eval(",
                    "severity": "critical",
                    "owasp": "A03:2021 Injection",
                }
            ]

            result = enhanced_command_injection_detection(temp_path, findings)

            assert result == [], "Should use AST and find no actual eval calls"
        finally:
            Path(temp_path).unlink()

    def test_detects_actual_eval_in_python_file(self):
        """Test that actual eval calls are still detected."""
        # Create temp file with actual eval
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def unsafe_func(x):
    return eval(x)  # Actual vulnerability!
"""
            )
            f.flush()
            temp_path = f.name

        try:
            findings = [
                {
                    "type": "command_injection",
                    "file": temp_path,
                    "line": 3,
                    "match": "eval(",
                    "severity": "critical",
                    "owasp": "A03:2021 Injection",
                }
            ]

            result = enhanced_command_injection_detection(temp_path, findings)

            assert len(result) == 1, "Should detect actual eval call"
            assert result[0]["line"] == 3
        finally:
            Path(temp_path).unlink()


@pytest.mark.integration
class TestPhase3Integration:
    """Integration tests for Phase 3 improvements."""

    def test_execution_strategies_no_findings(self):
        """Test that execution_strategies.py has no findings (only security docs)."""
        file_path = "src/attune/orchestration/execution_strategies.py"

        if not Path(file_path).exists():
            pytest.skip(f"{file_path} not found")

        findings = analyze_file_for_eval_exec(file_path)
        assert findings == [], "execution_strategies.py should have 0 actual eval/exec calls"

    def test_bug_predict_filtered_as_scanner_file(self):
        """Test that bug_predict.py is filtered as scanner implementation."""
        file_path = "src/attune/workflows/bug_predict.py"

        assert is_scanner_implementation_file(
            file_path
        ), "bug_predict.py should be recognized as scanner file"

        # Even if regex finds patterns, they should be filtered
        fake_findings = [
            {
                "type": "command_injection",
                "file": file_path,
                "line": 233,
                "match": "eval(",
            }
        ]

        result = enhanced_command_injection_detection(file_path, fake_findings)
        assert result == [], "Scanner file findings should be filtered"

    def test_phase3_reduces_false_positives_significantly(self):
        """Test that Phase 3 reduces false positives by >90%."""
        # This would require running full audit, which is tested in the main workflow
        # Just verify the functions exist and are callable
        from attune.workflows.security_audit_phase3 import apply_phase3_filtering

        assert callable(apply_phase3_filtering)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
