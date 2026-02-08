"""Phase 3 Scanner Improvements - AST-based Command Injection Detection

This module provides AST-based analysis for detecting actual eval/exec usage
vs mentions in comments, docstrings, and documentation.

Created: 2026-01-26
Related: docs/SECURITY_PHASE2_COMPLETE.md
"""

import ast
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EvalExecDetector(ast.NodeVisitor):
    """AST visitor that detects actual eval() and exec() calls.

    This visitor walks the AST to find real function calls to eval() and exec(),
    distinguishing them from:
    - String literals mentioning eval/exec
    - Comments mentioning eval/exec
    - Docstrings documenting security policies
    - Detection code checking for eval/exec patterns
    """

    def __init__(self, file_path: str):
        """Initialize detector.

        Args:
            file_path: Path to file being analyzed (for context)
        """
        self.file_path = file_path
        self.findings: list[dict[str, Any]] = []
        self._in_docstring = False
        self._current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to track context."""
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = None

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call nodes to detect eval/exec."""
        # Check if this is a call to eval() or exec()
        func_name = None

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle attribute access like obj.exec()
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            # Found a real eval/exec call!
            self.findings.append(
                {
                    "type": "command_injection",
                    "function": func_name,
                    "line": node.lineno,
                    "col": node.col_offset,
                    "context": self._current_function,
                }
            )

        self.generic_visit(node)


