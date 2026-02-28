"""Tests for security_audit_phase3.py.

Covers untested branches in is_in_docstring_or_comment() and
enhanced_command_injection_detection() to push coverage from 53.3% to 80%+.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from attune.workflows.security_audit_phase3 import (
    enhanced_command_injection_detection,
    is_in_docstring_or_comment,
)

# ---------------------------------------------------------------------------
# is_in_docstring_or_comment
# ---------------------------------------------------------------------------


class TestIsInDocstringOrComment:
    """Tests for is_in_docstring_or_comment()."""

    def test_comment_line_returns_true(self) -> None:
        """Lines starting with # are always in a comment."""
        assert is_in_docstring_or_comment("# eval(x) is dangerous", "", 1) is True

    def test_inline_comment_before_eval_returns_true(self) -> None:
        """Inline comment marker before 'eval' in line → comment context."""
        line = '    x = 1  # never use eval("x")'
        assert is_in_docstring_or_comment(line, line + "\n", 1) is True

    def test_line_in_function_docstring_returns_true(self) -> None:
        """Line content appearing inside a function docstring → True."""
        file_content = '''\
def foo():
    """Never use eval() directly.

    This is a security note: no eval allowed.
    """
    pass
'''
        line = "    Never use eval() directly."
        assert is_in_docstring_or_comment(line, file_content, 3) is True

    def test_line_in_module_docstring_returns_true(self) -> None:
        """Line appearing in module docstring → True."""
        file_content = '''\
"""Security policy: no eval, no exec.

Do not use eval() anywhere.
"""

x = 1
'''
        assert is_in_docstring_or_comment("Do not use eval() anywhere.", file_content, 3) is True

    def test_syntax_error_in_file_no_security_pattern(self) -> None:
        """SyntaxError swallowed; line has no security pattern and no 'eval' → True.

        The inline-comment check (line 163-169) evaluates to True when 'eval'
        is NOT in line_content because the ternary condition defaults to True.
        """
        invalid_python = "def foo(:\n    pass\n"
        # 'eval' not in line → ternary defaults to True → inline check returns True
        assert is_in_docstring_or_comment("result = 1", invalid_python, 1) is True

    def test_syntax_error_with_security_pattern_returns_true(self) -> None:
        """SyntaxError swallowed, but line contains 'no eval' → True."""
        invalid_python = "def foo(:\n"
        assert is_in_docstring_or_comment("no eval allowed", invalid_python, 1) is True

    def test_security_pattern_no_eval_returns_true(self) -> None:
        """Lines containing 'no eval' security policy → True."""
        assert is_in_docstring_or_comment("no eval", "no eval\n", 1) is True

    def test_security_pattern_never_use_exec_returns_true(self) -> None:
        """Lines containing 'never use exec' → True."""
        assert is_in_docstring_or_comment("never use exec", "never use exec\n", 1) is True

    def test_security_pattern_avoid_eval_returns_true(self) -> None:
        """Lines containing 'avoid eval' → True."""
        assert is_in_docstring_or_comment("avoid eval here", "avoid eval here\n", 1) is True

    def test_line_with_eval_not_in_comment_returns_false(self) -> None:
        """Code line containing 'eval' where '#' does not precede it → False.

        When 'eval' IS in the line, the ternary checks whether '#' appears
        before 'eval'. If there's no '#', index('#') raises ValueError → False.
        """
        file_content = "result = eval(user_input)\n"
        assert is_in_docstring_or_comment("result = eval(user_input)", file_content, 1) is False


# ---------------------------------------------------------------------------
# enhanced_command_injection_detection — fallback path (non-Python / AST fail)
# ---------------------------------------------------------------------------


class TestEnhancedCommandInjectionDetectionFallback:
    """Tests for the non-Python and AST-failure fallback paths."""

    def test_non_python_file_line_in_comment_filtered_out(self) -> None:
        """Non-Python file: line that starts with '#' is filtered out."""
        with tempfile.NamedTemporaryFile(
            suffix=".sh", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("#!/bin/bash\n# eval is used here for templating\neval $cmd\n")
            tmp_path = tmp.name

        try:
            findings = [{"line": 2, "match": "eval", "type": "command_injection"}]
            result = enhanced_command_injection_detection(tmp_path, findings)
            # Line 2 is a comment → filtered
            assert all(f.get("line") != 2 for f in result)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_non_python_file_real_code_kept(self) -> None:
        """Non-Python file: code line not in comment is kept."""
        with tempfile.NamedTemporaryFile(
            suffix=".sh", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("#!/bin/bash\neval $user_input\n")
            tmp_path = tmp.name

        try:
            findings = [{"line": 2, "match": "eval $user_input", "type": "command_injection"}]
            result = enhanced_command_injection_detection(tmp_path, findings)
            assert any(f.get("line") == 2 for f in result)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_read_text_oserror_returns_original_findings(self) -> None:
        """OSError reading non-Python file → returns original_findings unchanged."""
        findings = [{"line": 1, "match": "eval", "type": "command_injection"}]
        result = enhanced_command_injection_detection("/nonexistent/path.sh", findings)
        assert result == findings

    def test_ast_exception_falls_back_to_text_filter(self) -> None:
        """When AST import fails for a .py file, falls back to text-based filter."""
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("# eval is documented here\nsome_func()\n")
            tmp_path = tmp.name

        try:
            findings = [{"line": 1, "match": "eval", "type": "command_injection"}]
            # Patch analyze_file_for_eval_exec to raise so AST branch fails
            with patch(
                "attune.workflows.security_audit_phase3.analyze_file_for_eval_exec",
                side_effect=RuntimeError("ast unavailable"),
            ):
                result = enhanced_command_injection_detection(tmp_path, findings)
            # Fallback: line 1 is a comment → filtered out
            assert result == []
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_finding_with_out_of_range_line_is_dropped(self) -> None:
        """Finding with line number beyond file length is excluded.

        The condition `0 < line_num <= len(lines)` is False for line 99 in a
        1-line file, so the finding is not appended to filtered.
        """
        with tempfile.NamedTemporaryFile(
            suffix=".sh", mode="w", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write("echo hello\n")
            tmp_path = tmp.name

        try:
            findings = [{"line": 99, "match": "eval", "type": "command_injection"}]
            result = enhanced_command_injection_detection(tmp_path, findings)
            # line 99 > len(lines)=1 → not appended → not in result
            assert all(f.get("line") != 99 for f in result)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
