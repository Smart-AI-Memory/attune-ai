"""Unit tests for attune.meta_workflows.cli_commands.workflow_commands.

Covers run_workflow, natural_language_run, and detect_intent CLI commands.
Uses Typer's CliRunner with the app declared in cli_commands/__init__.py.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from attune.meta_workflows.cli_commands import meta_workflow_app


@pytest.fixture
def runner():
    return CliRunner()


def _fake_template(template_id="release-prep", name="Release Prep"):
    t = MagicMock()
    t.template_id = template_id
    t.name = name
    return t


def _fake_agent_result(role="security", success=True, cost=0.10, tier="cheap"):
    return SimpleNamespace(
        agent_id=f"agent-{role}",
        role=role,
        success=success,
        cost=cost,
        duration=1.5,
        tier_used=tier,
        output={"summary": "ok"},
        error=None,
    )


def _fake_form_responses():
    return SimpleNamespace(
        template_id="release-prep",
        responses={"q1": "yes"},
        timestamp="2025-01-01T00:00:00Z",
        response_id="resp-1",
    )


def _fake_workflow_result(success=True, error=None, run_id="run-abc"):
    return SimpleNamespace(
        run_id=run_id,
        timestamp="2025-01-01T00:00:00Z",
        success=success,
        error=error,
        total_cost=0.42,
        total_duration=12.5,
        agents_created=["a", "b", "c"],
        agent_results=[_fake_agent_result()],
        form_responses=_fake_form_responses(),
    )


# ---------------------------------------------------------------------------
# run_workflow
# ---------------------------------------------------------------------------


class TestRunWorkflow:
    def test_template_not_found(self, runner):
        """Lines 85-90: template missing → exit code 1, error message."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
        ) as MockReg:
            MockReg.return_value.load_template.return_value = None
            result = runner.invoke(meta_workflow_app, ["run", "missing"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_template_not_found_json(self, runner):
        """Lines 85-87: JSON output when template missing."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
        ) as MockReg:
            MockReg.return_value.load_template.return_value = None
            result = runner.invoke(meta_workflow_app, ["run", "missing", "--json"])
        assert result.exit_code == 1
        # JSON message printed to stdout
        assert "Template not found" in result.output

    def test_successful_mock_run(self, runner):
        """Happy path with mock execution."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(meta_workflow_app, ["run", "release-prep"])

        assert result.exit_code == 0
        assert "Execution Complete" in result.output
        assert "run-abc" in result.output
        # MetaWorkflow.execute was called with mock_execution=True
        MockWF.return_value.execute.assert_called_once_with(mock_execution=True, use_defaults=False)

    def test_real_run_uses_defaults(self, runner):
        """--real --use-defaults forwards to execute()."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(
                meta_workflow_app,
                ["run", "release-prep", "--real", "--use-defaults"],
            )

        assert result.exit_code == 0
        MockWF.return_value.execute.assert_called_once_with(mock_execution=False, use_defaults=True)
        assert "Using default values" in result.output

    def test_use_memory_initializes_pattern_learner(self, runner):
        """Lines 96-110: --use-memory initializes PatternLearner."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
            patch("attune.meta_workflows.cli_commands.workflow_commands.PatternLearner") as MockPL,
            patch(
                "attune.memory.unified.UnifiedMemory",
                return_value=MagicMock(),
            ),
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            mock_pl = MagicMock()
            mock_pl.memory = MagicMock()
            MockPL.return_value = mock_pl
            result = runner.invoke(meta_workflow_app, ["run", "release-prep", "--use-memory"])

        assert result.exit_code == 0
        assert "Memory enabled" in result.output
        assert "Memory: Long-term storage" in result.output

    def test_use_memory_with_json_output_silent(self, runner):
        """Lines 98->100, 105->113: --use-memory + --json suppresses prints."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
            patch("attune.meta_workflows.cli_commands.workflow_commands.PatternLearner"),
            patch(
                "attune.memory.unified.UnifiedMemory",
                return_value=MagicMock(),
            ),
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(
                meta_workflow_app,
                ["run", "release-prep", "--use-memory", "--json"],
            )

        assert result.exit_code == 0
        # No console init message
        assert "Initializing memory" not in result.output
        assert "Memory enabled" not in result.output

    def test_use_memory_with_json_output_failure_silent(self, runner):
        """Line 108->113: --use-memory + --json + memory failure → silent."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
            patch(
                "attune.memory.unified.UnifiedMemory",
                side_effect=RuntimeError("redis down"),
            ),
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(
                meta_workflow_app,
                ["run", "release-prep", "--use-memory", "--json"],
            )

        assert result.exit_code == 0
        # No warning printed in JSON mode
        assert "Memory initialization failed" not in result.output

    def test_use_memory_init_failure_continues(self, runner):
        """Lines 107-110: memory init exception is caught + warning shown."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
            patch(
                "attune.memory.unified.UnifiedMemory",
                side_effect=RuntimeError("redis down"),
            ),
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(meta_workflow_app, ["run", "release-prep", "--use-memory"])

        assert result.exit_code == 0
        assert "Memory initialization failed" in result.output

    def test_json_output(self, runner):
        """Lines 128-159: --json mode prints JSON, no panel output."""
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(meta_workflow_app, ["run", "release-prep", "--json"])

        assert result.exit_code == 0
        # The last line should be JSON
        json_line = result.output.strip().splitlines()[-1]
        data = json.loads(json_line)
        assert data["run_id"] == "run-abc"
        assert data["template_id"] == "release-prep"
        assert data["agents_created"] == 3
        assert data["form_responses"]["template_id"] == "release-prep"
        assert len(data["agent_results"]) == 1

    def test_failure_with_error_shown(self, runner):
        """Lines 174-175: result.error is shown in summary panel."""
        template = _fake_template()
        wf_result = _fake_workflow_result(success=False, error="boom")

        with (
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
        ):
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(meta_workflow_app, ["run", "release-prep"])

        assert result.exit_code == 0
        assert "Failed" in result.output
        assert "boom" in result.output

    def test_unexpected_exception_normal_mode(self, runner):
        """Lines 200-208: exception in normal mode → exit 1 + traceback."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry",
            side_effect=RuntimeError("registry broken"),
        ):
            result = runner.invoke(meta_workflow_app, ["run", "release-prep"])
        assert result.exit_code == 1
        assert "Error:" in result.output

    def test_unexpected_exception_json_mode(self, runner):
        """Lines 200-202: exception in JSON mode → exit 1, JSON error."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry",
            side_effect=RuntimeError("registry broken"),
        ):
            result = runner.invoke(meta_workflow_app, ["run", "release-prep", "--json"])
        assert result.exit_code == 1
        # JSON error printed to stdout
        out = result.output
        # Find the JSON line
        for line in out.strip().splitlines():
            try:
                data = json.loads(line)
                assert data["success"] is False
                assert "registry broken" in data["error"]
                return
            except json.JSONDecodeError:
                continue
        pytest.fail("No JSON error output found")


# ---------------------------------------------------------------------------
# natural_language_run (ask)
# ---------------------------------------------------------------------------


def _fake_match(
    template_id="release-prep",
    template_name="Release Prep",
    confidence=0.75,
    description="Prepare release",
    keywords=None,
):
    return SimpleNamespace(
        template_id=template_id,
        template_name=template_name,
        confidence=confidence,
        description=description,
        matched_keywords=keywords if keywords is not None else ["release", "ship"],
    )


class TestNaturalLanguageRun:
    def test_no_matches_shows_available_teams(self, runner):
        """Lines 247-261: no matches → list available teams."""
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = []
            result = runner.invoke(meta_workflow_app, ["ask", "do something weird"])
        assert result.exit_code == 0
        assert "couldn't identify" in result.output
        assert "release-prep" in result.output

    def test_auto_run_high_confidence(self, runner):
        """Lines 270-285: --auto + confidence >= 0.6 → call run_workflow."""
        match = _fake_match(confidence=0.9)
        template = _fake_template()
        wf_result = _fake_workflow_result()

        with (
            patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID,
            patch(
                "attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry"
            ) as MockReg,
            patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow") as MockWF,
        ):
            MockID.return_value.detect.return_value = [match]
            MockReg.return_value.load_template.return_value = template
            MockWF.return_value.execute.return_value = wf_result
            result = runner.invoke(meta_workflow_app, ["ask", "ship a release", "--auto"])

        assert result.exit_code == 0
        assert "Auto-detected" in result.output
        # The inner run_workflow path should have executed
        MockWF.return_value.execute.assert_called()

    def test_suggestions_displayed_for_low_confidence(self, runner):
        """Lines 290-313: matches without --auto → suggestion list."""
        matches = [
            _fake_match(confidence=0.7, template_id="t1"),
            _fake_match(confidence=0.5, template_id="t2"),
            _fake_match(confidence=0.35, template_id="t3"),
        ]
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = matches
            result = runner.invoke(meta_workflow_app, ["ask", "improve coverage"])
        assert result.exit_code == 0
        assert "Suggested Agent Teams" in result.output
        assert "t1" in result.output
        assert "Quick Run" in result.output  # because best confidence >= 0.5

    def test_suggestions_no_quick_run_hint_when_low_confidence(self, runner):
        """Line 307: best_match.confidence < 0.5 → no Quick Run hint."""
        matches = [_fake_match(confidence=0.4)]
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = matches
            result = runner.invoke(meta_workflow_app, ["ask", "x"])
        assert result.exit_code == 0
        assert "Suggested Agent Teams" in result.output
        assert "Quick Run" not in result.output

    def test_match_without_keywords(self, runner):
        """Line 300: match with empty matched_keywords → skip 'Matched:' line."""
        matches = [_fake_match(confidence=0.7, keywords=[])]
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = matches
            result = runner.invoke(meta_workflow_app, ["ask", "x"])
        assert result.exit_code == 0
        assert "Matched:" not in result.output

    def test_auto_run_low_confidence_falls_through_to_suggestions(self, runner):
        """--auto but confidence < 0.6 → still show suggestions."""
        matches = [_fake_match(confidence=0.55)]
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = matches
            result = runner.invoke(meta_workflow_app, ["ask", "x", "--auto"])
        assert result.exit_code == 0
        # No auto-run, suggestions shown
        assert "Auto-detected" not in result.output
        assert "Suggested Agent Teams" in result.output

    def test_exception_returns_exit_1(self, runner):
        """Lines 315-317: exception → exit code 1."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.IntentDetector",
            side_effect=RuntimeError("detector broken"),
        ):
            result = runner.invoke(meta_workflow_app, ["ask", "x"])
        assert result.exit_code == 1
        assert "Error:" in result.output