def analyze_file_for_eval_exec(file_path: str | Path) -> list[dict[str, Any]]:
    """Analyze a Python file for actual eval/exec usage using AST.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        List of findings (actual eval/exec calls)

    Example:
        >>> findings = analyze_file_for_eval_exec("myfile.py")
        >>> for finding in findings:
        ...     print(f"{finding['function']} at line {finding['line']}")
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))

        detector = EvalExecDetector(str(file_path))
        detector.visit(tree)

        return detector.findings

    except SyntaxError as e:
        logger.debug(f"Syntax error parsing {file_path}: {e}")
        return []
    except Exception as e:
        logger.debug(f"Error analyzing {file_path}: {e}")
        return []


def is_scanner_implementation_file(file_path: str) -> bool:
    """Check if file is part of security scanner implementation.

    Scanner files legitimately contain eval/exec patterns for detection
    purposes and should not be flagged.

    Args:
        file_path: Path to check

    Returns:
        True if this is a scanner implementation file
    """
    scanner_indicators = [
        # Scanner implementation files
        "bug_predict",
        "security_audit",
        "security_scan",
        "vulnerability_scan",
        "owasp",
        "secrets_detector",
        "pii_scrubber",
        # Pattern/rule definition files
        "patterns.py",
        "rules.py",
        "checks.py",
        # Test files for security scanners
        "test_bug_predict",
        "test_security",
        "test_scanner",
    ]

    path_lower = file_path.lower()
    return any(indicator in path_lower for indicator in scanner_indicators)


def is_in_docstring_or_comment(line_content: str, file_content: str, line_num: int) -> bool:
    """Enhanced check if line is in docstring or comment.

    Phase 3 Enhancement: More robust detection of documentation context.

    Args:
        line_content: The line to check
        file_content: Full file content
        line_num: Line number (1-indexed)

    Returns:
        True if line is in docstring or comment
    """
    line = line_content.strip()

    # Check for comment lines
    if line.startswith("#"):
        return True

    # Check for inline comments
    if (
        "#" in line_content and line_content.index("#") < line_content.find("eval")
        if "eval" in line_content
        else True
    ):
        return True

    # Parse file as AST to find docstrings
    try:
        tree = ast.parse(file_content)

        # Get all docstrings - only from nodes that can have docstrings
        docstrings = []
        for node in ast.walk(tree):
            # Only these node types can have docstrings
            if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef | ast.Module):
                docstring = ast.get_docstring(node)
                if docstring:
                    docstrings.append(docstring)

        # Check if any docstring contains this line content
        for docstring in docstrings:
            if line_content.strip() in docstring:
                return True

    except SyntaxError:
        pass

    # Check for security policy patterns
    security_patterns = [
        "no eval",
        "no exec",
        "never use eval",
        "never use exec",
        "avoid eval",
        "avoid exec",
        "security:",
        "- no eval",
        "- no exec",
    ]

    line_lower = line.lower()
    if any(pattern in line_lower for pattern in security_patterns):
        return True

    return False


def enhanced_command_injection_detection(
    file_path: str, original_findings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Enhanced command injection detection with AST-based filtering.

    Phase 3: Uses AST to distinguish actual eval/exec calls from mentions
    in documentation, comments, and scanner implementation.

    Args:
        file_path: Path to file being analyzed
        original_findings: Findings from regex-based detection

    Returns:
        Filtered list of actual vulnerabilities (not false positives)
    """
    # Step 1: Check if this is a scanner implementation file
    if is_scanner_implementation_file(file_path):
        return []  # Scanner files are allowed to mention eval/exec

    # Step 2: For Python files, use AST-based detection for eval/exec only
    # Keep subprocess findings from regex detection
    if file_path.endswith(".py"):
        try:
            # Separate eval/exec findings from subprocess/os.system findings
            # Eval/exec findings will be replaced with AST-based findings
            # Subprocess/os.system findings will be kept from regex detection
            eval_exec_findings = []
            subprocess_findings = []

            for finding in original_findings:
                match_text = finding.get("match", "").lower()
                if "eval" in match_text or "exec" in match_text:
                    eval_exec_findings.append(finding)
                else:
                    # subprocess, os.system, or other command injection patterns
                    subprocess_findings.append(finding)

            # Use AST to validate eval/exec findings (reduces false positives)
            ast_findings = analyze_file_for_eval_exec(file_path)

            # Check if this is a test file (downgrade severity)
            from .security_audit import TEST_FILE_PATTERNS

            is_test_file = any(re.search(pat, file_path) for pat in TEST_FILE_PATTERNS)

            # Convert AST findings to format compatible with original
            filtered = []
            for finding in ast_findings:
                filtered.append(
                    {
                        "type": "command_injection",
                        "file": file_path,
                        "line": finding["line"],
                        "match": f"{finding['function']}(",
                        "severity": "low" if is_test_file else "critical",
                        "owasp": "A03:2021 Injection",
                        "context": finding.get("context", ""),
                        "is_test": is_test_file,
                    }
                )

            # Keep subprocess/os.system findings (not filtered by AST)
            filtered.extend(subprocess_findings)

            return filtered

        except Exception as e:
            logger.debug(f"AST analysis failed for {file_path}, falling back to regex: {e}")
            # Fall back to original findings if AST fails
            pass

    # Step 3: For non-Python files or if AST fails, filter original findings
    try:
        file_content = Path(file_path).read_text(encoding="utf-8", errors="ignore")

        filtered = []
        for finding in original_findings:
            line_num = finding.get("line", 0)
            lines = file_content.split("\n")

            if 0 < line_num <= len(lines):
                line_content = lines[line_num - 1]

                # Skip if in docstring or comment
                if is_in_docstring_or_comment(line_content, file_content, line_num):
                    continue

                filtered.append(finding)

        return filtered

    except Exception as e:
        logger.debug(f"Enhanced filtering failed for {file_path}: {e}")
        return original_findings


# =============================================================================
# Integration with SecurityAuditWorkflow
# =============================================================================


def apply_phase3_filtering(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply Phase 3 AST-based filtering to command injection findings.

    This is the main entry point for Phase 3 improvements.

    Args:
        findings: List of command injection findings from regex-based detection
                 (should only contain command_injection type)

    Returns:
        Filtered list with false positives removed
    """
    if not findings:
        return []

    # Group findings by file
    by_file: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        file_path = finding.get("file", "")
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(finding)

    # Apply enhanced detection per file
    filtered_findings = []
    for file_path, file_findings in by_file.items():
        enhanced = enhanced_command_injection_detection(file_path, file_findings)
        filtered_findings.extend(enhanced)

    return filtered_findings


if __name__ == "__main__":
    # Test on known files
    test_files = [
        "src/attune/workflows/bug_predict.py",
        "src/attune/orchestration/execution_strategies.py",
        "tests/test_bug_predict_workflow.py",
    ]

    for file in test_files:
        if Path(file).exists():
            findings = analyze_file_for_eval_exec(file)
            print(f"\n{file}:")
            print(f"  Actual eval/exec calls: {len(findings)}")
            for f in findings:
                print(f"    Line {f['line']}: {f['function']}() in {f.get('context', 'module')}")
        else:
            print(f"\n{file}: Not found")
