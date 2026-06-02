"""Tests for .github/scripts/analyze_security_results.py.

Loaded via importlib.util because .github/scripts/ is not a Python
package — matches the repo convention used in
tests/unit/help/test_coverage_script.py.

Issue #560 regression guard: when the upstream security-audit
workflow produces no parseable JSON (typically because the
underlying SDK call failed before emitting output), the analyzer
must NOT write pr_comment.md. The workflow's "Post results to PR"
step is gated on the file existing, so suppressing the write
suppresses the alarming "⚠️ Error: Could not extract JSON" comment
that confuses contributors when the GH check is actually green.

Real errors (anything other than the extraction-failure markers)
still produce a comment so genuine diagnostic info reaches
reviewers.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "analyze_security_results.py"


@pytest.fixture
def analyzer():
    spec = importlib.util.spec_from_file_location("_analyze_security_results", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_analyze_security_results"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_analyze_security_results", None)


def _run_main(analyzer_mod, tmp_path: Path, input_data: dict) -> Path:
    """Drive the script's main() with the given input JSON.

    Returns the working directory main() ran in (where pr_comment.md
    and analysis.json land).
    """
    cwd = tmp_path / "workdir"
    cwd.mkdir()
    input_file = cwd / "security_results.json"
    output_file = cwd / "analysis.json"
    gh_output = cwd / "gh_output.txt"
    gh_output.touch()

    input_file.write_text(json.dumps(input_data), encoding="utf-8")

    original_cwd = Path.cwd()
    original_argv = sys.argv[:]
    try:
        import os

        os.chdir(cwd)
        sys.argv = [
            "analyze_security_results.py",
            "--input",
            str(input_file),
            "--output",
            str(output_file),
            "--github-output",
            str(gh_output),
        ]
        try:
            analyzer_mod.main()
        except SystemExit as exc:
            # main() calls sys.exit(0) on error paths; treat as normal return
            assert exc.code == 0, f"main() exited non-zero: {exc.code}"
    finally:
        import os

        os.chdir(original_cwd)
        sys.argv = original_argv

    return cwd


class TestIsExtractionFailure:
    """The classifier that decides whether to suppress the comment."""

    def test_recognizes_could_not_extract_message(self, analyzer):
        assert analyzer.is_extraction_failure("Could not extract JSON from CLI output")

    def test_recognizes_no_json_found_message(self, analyzer):
        assert analyzer.is_extraction_failure("No JSON found in output")

    def test_recognizes_no_output_message(self, analyzer):
        assert analyzer.is_extraction_failure("Security scan produced no output")

    def test_recognizes_empty_file_message(self, analyzer):
        assert analyzer.is_extraction_failure("Security results file is empty")

    def test_recognizes_mixed_output_message(self, analyzer):
        assert analyzer.is_extraction_failure("Could not parse security results from mixed output")

    def test_does_not_match_real_diagnostic_errors(self, analyzer):
        assert not analyzer.is_extraction_failure("Permission denied opening security_results.json")
        assert not analyzer.is_extraction_failure("Unexpected disk failure")
        assert not analyzer.is_extraction_failure("KeyError: 'severity'")

    def test_handles_empty_string(self, analyzer):
        assert not analyzer.is_extraction_failure("")


class TestMainSuppressesCommentOnExtractionFailure:
    """Regression guard for issue #560 — no PR comment on extraction failure."""

    def test_extraction_failure_does_not_write_pr_comment(self, analyzer, tmp_path):
        cwd = _run_main(
            analyzer,
            tmp_path,
            {"findings": [], "error": "Could not extract JSON from CLI output"},
        )
        assert not (cwd / "pr_comment.md").exists(), (
            "pr_comment.md must not be written on extraction failure — "
            "would alarm contributors per issue #560"
        )

    def test_extraction_failure_still_writes_analysis_json(self, analyzer, tmp_path):
        cwd = _run_main(
            analyzer,
            tmp_path,
            {"findings": [], "error": "No JSON found in output"},
        )
        analysis = json.loads((cwd / "analysis.json").read_text(encoding="utf-8"))
        assert analysis["scan_skipped"] is True
        assert analysis["has_critical"] is False
        assert analysis["total_findings"] == 0

    def test_real_error_still_writes_pr_comment(self, analyzer, tmp_path):
        """Non-extraction errors keep their diagnostic comment so reviewers
        see the real failure."""
        cwd = _run_main(
            analyzer,
            tmp_path,
            {"findings": [], "error": "KeyError: missing required field 'severity'"},
        )
        comment_path = cwd / "pr_comment.md"
        assert comment_path.exists(), "Real errors must still surface via PR comment"
        assert "KeyError" in comment_path.read_text(encoding="utf-8")

    def test_real_error_marks_scan_not_skipped(self, analyzer, tmp_path):
        cwd = _run_main(
            analyzer,
            tmp_path,
            {"findings": [], "error": "Disk write error"},
        )
        analysis = json.loads((cwd / "analysis.json").read_text(encoding="utf-8"))
        assert analysis["scan_skipped"] is False


class TestMainHandlesNormalFindings:
    """Sanity check that the normal-findings path still writes a comment."""

    def test_normal_findings_write_pr_comment(self, analyzer, tmp_path):
        cwd = _run_main(
            analyzer,
            tmp_path,
            {
                "findings": [
                    {
                        "severity": "medium",
                        "type": "broad_exception",
                        "file": "src/foo.py",
                        "line": 42,
                    },
                ]
            },
        )
        comment_path = cwd / "pr_comment.md"
        assert comment_path.exists()
        comment = comment_path.read_text(encoding="utf-8")
        assert "Security Scan Results" in comment

    def test_normal_findings_record_counts_in_analysis(self, analyzer, tmp_path):
        cwd = _run_main(
            analyzer,
            tmp_path,
            {
                "findings": [
                    {"severity": "critical", "type": "sql_injection", "file": "a.py"},
                    {"severity": "medium", "type": "broad_exception", "file": "b.py"},
                    {"severity": "low", "type": "incomplete_code", "file": "c.py"},
                ]
            },
        )
        analysis = json.loads((cwd / "analysis.json").read_text(encoding="utf-8"))
        assert analysis["total_findings"] == 3
        assert analysis["critical_count"] == 1
        assert analysis["medium_count"] == 1
        assert analysis["low_count"] == 1
        assert analysis["has_critical"] is True
