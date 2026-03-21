"""Tests for the unified voice formatter."""

from datetime import datetime, timezone
from unittest.mock import patch

from attune.voice import personality
from attune.voice.formatter import (
    _extract_from_dict,
    _extract_result_data,
    format_error,
    format_mcp_response,
    format_output,
)
from attune.workflows.data_classes import CostReport, WorkflowResult


def _make_result(
    success: bool = True,
    final_output: dict | None = None,
    error: str | None = None,
    error_type: str | None = None,
    cost_report: CostReport | None = None,
) -> WorkflowResult:
    """Build a minimal WorkflowResult for testing."""
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output or {"formatted_report": "Test report"},
        cost_report=cost_report
        or CostReport(
            total_cost=0.0042,
            baseline_cost=0.01,
            savings=0.0058,
            savings_percent=58.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=1500,
        error=error,
        error_type=error_type,
    )


class TestFormatOutput:
    """Test the main format_output function."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_successful_result_has_greeting(self, _mock):
        """Successful results get a positive opening."""
        result = _make_result(success=True)
        output = format_output("code-review", result)
        assert personality.GREETING_SUCCESS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_failed_result_has_failure_greeting(self, _mock):
        """Failed results get the failure opening."""
        result = _make_result(
            success=False,
            error="Something broke",
        )
        output = format_output("code-review", result)
        assert personality.GREETING_FAILURE in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_report_text(self, _mock):
        """Output includes the formatted report."""
        result = _make_result(
            final_output={"formatted_report": "Found 3 issues"},
        )
        output = format_output("security-audit", result)
        assert "Found 3 issues" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_cost_line(self, _mock):
        """Output includes cost information."""
        result = _make_result()
        output = format_output("test-gen", result)
        assert "$0.0042" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_includes_savings_percent(self, _mock):
        """Output shows savings when available."""
        result = _make_result()
        output = format_output("test-gen", result)
        assert "58%" in output

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["I'd run `attune workflow run test-gen` next — gaps found"],
    )
    def test_includes_next_steps(self, _mock):
        """Output includes next-step suggestions."""
        result = _make_result()
        output = format_output("code-review", result)
        assert "test-gen" in output
        assert personality.HEADER_NEXT_STEPS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_score_commentary_included(self, _mock):
        """Output with a score includes commentary."""
        result = _make_result(
            final_output={"formatted_report": "report", "score": 92},
        )
        output = format_output("security-audit", result)
        assert personality.score_commentary(92) in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_error_details_included(self, _mock):
        """Failed output includes error message."""
        result = _make_result(
            success=False,
            error="API timeout",
            error_type="transient",
        )
        output = format_output("code-review", result)
        assert "API timeout" in output
        assert personality.HEADER_ERROR in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_compact_mode(self, _mock):
        """Compact mode produces output."""
        result = _make_result()
        output = format_output("code-review", result, compact=True)
        assert isinstance(output, str)

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_none_result(self, _mock):
        """None result handled gracefully."""
        output = format_output("code-review", None)
        assert personality.GREETING_SUCCESS in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_string_result(self, _mock):
        """String result passes through."""
        output = format_output("code-review", "All tests passed")
        assert "All tests passed" in output

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_none_cost_report(self, _mock):
        """WorkflowResult with None cost_report handled gracefully."""
        now = datetime.now(timezone.utc)
        result = WorkflowResult(
            success=True,
            stages=[],
            final_output={"formatted_report": "report"},
            cost_report=None,
            started_at=now,
            completed_at=now,
            total_duration_ms=1000,
        )
        output = format_output("code-review", result)
        assert "report" in output
        # No cost line should appear
        assert personality.HEADER_COST not in output


class TestFormatError:
    """Test the format_error function."""

    def test_includes_error_message(self):
        """Error output includes the raw message."""
        output = format_error("Connection refused")
        assert "Connection refused" in output

    def test_includes_error_prefix(self):
        """Error output starts with the voiced prefix."""
        output = format_error("test error")
        assert personality.ERROR_PREFIX in output

    def test_transient_suggests_retry(self):
        """Transient errors include retry suggestion."""
        output = format_error(
            "timeout",
            error_type="transient",
            workflow_name="code-review",
        )
        assert "code-review" in output
        assert "again" in output.lower()

    def test_no_retry_for_non_transient(self):
        """Non-transient errors don't suggest retry."""
        output = format_error("bad input", error_type="validation")
        assert "again" not in output.lower()


class TestFormatMcpResponse:
    """Test the format_mcp_response function."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_preserves_original_fields(self, _mock):
        """MCP response keeps all original dict fields."""
        original = {"success": True, "score": 85, "findings": []}
        result = format_mcp_response("security-audit", original)
        assert result["success"] is True
        assert result["score"] == 85
        assert result["findings"] == []

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_adds_voice_summary(self, _mock):
        """MCP response includes voice_summary field."""
        result = format_mcp_response("code-review", {"success": True, "score": 92})
        assert "voice_summary" in result

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["Try `test-gen` — gaps found"],
    )
    def test_adds_next_steps(self, _mock):
        """MCP response includes next_steps when available."""
        result = format_mcp_response("code-review", {"success": True})
        assert "next_steps" in result
        assert len(result["next_steps"]) == 1

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_failure_voice_summary(self, _mock):
        """Failed MCP response gets failure summary."""
        result = format_mcp_response("code-review", {"success": False})
        assert result["voice_summary"] == personality.GREETING_FAILURE

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    def test_skips_underscore_prefixed_keys(self, _mock):
        """Dict fallback skips _-prefixed internal keys."""
        result = format_mcp_response(
            "code-review",
            {"success": True, "_internal": "hidden", "visible": "shown"},
        )
        assert "_internal" not in result.get("voice_summary", "")


class TestExtractResultData:
    """Test the _extract_result_data helper."""

    def test_string_result(self):
        """String results pass through."""
        success, score, text, cost, error = _extract_result_data("hello")
        assert success is True
        assert text == "hello"
        assert score is None

    def test_dict_result(self):
        """Dict results extract fields."""
        success, score, text, cost, error = _extract_from_dict(
            {"success": True, "score": 80, "info": "details"},
        )
        assert success is True
        assert score == 80

    def test_dict_skips_internal_keys(self):
        """Dict fallback skips _-prefixed keys."""
        _, _, text, _, _ = _extract_from_dict(
            {"_internal": "hidden", "visible": "shown"},
        )
        assert "_internal" not in (text or "")
        assert "visible" in (text or "")

    def test_none_result(self):
        """None result returns safe defaults."""
        success, score, text, cost, error = _extract_result_data(None)
        assert success is True
        assert text is None
