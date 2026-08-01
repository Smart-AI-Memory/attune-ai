"""Tests for specialized release agents.

Tests TestCoverageAgent, CodeQualityAgent, DocumentationAgent, and
SecurityAuditorAgent _execute_tier methods and output parsing.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PATCH_ANTHROPIC = "attune.agents.release.base_agent.ANTHROPIC_AVAILABLE"
_PATCH_LLM_MODE = "attune.agents.release.base_agent.LLM_MODE"


def _no_llm():
    """Context manager pair to disable LLM in all agents."""
    return (
        patch(_PATCH_ANTHROPIC, False),
        patch(_PATCH_LLM_MODE, "rule_based"),
    )


# ---------------------------------------------------------------------------
# TestCoverageAgent
# ---------------------------------------------------------------------------


class TestTestCoverageAgent:
    """Tests for TestCoverageAgent._execute_tier and _parse_coverage_output."""

    def _make_agent(self):
        with (
            patch(_PATCH_ANTHROPIC, False),
            patch(_PATCH_LLM_MODE, "rule_based"),
        ):
            from attune.agents.release.coverage_agent import TestCoverageAgent

            return TestCoverageAgent()

    # --- _parse_coverage_output ---

    def test_parse_coverage_output_total_line(self):
        """Parses coverage from a TOTAL line like 'TOTAL  1234  567  83%'."""
        agent = self._make_agent()
        output = (
            "Name                  Stmts   Miss  Cover\n"
            "src/attune/foo.py       100     20    80%\n"
            "TOTAL                   200     34    83%\n"
        )
        result = agent._parse_coverage_output(output)

        assert result == pytest.approx(83.0)

    def test_parse_coverage_output_alternate_pattern(self):
        """Parses '75% coverage' alternate pattern."""
        agent = self._make_agent()
        output = "75% coverage, 25 missing lines\n"
        result = agent._parse_coverage_output(output)

        assert result == pytest.approx(75.0)

    def test_parse_coverage_output_no_match_returns_minus_one(self):
        """Returns -1.0 when no coverage info present."""
        agent = self._make_agent()
        result = agent._parse_coverage_output("no coverage here")

        assert result == pytest.approx(-1.0)

    def test_parse_coverage_output_empty_string_returns_minus_one(self):
        """Returns -1.0 for empty output."""
        agent = self._make_agent()
        result = agent._parse_coverage_output("")

        assert result == pytest.approx(-1.0)

    # --- _execute_tier: success path with real coverage output ---

    def test_execute_tier_success_with_coverage_total(self):
        """_execute_tier returns True and parsed coverage when TOTAL line present."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        collect_output = "10 tests collected\n"
        cov_output = (
            "Name              Stmts   Miss  Cover\n" "TOTAL              500     75    85%\n"
        )

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, collect_output, "")
            return (0, cov_output, "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["coverage_percent"] == pytest.approx(85.0)
        assert findings["estimated"] is False

    def test_execute_tier_uses_heuristic_when_no_total_line(self):
        """Falls back to heuristic when coverage not parseable, using test count."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        # Return enough ":: " lines so test_count > 200
        big_collect = "\n".join(f"test_foo::test_{i}" for i in range(250))

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, big_collect, "")
            return (0, "no coverage info here", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["estimated"] is True
        assert findings["coverage_percent"] >= 80.0  # heuristic for >200 tests

    def test_execute_tier_heuristic_over_500_tests(self):
        """Heuristic yields 85.0 when test_count > 500."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        big_collect = "\n".join(f"test_foo::test_{i}" for i in range(600))

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, big_collect, "")
            return (0, "no coverage info here", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["estimated"] is True
        assert findings["coverage_percent"] == pytest.approx(85.0)

    def test_execute_tier_heuristic_over_100_tests(self):
        """Heuristic yields 75.0 when 100 < test_count <= 200."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        collect_output = "\n".join(f"test_foo::test_{i}" for i in range(150))

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, collect_output, "")
            return (0, "no coverage info here", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["estimated"] is True
        assert findings["coverage_percent"] == pytest.approx(75.0)

    def test_execute_tier_heuristic_over_50_tests(self):
        """Heuristic yields 60.0 when 50 < test_count <= 100."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        collect_output = "\n".join(f"test_foo::test_{i}" for i in range(75))

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, collect_output, "")
            return (0, "no coverage info here", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["estimated"] is True
        assert findings["coverage_percent"] == pytest.approx(60.0)

    def test_execute_tier_heuristic_over_10_tests(self):
        """Heuristic yields 40.0 when 10 < test_count <= 50."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        collect_output = "\n".join(f"test_foo::test_{i}" for i in range(25))

        def fake_run(cmd, cwd="."):
            if "--co" in cmd:
                return (0, collect_output, "")
            return (0, "no coverage info here", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["estimated"] is True
        assert findings["coverage_percent"] == pytest.approx(40.0)

    def test_execute_tier_always_returns_true_on_estimated(self):
        """_execute_tier always returns True (quality gate handles threshold)."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        def fake_run(cmd, cwd="."):
            return (0, "no coverage output", "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            success, _ = agent._execute_tier(".", Tier.CAPABLE)

        assert success is True

    def test_execute_tier_returns_findings_with_expected_keys(self):
        """Findings dict contains all expected keys."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        cov_output = "TOTAL  200  40  80%\n"

        def fake_run(cmd, cwd="."):
            return (0, cov_output, "")

        with patch("attune.agents.release.coverage_agent._run_command", side_effect=fake_run):
            _, findings = agent._execute_tier(".", Tier.CHEAP)

        assert "coverage_percent" in findings
        assert "test_count" in findings
        assert "estimated" in findings
        assert "score" in findings
        assert "confidence" in findings

    def test_execute_tier_handles_exception_gracefully(self):
        """Exception in _execute_tier returns (False, error dict)."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        with patch(
            "attune.agents.release.coverage_agent._run_command",
            side_effect=RuntimeError("unexpected"),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is False
        assert "error" in findings


# ---------------------------------------------------------------------------
# CodeQualityAgent
# ---------------------------------------------------------------------------


class TestCodeQualityAgent:
    """Tests for CodeQualityAgent._execute_tier and _parse_ruff_output."""

    def _make_agent(self):
        with (
            patch(_PATCH_ANTHROPIC, False),
            patch(_PATCH_LLM_MODE, "rule_based"),
        ):
            from attune.agents.release.quality_agent import CodeQualityAgent

            return CodeQualityAgent()

    # --- _parse_ruff_output ---

    def test_parse_ruff_output_clean_returns_ten(self):
        """No violations → quality_score = 10.0."""
        agent = self._make_agent()
        result = agent._parse_ruff_output("", returncode=0)

        assert result["quality_score"] == pytest.approx(10.0)
        assert result["total_violations"] == 0

    def test_parse_ruff_output_few_violations_score_nine(self):
        """1-9 violations → quality_score = 9.0."""
        agent = self._make_agent()
        output = "5 E501 Line too long\n"
        result = agent._parse_ruff_output(output, returncode=1)

        assert result["quality_score"] == pytest.approx(9.0)
        assert result["total_violations"] == 5

    def test_parse_ruff_output_many_violations_score_low(self):
        """300+ violations → quality_score = 3.0."""
        agent = self._make_agent()
        output = "400 E501 Line too long\n"
        result = agent._parse_ruff_output(output, returncode=1)

        assert result["quality_score"] == pytest.approx(3.0)

    def test_parse_ruff_output_command_not_found(self):
        """returncode=-1 (command not found) → quality_score=5.0 with note."""
        agent = self._make_agent()
        result = agent._parse_ruff_output("", returncode=-1)

        assert result["quality_score"] == pytest.approx(5.0)
        assert "ruff not available" in result.get("note", "")

    def test_parse_ruff_output_categorises_by_prefix(self):
        """Violation categories are mapped by ruff code prefix."""
        agent = self._make_agent()
        output = "10 E501 Line too long\n" "5 S101 Use of assert\n" "3 F401 Unused import\n"
        result = agent._parse_ruff_output(output, returncode=1)

        assert result["categories"].get("style", 0) == 10
        assert result["categories"].get("security", 0) == 5
        assert result["categories"].get("errors", 0) == 3

    # --- _execute_tier ---

    def test_execute_tier_clean_returns_success(self):
        """Clean ruff output (score >= 7.0) → success=True."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        with patch(
            "attune.agents.release.quality_agent._run_command",
            return_value=(0, "", ""),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["quality_score"] == pytest.approx(10.0)

    def test_execute_tier_many_violations_returns_failure(self):
        """300+ violations score 3.0 < threshold 7.0 → success=False."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        ruff_output = "400 E501 Line too long\n"

        with patch(
            "attune.agents.release.quality_agent._run_command",
            return_value=(1, ruff_output, ""),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is False
        assert findings["total_violations"] == 400

    def test_execute_tier_findings_have_tier_key(self):
        """Findings include 'tier' key with current tier value."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        with patch(
            "attune.agents.release.quality_agent._run_command",
            return_value=(0, "", ""),
        ):
            _, findings = agent._execute_tier(".", Tier.CAPABLE)

        assert findings["tier"] == "capable"

    def test_execute_tier_exception_returns_false(self):
        """Exception during analysis returns (False, error_dict)."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        with patch(
            "attune.agents.release.quality_agent._run_command",
            side_effect=RuntimeError("oops"),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is False
        assert "error" in findings


# ---------------------------------------------------------------------------
# DocumentationAgent
# ---------------------------------------------------------------------------


class TestDocumentationAgent:
    """Tests for DocumentationAgent._execute_tier."""

    def _make_agent(self):
        with (
            patch(_PATCH_ANTHROPIC, False),
            patch(_PATCH_LLM_MODE, "rule_based"),
        ):
            from attune.agents.release.documentation_agent import DocumentationAgent

            return DocumentationAgent()

    def test_all_docs_present_success(self, tmp_path):
        """When README and CHANGELOG exist, findings show both present."""
        from attune.agents.release.release_models import Tier

        # Create minimal project structure
        src = tmp_path / "src"
        src.mkdir()
        (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

        # Create a simple Python file with a documented public function
        py_file = src / "module.py"
        py_file.write_text(
            'def public_func():\n    """A public function."""\n    pass\n',
            encoding="utf-8",
        )

        agent = self._make_agent()
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert success is True
        assert findings["readme_exists"] is True
        assert findings["changelog_exists"] is True

    def test_missing_readme_reflected_in_findings(self, tmp_path):
        """When README does not exist, readme_exists is False."""
        from attune.agents.release.release_models import Tier

        src = tmp_path / "src"
        src.mkdir()
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

        agent = self._make_agent()
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert success is True  # Documentation is always non-blocking
        assert findings["readme_exists"] is False

    def test_missing_changelog_reflected_in_findings(self, tmp_path):
        """When CHANGELOG does not exist, changelog_exists is False."""
        from attune.agents.release.release_models import Tier

        src = tmp_path / "src"
        src.mkdir()
        (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")

        agent = self._make_agent()
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert findings["changelog_exists"] is False

    def test_docstring_coverage_calculated(self, tmp_path):
        """coverage_percent is computed from functions with/without docstrings."""
        from attune.agents.release.release_models import Tier

        src = tmp_path / "src"
        src.mkdir()

        py_file = src / "sample.py"
        py_file.write_text(
            (
                'def with_doc():\n    """Has docstring."""\n    pass\n\n'
                "def without_doc():\n    pass\n"
            ),
            encoding="utf-8",
        )

        agent = self._make_agent()
        _, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        # 1 documented out of 2 public functions = 50%
        assert findings["total_functions"] == 2
        assert findings["documented_functions"] == 1
        assert findings["coverage_percent"] == pytest.approx(50.0)

    def test_private_functions_excluded_from_count(self, tmp_path):
        """Private (single-underscore) functions are not counted."""
        from attune.agents.release.release_models import Tier

        src = tmp_path / "src"
        src.mkdir()

        py_file = src / "sample.py"
        py_file.write_text(
            (
                'def public_func():\n    """Documented."""\n    pass\n\n'
                "def _private_func():\n    pass\n"
            ),
            encoding="utf-8",
        )

        agent = self._make_agent()
        _, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert findings["total_functions"] == 1
        assert findings["documented_functions"] == 1

    def test_no_python_files_returns_zero_coverage(self, tmp_path):
        """Empty src directory yields 0% coverage."""
        from attune.agents.release.release_models import Tier

        src = tmp_path / "src"
        src.mkdir()

        agent = self._make_agent()
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert success is True
        assert findings["coverage_percent"] == pytest.approx(0.0)

    def test_findings_have_expected_keys(self, tmp_path):
        """Findings contain all expected keys."""
        from attune.agents.release.release_models import Tier

        (tmp_path / "src").mkdir()
        agent = self._make_agent()
        _, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        expected_keys = {
            "coverage_percent",
            "total_functions",
            "documented_functions",
            "undocumented_count",
            "undocumented_sample",
            "readme_exists",
            "changelog_exists",
            "score",
            "confidence",
            "tier",
            "mode",
        }
        assert expected_keys.issubset(findings.keys())

    def test_always_returns_success_true(self, tmp_path):
        """_execute_tier always returns True (non-blocking)."""
        from attune.agents.release.release_models import Tier

        (tmp_path / "src").mkdir()
        agent = self._make_agent()
        success, _ = agent._execute_tier(str(tmp_path), Tier.PREMIUM)

        assert success is True

    def test_falls_back_to_codebase_path_when_no_src(self, tmp_path):
        """Uses codebase_path directly when no 'src' subdir exists."""
        from attune.agents.release.release_models import Tier

        # No src subdirectory — agent should use tmp_path itself
        py_file = tmp_path / "module.py"
        py_file.write_text('def foo():\n    """Doc."""\n    pass\n', encoding="utf-8")

        agent = self._make_agent()
        success, findings = agent._execute_tier(str(tmp_path), Tier.CHEAP)

        assert success is True
        assert findings["total_functions"] >= 1


# ---------------------------------------------------------------------------
# SecurityAuditorAgent
# ---------------------------------------------------------------------------


class TestSecurityAuditorAgent:
    """Tests for SecurityAuditorAgent._execute_tier and _parse_bandit_output."""

    def _make_agent(self):
        with (
            patch(_PATCH_ANTHROPIC, False),
            patch(_PATCH_LLM_MODE, "rule_based"),
        ):
            from attune.agents.release.security_agent import SecurityAuditorAgent

            return SecurityAuditorAgent()

    # --- _parse_bandit_output ---

    def test_parse_bandit_output_clean_returns_full_score(self):
        """Empty results → 0 critical issues, score=100."""
        agent = self._make_agent()
        stdout = json.dumps({"results": [], "errors": []})
        result = agent._parse_bandit_output(stdout, returncode=0)

        assert result["critical_issues"] == 0
        assert result["score"] == pytest.approx(100.0)

    def test_parse_bandit_output_high_findings_increase_critical(self):
        """HIGH severity findings increment critical_issues."""
        agent = self._make_agent()
        results = [
            {
                "issue_severity": "HIGH",
                "issue_text": "Use of exec",
                "filename": "a.py",
                "line_number": 10,
            },
            {
                "issue_severity": "HIGH",
                "issue_text": "Hardcoded password",
                "filename": "b.py",
                "line_number": 20,
            },
        ]
        stdout = json.dumps({"results": results})
        result = agent._parse_bandit_output(stdout, returncode=1)

        # critical_issues = CRITICAL + HIGH counts
        assert result["critical_issues"] == 2
        assert result["high_issues"] == 2

    def test_parse_bandit_output_medium_findings_reduce_score(self):
        """MEDIUM findings reduce score but don't add to critical_issues."""
        agent = self._make_agent()
        results = [
            {
                "issue_severity": "MEDIUM",
                "issue_text": "Use of md5",
                "filename": "c.py",
                "line_number": 5,
            },
        ]
        stdout = json.dumps({"results": results})
        result = agent._parse_bandit_output(stdout, returncode=1)

        assert result["critical_issues"] == 0
        assert result["medium_issues"] == 1
        # Score reduced by 5 per medium issue
        assert result["score"] == pytest.approx(95.0)

    def test_parse_bandit_output_command_not_found(self):
        """returncode=-1 → bandit not available, score=50, critical=0."""
        agent = self._make_agent()
        result = agent._parse_bandit_output("", returncode=-1)

        assert result["critical_issues"] == 0
        assert result["score"] == pytest.approx(50.0)
        assert "bandit not available" in result.get("note", "")

    def test_parse_bandit_output_invalid_json_returns_defaults(self):
        """Invalid JSON stdout returns safe defaults."""
        agent = self._make_agent()
        result = agent._parse_bandit_output("not json at all", returncode=0)

        assert result["critical_issues"] == 0
        assert "note" in result

    def test_parse_bandit_output_top_findings_limited_to_five(self):
        """top_findings is capped at 5 entries."""
        agent = self._make_agent()
        results = [
            {
                "issue_severity": "LOW",
                "issue_text": f"Issue {i}",
                "filename": "f.py",
                "line_number": i,
            }
            for i in range(10)
        ]
        stdout = json.dumps({"results": results})
        result = agent._parse_bandit_output(stdout, returncode=0)

        assert len(result["top_findings"]) == 5

    # --- _execute_tier ---

    def test_execute_tier_clean_returns_success(self):
        """No critical issues → success=True."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        clean_output = json.dumps({"results": [], "errors": []})

        with patch(
            "attune.agents.release.security_agent._run_command",
            return_value=(0, clean_output, ""),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is True
        assert findings["critical_issues"] == 0

    def test_execute_tier_critical_issue_returns_failure(self):
        """Critical (HIGH/CRITICAL) findings → success=False."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        bandit_output = json.dumps(
            {
                "results": [
                    {
                        "issue_severity": "HIGH",
                        "issue_text": "Use of exec",
                        "filename": "bad.py",
                        "line_number": 10,
                    }
                ]
            }
        )

        with patch(
            "attune.agents.release.security_agent._run_command",
            return_value=(1, bandit_output, ""),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is False
        assert findings["critical_issues"] >= 1

    def test_execute_tier_findings_have_mode_and_tier(self):
        """Findings always include 'mode' and 'tier' keys."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        clean_output = json.dumps({"results": []})

        with patch(
            "attune.agents.release.security_agent._run_command",
            return_value=(0, clean_output, ""),
        ):
            _, findings = agent._execute_tier(".", Tier.CAPABLE)

        assert "mode" in findings
        assert findings["tier"] == "capable"

    def test_execute_tier_exception_returns_false(self):
        """Exception during execution returns (False, error_dict)."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()

        with patch(
            "attune.agents.release.security_agent._run_command",
            side_effect=RuntimeError("crash"),
        ):
            success, findings = agent._execute_tier(".", Tier.CHEAP)

        assert success is False
        assert "error" in findings

    def test_execute_tier_score_present_in_findings(self):
        """Findings include a numeric 'score' key."""
        from attune.agents.release.release_models import Tier

        agent = self._make_agent()
        clean_output = json.dumps({"results": []})

        with patch(
            "attune.agents.release.security_agent._run_command",
            return_value=(0, clean_output, ""),
        ):
            _, findings = agent._execute_tier(".", Tier.CHEAP)

        assert isinstance(findings.get("score"), int | float)
