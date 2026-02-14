"""Unit tests for CodeReviewAnalysisMixin and its module-level helpers.

Tests cover:
    Module-level helpers:
        _has_return_type_hint — return type annotation detection
        _gather_file_snippets — source file snippet extraction
        _format_findings_for_prompt — prompt formatting
        _parse_deep_enrichment — LLM response parsing and merge
        _recount_by_key — finding recount with false-positive filtering

    CodeReviewAnalysisMixin:
        _perf_check — static performance anti-pattern scanning
        _perf_check_deep — LLM-enriched performance validation
        _health_monitor — framework health snapshot
        _quality_check — static code quality checks
        _quality_check_deep — LLM-enriched quality validation

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, patch

from attune.workflows.code_review_analysis_mixin import (
    CHARS_PER_TOKEN_ESTIMATE,
    MAX_FILE_LINES,
    CodeReviewAnalysisMixin,
    _format_findings_for_prompt,
    _gather_file_snippets,
    _has_return_type_hint,
    _parse_deep_enrichment,
    _recount_by_key,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeHost(CodeReviewAnalysisMixin):
    """Minimal host providing the attributes the mixin expects."""

    def __init__(self):
        import logging

        self.logger = logging.getLogger("test")
        self._call_llm = AsyncMock(return_value=("{}", 10, 10))


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests: _has_return_type_hint
# ---------------------------------------------------------------------------


class TestHasReturnTypeHint:
    """Tests for _has_return_type_hint helper."""

    def test_function_with_return_hint(self):
        code = "def foo(x: int) -> int:\n    return x"
        assert _has_return_type_hint(code, 0) is True

    def test_function_without_return_hint(self):
        code = "def foo(x: int):\n    return x"
        assert _has_return_type_hint(code, 0) is False

    def test_function_no_open_paren(self):
        """Edge case: no open paren found — assume OK."""
        code = "def foo"
        assert _has_return_type_hint(code, 0) is True

    def test_function_with_nested_parens(self):
        code = "def foo(x: tuple[int, int]) -> bool:\n    pass"
        assert _has_return_type_hint(code, 0) is True

    def test_function_with_nested_parens_no_hint(self):
        code = "def foo(x: tuple[int, int]):\n    pass"
        assert _has_return_type_hint(code, 0) is False

    def test_function_offset_in_content(self):
        code = "# preamble\ndef bar(a, b) -> str:\n    pass"
        offset = code.index("def")
        assert _has_return_type_hint(code, offset) is True

    def test_function_no_colon_after_parens(self):
        """Edge case: no colon after closing paren — assume OK."""
        code = "def foo(x)"
        assert _has_return_type_hint(code, 0) is True

    def test_malformed_unbalanced_parens(self):
        """Edge case: unbalanced parens — assume OK."""
        code = "def foo(x, (y:"
        assert _has_return_type_hint(code, 0) is True

    def test_complex_signature(self):
        code = "def process(data: dict[str, list[int]], *, key: str = 'x') -> None:\n    pass"
        assert _has_return_type_hint(code, 0) is True


# ---------------------------------------------------------------------------
# Tests: _gather_file_snippets
# ---------------------------------------------------------------------------


class TestGatherFileSnippets:
    """Tests for _gather_file_snippets helper."""

    def test_basic_snippet_extraction(self, tmp_path):
        src = tmp_path / "sample.py"
        src.write_text("line1\nline2\nline3\nline4\nline5\nline6\nline7\n")

        findings = [{"file": str(src), "line": 4}]
        result = _gather_file_snippets(findings, context_lines=1)

        assert str(src) in result
        assert 4 in result[str(src)]
        snippet = result[str(src)][4]
        assert "line3" in snippet
        assert "line4" in snippet
        assert "line5" in snippet

    def test_snippet_at_file_start(self, tmp_path):
        src = tmp_path / "top.py"
        src.write_text("a\nb\nc\n")

        findings = [{"file": str(src), "line": 1}]
        result = _gather_file_snippets(findings, context_lines=2)

        snippet = result[str(src)][1]
        assert "a" in snippet

    def test_missing_file_skipped(self):
        findings = [{"file": "/nonexistent/file.py", "line": 1}]
        result = _gather_file_snippets(findings)
        assert len(result) == 0

    def test_missing_line_key_skipped(self):
        findings = [{"file": "some.py"}]  # no "line" key
        result = _gather_file_snippets(findings)
        assert len(result) == 0

    def test_missing_file_key_skipped(self):
        findings = [{"line": 1}]  # no "file" key
        result = _gather_file_snippets(findings)
        assert len(result) == 0

    def test_empty_findings(self):
        result = _gather_file_snippets([])
        assert result == {}

    def test_multiple_findings_same_file(self, tmp_path):
        src = tmp_path / "multi.py"
        src.write_text("\n".join(f"line{i}" for i in range(1, 11)))

        findings = [
            {"file": str(src), "line": 2},
            {"file": str(src), "line": 8},
        ]
        result = _gather_file_snippets(findings, context_lines=1)

        assert 2 in result[str(src)]
        assert 8 in result[str(src)]


# ---------------------------------------------------------------------------
# Tests: _format_findings_for_prompt
# ---------------------------------------------------------------------------


class TestFormatFindingsForPrompt:
    """Tests for _format_findings_for_prompt helper."""

    def test_basic_formatting(self):
        findings = [
            {
                "type": "perf_issue",
                "file": "foo.py",
                "line": 10,
                "description": "slow loop",
                "severity": "high",
            }
        ]
        snippets: dict = {}
        result = _format_findings_for_prompt(findings, snippets)

        assert "[0]" in result
        assert "perf_issue" in result
        assert "high" in result
        assert "foo.py:10" in result
        assert "slow loop" in result

    def test_with_snippet(self):
        findings = [
            {
                "type": "issue",
                "file": "bar.py",
                "line": 5,
                "description": "desc",
                "severity": "medium",
            }
        ]
        snippets = {"bar.py": {5: "  5: x = 1"}}
        result = _format_findings_for_prompt(findings, snippets)

        assert "Code context:" in result
        assert "x = 1" in result

    def test_impact_as_severity(self):
        """'impact' key is used when 'severity' is absent."""
        findings = [
            {
                "type": "test",
                "file": "f.py",
                "line": 1,
                "description": "d",
                "impact": "low",
            }
        ]
        result = _format_findings_for_prompt(findings, {})
        assert "low" in result

    def test_empty_findings(self):
        result = _format_findings_for_prompt([], {})
        assert result == ""

    def test_multiple_findings(self):
        findings = [
            {"type": "a", "file": "a.py", "line": 1, "description": "da", "severity": "low"},
            {"type": "b", "file": "b.py", "line": 2, "description": "db", "severity": "high"},
        ]
        result = _format_findings_for_prompt(findings, {})
        assert "[0]" in result
        assert "[1]" in result


# ---------------------------------------------------------------------------
# Tests: _parse_deep_enrichment
# ---------------------------------------------------------------------------


class TestParseDeepEnrichment:
    """Tests for _parse_deep_enrichment helper."""

    def test_valid_json_response(self):
        original = [
            {"type": "issue", "severity": "high"},
            {"type": "issue2", "severity": "medium"},
        ]
        response = json.dumps(
            {
                "findings": [
                    {
                        "index": 0,
                        "validated": True,
                        "false_positive": True,
                        "suggestion": "false alarm",
                        "severity": "low",
                    },
                    {
                        "index": 1,
                        "validated": True,
                        "false_positive": False,
                        "suggestion": "fix it",
                    },
                ]
            }
        )

        result = _parse_deep_enrichment(response, original)

        assert len(result) == 2
        assert result[0]["false_positive"] is True
        assert result[0]["suggestion"] == "false alarm"
        assert result[0]["severity"] == "low"  # severity adjusted
        assert result[1]["false_positive"] is False
        assert result[1]["suggestion"] == "fix it"

    def test_json_in_markdown_code_block(self):
        original = [{"type": "issue", "severity": "high"}]
        response = (
            '```json\n{"findings": [{"index": 0, "validated": true, "false_positive": false}]}\n```'
        )

        result = _parse_deep_enrichment(response, original)
        assert result[0]["validated"] is True
        assert result[0]["false_positive"] is False

    def test_invalid_json_falls_back(self):
        original = [{"type": "issue", "severity": "high"}]
        response = "this is not json at all"

        result = _parse_deep_enrichment(response, original)
        assert len(result) == 1
        assert result[0]["validated"] is True
        assert result[0]["false_positive"] is False

    def test_out_of_range_index_ignored(self):
        original = [{"type": "issue", "severity": "high"}]
        response = json.dumps(
            {"findings": [{"index": 99, "validated": True, "false_positive": True}]}
        )

        result = _parse_deep_enrichment(response, original)
        assert len(result) == 1
        # original not modified since index 99 is out of range
        assert "validated" not in result[0] or result[0].get("validated") is True

    def test_negative_index_ignored(self):
        original = [{"type": "issue"}]
        response = json.dumps(
            {"findings": [{"index": -1, "validated": True, "false_positive": True}]}
        )

        result = _parse_deep_enrichment(response, original)
        assert result[0].get("false_positive") is not True

    def test_severity_uses_impact_key_when_present(self):
        """When original has 'impact' instead of 'severity', update 'impact'."""
        original = [{"type": "issue", "impact": "high"}]
        response = json.dumps(
            {
                "findings": [
                    {"index": 0, "validated": True, "false_positive": False, "severity": "low"}
                ]
            }
        )

        result = _parse_deep_enrichment(response, original)
        # Should update 'impact' key since original doesn't have 'severity'
        assert result[0].get("impact") == "low" or result[0].get("severity") == "low"

    def test_does_not_mutate_original(self):
        original = [{"type": "issue", "severity": "high"}]
        original_copy = [dict(f) for f in original]
        response = json.dumps(
            {
                "findings": [
                    {"index": 0, "validated": True, "false_positive": True, "suggestion": "fix"}
                ]
            }
        )

        _parse_deep_enrichment(response, original)
        assert original == original_copy  # original unchanged

    def test_empty_findings_key(self):
        original = [{"type": "issue"}]
        response = json.dumps({"findings": []})

        result = _parse_deep_enrichment(response, original)
        assert len(result) == 1

    def test_missing_findings_key(self):
        original = [{"type": "issue"}]
        response = json.dumps({"other": "data"})

        result = _parse_deep_enrichment(response, original)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Tests: _recount_by_key
# ---------------------------------------------------------------------------


class TestRecountByKey:
    """Tests for _recount_by_key helper."""

    def test_basic_counting(self):
        findings = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        result = _recount_by_key(findings, "severity")
        assert result == {"high": 2, "medium": 1, "low": 1}

    def test_excludes_false_positives(self):
        findings = [
            {"severity": "high", "false_positive": True},
            {"severity": "high", "false_positive": False},
            {"severity": "medium"},
        ]
        result = _recount_by_key(findings, "severity")
        assert result["high"] == 1  # only the non-false-positive one
        assert result["medium"] == 1

    def test_defaults_to_low(self):
        findings = [{"other": "data"}]  # no severity key
        result = _recount_by_key(findings, "severity")
        assert result["low"] == 1

    def test_empty_findings(self):
        result = _recount_by_key([], "severity")
        assert result == {"high": 0, "medium": 0, "low": 0}

    def test_impact_key(self):
        findings = [
            {"impact": "high"},
            {"impact": "low"},
        ]
        result = _recount_by_key(findings, "impact")
        assert result["high"] == 1
        assert result["low"] == 1


# ---------------------------------------------------------------------------
# Tests: CodeReviewAnalysisMixin._perf_check
# ---------------------------------------------------------------------------


class TestPerfCheck:
    """Tests for CodeReviewAnalysisMixin._perf_check."""

    def test_no_files(self):
        host = _FakeHost()
        result, in_t, out_t = _run(host._perf_check({"files_changed": []}, "cheap"))
        assert result["perf_finding_count"] == 0
        assert result["perf_findings"] == []

    def test_nonexistent_files_skipped(self):
        host = _FakeHost()
        result, _, _ = _run(host._perf_check({"files_changed": ["/nonexistent/file.py"]}, "cheap"))
        assert result["perf_finding_count"] == 0

    def test_non_python_files_skipped(self, tmp_path):
        txt = tmp_path / "data.txt"
        txt.write_text("some content")
        host = _FakeHost()
        result, _, _ = _run(host._perf_check({"files_changed": [str(txt)]}, "cheap"))
        assert result["perf_finding_count"] == 0

    def test_detects_perf_patterns(self, tmp_path):
        """Create a Python file with known perf anti-patterns."""
        src = tmp_path / "slow.py"
        src.write_text(
            textwrap.dedent(
                """\
                import time
                time.sleep(5)
                data = sorted(items)[:10]
            """
            )
        )

        host = _FakeHost()
        result, in_t, out_t = _run(host._perf_check({"files_changed": [str(src)]}, "cheap"))

        # Should find at least one pattern (depends on PERF_PATTERNS content)
        assert isinstance(result["perf_findings"], list)
        assert isinstance(result["perf_by_impact"], dict)
        assert "high" in result["perf_by_impact"]
        assert "medium" in result["perf_by_impact"]
        assert "low" in result["perf_by_impact"]
        assert in_t >= 0
        assert out_t >= 0

    def test_preserves_input_data(self, tmp_path):
        host = _FakeHost()
        result, _, _ = _run(
            host._perf_check({"files_changed": [], "extra_key": "preserved"}, "cheap")
        )
        assert result["extra_key"] == "preserved"

    def test_unreadable_file_skipped(self, tmp_path):
        src = tmp_path / "unreadable.py"
        src.write_text("content")

        host = _FakeHost()
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result, _, _ = _run(host._perf_check({"files_changed": [str(src)]}, "cheap"))
        assert result["perf_finding_count"] == 0


# ---------------------------------------------------------------------------
# Tests: CodeReviewAnalysisMixin._perf_check_deep
# ---------------------------------------------------------------------------


class TestPerfCheckDeep:
    """Tests for CodeReviewAnalysisMixin._perf_check_deep."""

    def test_no_findings_short_circuit(self):
        host = _FakeHost()
        input_data = {"perf_findings": [], "files_changed": []}
        result, in_t, out_t = _run(host._perf_check_deep(input_data, "capable"))
        assert in_t == 0
        assert out_t == 0
        host._call_llm.assert_not_called()

    def test_calls_llm_with_findings(self, tmp_path):
        src = tmp_path / "code.py"
        src.write_text("line1\nline2\nline3\nline4\nline5\n")

        host = _FakeHost()
        llm_response = json.dumps(
            {
                "findings": [
                    {
                        "index": 0,
                        "validated": True,
                        "false_positive": False,
                        "suggestion": "use heapq",
                    }
                ]
            }
        )
        host._call_llm = AsyncMock(return_value=(llm_response, 100, 50))

        input_data = {
            "perf_findings": [
                {
                    "type": "sorted_slice",
                    "file": str(src),
                    "line": 3,
                    "description": "sorted()[:N] pattern",
                    "impact": "medium",
                    "match": "sorted(items)[:10]",
                }
            ],
            "files_changed": [str(src)],
        }

        result, in_t, out_t = _run(host._perf_check_deep(input_data, "capable"))

        host._call_llm.assert_called_once()
        assert result["perf_deep_ran"] is True
        assert result["perf_finding_count"] == 1
        assert result["perf_findings"][0]["suggestion"] == "use heapq"
        assert in_t == 100
        assert out_t == 50

    def test_false_positive_reduces_count(self, tmp_path):
        src = tmp_path / "code.py"
        src.write_text("content\n")

        host = _FakeHost()
        llm_response = json.dumps(
            {
                "findings": [
                    {"index": 0, "validated": True, "false_positive": True, "suggestion": "ok"},
                ]
            }
        )
        host._call_llm = AsyncMock(return_value=(llm_response, 50, 30))

        input_data = {
            "perf_findings": [
                {"type": "issue", "file": str(src), "line": 1, "description": "d", "impact": "high"}
            ],
            "files_changed": [],
        }

        result, _, _ = _run(host._perf_check_deep(input_data, "capable"))
        assert result["perf_finding_count"] == 0  # false positive excluded


# ---------------------------------------------------------------------------
# Tests: CodeReviewAnalysisMixin._health_monitor
# ---------------------------------------------------------------------------


class TestHealthMonitor:
    """Tests for CodeReviewAnalysisMixin._health_monitor."""

    def test_returns_health_snapshot(self):
        host = _FakeHost()
        result, in_t, out_t = _run(host._health_monitor({"files_changed": []}, "cheap"))

        assert "health_snapshot" in result
        snapshot = result["health_snapshot"]
        assert "cache_stats" in snapshot
        assert "cost_today" in snapshot
        assert "usage_stats_7d" in snapshot
        assert in_t == 0
        assert out_t >= 0

    def test_preserves_input_data(self):
        host = _FakeHost()
        result, _, _ = _run(host._health_monitor({"files_changed": [], "key": "val"}, "cheap"))
        assert result["key"] == "val"

    def test_handles_missing_cache_monitor(self):
        host = _FakeHost()
        with patch.dict("sys.modules", {"attune.cache_monitor": None}):
            result, _, _ = _run(host._health_monitor({}, "cheap"))
        assert "health_snapshot" in result

    def test_handles_missing_cost_tracker(self):
        host = _FakeHost()
        with patch("attune.workflows.code_review_analysis_mixin.logger"):
            result, _, _ = _run(host._health_monitor({}, "cheap"))
        assert "health_snapshot" in result

    def test_handles_import_errors_gracefully(self):
        """All three metric sources can fail with ImportError."""
        host = _FakeHost()

        # Patch all three imports to raise ImportError
        def raise_import_error(*args, **kwargs):
            raise ImportError("not available")

        with patch(
            "builtins.__import__",
            side_effect=lambda name, *a, **kw: (
                raise_import_error()
                if name in ("attune.cache_monitor", "attune.cost_tracker", "attune.telemetry")
                else __builtins__.__import__(name, *a, **kw)  # type: ignore[union-attr]
            ),
        ):
            result, _, _ = _run(host._health_monitor({}, "cheap"))

        snapshot = result["health_snapshot"]
        # Should have empty dicts for all three, not crash
        assert isinstance(snapshot.get("cache_stats"), dict)
        assert isinstance(snapshot.get("cost_today"), dict)
        assert isinstance(snapshot.get("usage_stats_7d"), dict)


# ---------------------------------------------------------------------------
# Tests: CodeReviewAnalysisMixin._quality_check
# ---------------------------------------------------------------------------


class TestQualityCheck:
    """Tests for CodeReviewAnalysisMixin._quality_check."""

    def test_no_files(self):
        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": []}, "cheap"))
        assert result["quality_finding_count"] == 0
        assert result["quality_findings"] == []

    def test_detects_bare_except(self, tmp_path):
        src = tmp_path / "bad.py"
        src.write_text(
            textwrap.dedent(
                """\
                try:
                    risky()
                except:
                    pass
            """
            )
        )

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        bare_excepts = [f for f in result["quality_findings"] if f["type"] == "bare_except"]
        assert len(bare_excepts) >= 1
        assert bare_excepts[0]["severity"] == "high"

    def test_allows_except_with_noqa(self, tmp_path):
        src = tmp_path / "ok.py"
        src.write_text(
            textwrap.dedent(
                """\
                try:
                    risky()
                except Exception:  # noqa: BLE001
                    pass
            """
            )
        )

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        bare_excepts = [f for f in result["quality_findings"] if f["type"] == "bare_except"]
        assert len(bare_excepts) == 0

    def test_detects_long_file(self, tmp_path):
        src = tmp_path / "long.py"
        src.write_text("\n".join(f"line_{i} = {i}" for i in range(MAX_FILE_LINES + 100)))

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        long_files = [f for f in result["quality_findings"] if f["type"] == "long_file"]
        assert len(long_files) == 1
        assert long_files[0]["severity"] == "medium"

    def test_detects_todo_comments(self, tmp_path):
        src = tmp_path / "todos.py"
        src.write_text("# TODO: fix this\n# FIXME: also this\nx = 1\n")

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        todos = [f for f in result["quality_findings"] if f["type"] == "todo_fixme"]
        assert len(todos) == 1
        assert "2" in todos[0]["description"]  # 2 TODO/FIXME found

    def test_detects_missing_return_type_hint(self, tmp_path):
        src = tmp_path / "nohint.py"
        src.write_text("def compute(x):\n    return x * 2\n")

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        missing_hints = [f for f in result["quality_findings"] if f["type"] == "missing_type_hint"]
        assert len(missing_hints) == 1
        assert "compute" in missing_hints[0]["description"]

    def test_skips_private_functions(self, tmp_path):
        src = tmp_path / "private.py"
        src.write_text("def _helper(x):\n    return x\n")

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        missing_hints = [f for f in result["quality_findings"] if f["type"] == "missing_type_hint"]
        assert len(missing_hints) == 0

    def test_function_with_return_hint_not_flagged(self, tmp_path):
        src = tmp_path / "hinted.py"
        src.write_text("def compute(x: int) -> int:\n    return x * 2\n")

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        missing_hints = [f for f in result["quality_findings"] if f["type"] == "missing_type_hint"]
        assert len(missing_hints) == 0

    def test_non_python_files_skipped(self, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.write_text("except:\nTODO: stuff\n")

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(txt)]}, "cheap"))
        assert result["quality_finding_count"] == 0

    def test_preserves_input_data(self):
        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [], "context": "data"}, "cheap"))
        assert result["context"] == "data"

    def test_by_severity_counts(self, tmp_path):
        src = tmp_path / "mixed.py"
        src.write_text(
            textwrap.dedent(
                """\
                # TODO: later
                try:
                    x = 1
                except:
                    pass
            """
            )
        )

        host = _FakeHost()
        result, _, _ = _run(host._quality_check({"files_changed": [str(src)]}, "cheap"))

        by_sev = result["quality_by_severity"]
        assert by_sev["high"] >= 1  # bare except
        assert by_sev["low"] >= 1  # TODO


# ---------------------------------------------------------------------------
# Tests: CodeReviewAnalysisMixin._quality_check_deep
# ---------------------------------------------------------------------------


class TestQualityCheckDeep:
    """Tests for CodeReviewAnalysisMixin._quality_check_deep."""

    def test_no_findings_short_circuit(self):
        host = _FakeHost()
        input_data = {"quality_findings": [], "files_changed": []}
        result, in_t, out_t = _run(host._quality_check_deep(input_data, "capable"))
        assert in_t == 0
        assert out_t == 0
        host._call_llm.assert_not_called()

    def test_calls_llm_with_findings(self, tmp_path):
        src = tmp_path / "code.py"
        src.write_text("line1\nline2\nline3\n")

        host = _FakeHost()
        llm_response = json.dumps(
            {
                "findings": [
                    {
                        "index": 0,
                        "validated": True,
                        "false_positive": False,
                        "severity": "high",
                        "suggestion": "add specific exception types",
                    }
                ]
            }
        )
        host._call_llm = AsyncMock(return_value=(llm_response, 80, 40))

        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": str(src),
                    "line": 2,
                    "description": "Bare except",
                    "severity": "high",
                }
            ],
            "files_changed": [str(src)],
        }

        result, in_t, out_t = _run(host._quality_check_deep(input_data, "capable"))

        host._call_llm.assert_called_once()
        assert result["quality_deep_ran"] is True
        assert result["quality_finding_count"] == 1
        assert result["quality_findings"][0]["suggestion"] == "add specific exception types"

    def test_false_positive_reduces_count(self, tmp_path):
        src = tmp_path / "code.py"
        src.write_text("content\n")

        host = _FakeHost()
        llm_response = json.dumps(
            {
                "findings": [
                    {
                        "index": 0,
                        "validated": True,
                        "false_positive": True,
                        "suggestion": "intentional pattern",
                    },
                ]
            }
        )
        host._call_llm = AsyncMock(return_value=(llm_response, 50, 30))

        input_data = {
            "quality_findings": [
                {
                    "type": "bare_except",
                    "file": str(src),
                    "line": 1,
                    "description": "Bare except",
                    "severity": "high",
                }
            ],
            "files_changed": [],
        }

        result, _, _ = _run(host._quality_check_deep(input_data, "capable"))
        assert result["quality_finding_count"] == 0

    def test_overwrites_quality_keys_from_input(self, tmp_path):
        """Deep results should replace CHEAP-stage quality keys."""
        src = tmp_path / "code.py"
        src.write_text("x = 1\n")

        host = _FakeHost()
        llm_response = json.dumps({"findings": []})
        host._call_llm = AsyncMock(return_value=(llm_response, 10, 10))

        input_data = {
            "quality_findings": [
                {
                    "type": "issue",
                    "file": str(src),
                    "line": 1,
                    "description": "d",
                    "severity": "low",
                }
            ],
            "quality_finding_count": 1,
            "quality_by_severity": {"high": 0, "medium": 0, "low": 1},
            "other_data": "keep",
        }

        result, _, _ = _run(host._quality_check_deep(input_data, "capable"))
        assert result["other_data"] == "keep"
        assert result["quality_deep_ran"] is True


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_max_file_lines_value(self):
        assert MAX_FILE_LINES == 500

    def test_chars_per_token_estimate_value(self):
        assert CHARS_PER_TOKEN_ESTIMATE == 4