# ---------------------------------------------------------------------------
# detect_intent
# ---------------------------------------------------------------------------


class TestDetectIntent:
    def test_no_matches(self, runner):
        """Lines 346-348: no matches above threshold → message + return."""
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = []
            result = runner.invoke(meta_workflow_app, ["detect", "do thing"])
        assert result.exit_code == 0
        assert "No matches above threshold" in result.output

    def test_with_matches_shows_table(self, runner):
        """Lines 351-369: matches → render table with auto-run column."""
        matches = [
            _fake_match(template_id="t1", confidence=0.7),
            _fake_match(template_id="t2", confidence=0.4, keywords=[]),
        ]
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = matches
            result = runner.invoke(meta_workflow_app, ["detect", "ship a release"])
        assert result.exit_code == 0
        assert "Intent Analysis" in result.output
        assert "t1" in result.output
        assert "t2" in result.output

    def test_custom_threshold(self, runner):
        """Threshold flag passed to detector."""
        with patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector") as MockID:
            MockID.return_value.detect.return_value = []
            result = runner.invoke(meta_workflow_app, ["detect", "x", "--threshold", "0.5"])
        assert result.exit_code == 0
        # detector.detect called with threshold=0.5
        MockID.return_value.detect.assert_called_once_with("x", threshold=0.5)

    def test_exception_returns_exit_1(self, runner):
        """Lines 372-374: exception → exit code 1."""
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.IntentDetector",
            side_effect=RuntimeError("broken"),
        ):
            result = runner.invoke(meta_workflow_app, ["detect", "x"])
        assert result.exit_code == 1
        assert "Error:" in result.output
