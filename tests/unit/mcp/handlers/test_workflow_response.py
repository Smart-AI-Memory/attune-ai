"""Unit tests for the report-aware MCP response helper (spec T5).

Covers _workflow_response directly (legacy flat-dict picks vs the
serialized-WorkflowReport path) and two handler-level round-trips:
a report-dict final_output through _run_security_audit must carry
the rendered summary markdown verbatim plus the report JSON and
non-empty back-compat findings; a legacy flat-dict final_output
must keep the exact pre-T5 response shape.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import EmpathyMCPServer
from attune.mcp.workflow_handlers import _workflow_response
from attune.voice.report_renderer import render_safe
from attune.workflows.output import Finding, WorkflowReport

# ------------------------------------------------------------------
# Shared helpers (same pattern as test_workflow_handlers.py)
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fixed_show_cost():
    """Pin resolve_show_cost so rendered markdown is deterministic."""
    with patch("attune.config.resolve_show_cost", return_value=False):
        yield


@pytest.fixture()
def _bypass_path_validation():
    """Stub path validation so handler tests work cross-platform."""

    def _passthrough(path, **_kwargs):
        return PurePosixPath(path)

    with patch(
        "attune.security.path_validation._validate_file_path",
        side_effect=_passthrough,
    ):
        yield


def _make_server(workspace_root: str = "/") -> EmpathyMCPServer:
    with patch.object(EmpathyMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return EmpathyMCPServer(workspace_root=workspace_root)


def _make_result(
    success: bool = True,
    final_output: object = None,
    total_cost: float = 0.01,
    metadata: dict | None = None,
) -> MagicMock:
    result = MagicMock()
    result.success = success
    result.final_output = final_output if final_output is not None else {}
    result.cost_report = MagicMock()
    result.cost_report.total_cost = total_cost
    result.provider = "anthropic"
    result.metadata = metadata if metadata is not None else {}
    return result


def _make_workflow_module(module_name: str, class_name: str, result: MagicMock) -> ModuleType:
    mod = ModuleType(module_name)
    workflow_cls = MagicMock()
    workflow_instance = MagicMock()
    workflow_instance.execute = AsyncMock(return_value=result)
    workflow_cls.return_value = workflow_instance
    setattr(mod, class_name, workflow_cls)
    return mod


def _make_report() -> WorkflowReport:
    return WorkflowReport.from_findings(
        "Security audit",
        [
            Finding(severity="high", file="src/app.py", line=10, message="eval() usage"),
            Finding(severity="low", file="src/util.py", line=3, message="TODO left in"),
        ],
        summary="2 issues found.",
        score=72,
    )


# ==================================================================
# _workflow_response — legacy flat-dict path
# ==================================================================


class TestWorkflowResponseLegacy:
    """Legacy flat-dict final_output keeps the exact pre-T5 shape."""

    def test_field_picks_and_defaults(self):
        result = _make_result(final_output={"health_score": 85}, total_cost=0.05)
        out = _workflow_response(
            result,
            include_provider=True,
            score="health_score",
            findings=("findings", []),
        )

        assert out == {
            "success": True,
            "score": 85,
            "findings": [],
            "cost": 0.05,
            "provider": "anthropic",
        }

    def test_missing_keys_default_to_none(self):
        result = _make_result(final_output={})
        out = _workflow_response(result, feedback="feedback", score="quality_score")

        assert out["feedback"] is None
        assert out["score"] is None
        assert "report" not in out
        assert "summary_markdown" not in out

    def test_raw_output_passes_final_output_through(self):
        result = _make_result(final_output={"coverage": 85})
        out = _workflow_response(result, raw_output=True)

        assert out["output"] == {"coverage": 85}

    def test_string_final_output_yields_pick_defaults(self):
        result = _make_result(success=False, final_output="boom", total_cost=0.0)
        out = _workflow_response(result, approved="approved", recommendation="recommendation")

        assert out["success"] is False
        assert out["approved"] is None
        assert out["recommendation"] is None

    def test_prose_string_final_output_gets_panel(self):
        # Family-B: a prose-only run (no parseable findings) leaves
        # final_output a raw markdown string — it should still get a panel.
        result = _make_result(final_output="# Review\n\nAll **good**.", total_cost=0.0)
        out = _workflow_response(result, raw_output=True)

        assert isinstance(out.get("panel_html"), str)
        assert 'id="rp-panel"' in out["panel_html"]
        assert "<strong>good</strong>" in out["panel_html"]
        # raw markdown still passes through unchanged for back-compat
        assert out["output"] == "# Review\n\nAll **good**."

    def test_prose_panel_failed_run_not_a_false_all_clear(self):
        result = _make_result(success=False, final_output="partial output", total_cost=0.0)
        out = _workflow_response(result, raw_output=True)

        assert "did not complete" in out["panel_html"]

    def test_dict_final_output_gets_no_prose_panel(self):
        result = _make_result(final_output={"coverage": 85})
        out = _workflow_response(result, raw_output=True)

        assert "panel_html" not in out

    def test_empty_string_final_output_gets_no_panel(self):
        result = _make_result(final_output="   ", total_cost=0.0)
        out = _workflow_response(result, raw_output=True)

        assert "panel_html" not in out


# ==================================================================
# _workflow_response — serialized WorkflowReport path
# ==================================================================


class TestWorkflowResponseReport:
    """Report-dict final_output carries markdown + report + back-compat."""

    def test_summary_markdown_verbatim_and_report_json(self):
        report = _make_report()
        report_dict = report.to_dict()
        result = _make_result(final_output=report_dict)

        out = _workflow_response(result, score="health_score", findings=("findings", []))

        expected = render_safe(
            WorkflowReport.from_dict(report_dict),
            disclosure="summary",
            show_cost=False,
        )
        assert out["summary_markdown"] == expected
        assert out["report"] == report_dict
        assert out["score"] == 72
        assert len(out["findings"]) == 2
        assert out["findings"][0]["message"] == "eval() usage"

    def test_findings_like_picks_resolve_to_report_findings(self):
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(result, predictions=("predictions", []))

        assert out["predictions"] == out["findings"]
        assert len(out["predictions"]) == 2

    def test_panel_html_attached_on_report_path(self):
        # the universal rich panel rides every WorkflowReport response
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(result)
        assert isinstance(out.get("panel_html"), str)
        assert 'id="rp-panel"' in out["panel_html"]

    def test_panel_html_failure_state(self):
        result = _make_result(success=False, final_output=_make_report().to_dict())
        out = _workflow_response(result)
        assert "did not complete" in out["panel_html"]

    def test_score_like_picks_resolve_to_report_score(self):
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(result, health_score="health_score")

        assert out["health_score"] == 72

    def test_other_picks_resolve_to_defaults(self):
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(
            result, tests_generated=("tests_generated", 0), document="document"
        )

        assert out["tests_generated"] == 0
        assert out["document"] is None

    def test_raw_output_carries_summary_markdown(self):
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(result, raw_output=True)

        assert out["output"] == out["summary_markdown"]

    def test_metadata_findings_fallback_when_report_has_none(self):
        """String-bullet findings live in metadata, not FindingsSection."""
        report = WorkflowReport(title="Doc audit", summary="ok", score=90)
        result = _make_result(
            final_output=report.to_dict(),
            metadata={"findings": {"stale": ["a.md outdated"], "broken": ["b.md 404"]}},
        )

        out = _workflow_response(result)

        assert sorted(out["findings"]) == ["a.md outdated", "b.md 404"]

    def test_report_response_exact_key_set(self):
        """Characterization pin (D-block batch 2): the report-path
        response carries exactly these keys — the refactor cut must
        not add, drop, or rename any."""
        result = _make_result(final_output=_make_report().to_dict())
        out = _workflow_response(result, score="health_score")

        assert set(out.keys()) == {
            "success",
            "summary_markdown",
            "report",
            "score",
            "findings",
            "panel_html",
            "cost",
        }

    def test_cost_zero_when_cost_report_absent(self):
        result = _make_result(final_output={"x": 1})
        result.cost_report = None
        out = _workflow_response(result)

        assert out["cost"] == 0.0


class TestMetadataFindingsEdges:
    """Characterization pins (D-block batch 2) for the metadata-findings
    fallback: each input shape must keep its exact current handling."""

    @staticmethod
    def _empty_report_result(metadata):
        report = WorkflowReport(title="Doc audit", summary="ok", score=90)
        return _make_result(final_output=report.to_dict(), metadata=metadata)

    def test_none_metadata_yields_empty_findings(self):
        result = self._empty_report_result(metadata={})
        result.metadata = None
        out = _workflow_response(result)

        assert out["findings"] == []

    def test_list_metadata_findings_used_verbatim(self):
        result = self._empty_report_result(metadata={"findings": ["a", "b"]})
        out = _workflow_response(result)

        assert out["findings"] == ["a", "b"]

    def test_non_list_values_in_findings_dict_skipped(self):
        result = self._empty_report_result(
            metadata={"findings": {"good": ["kept"], "bad": "skipped-not-a-list"}}
        )
        out = _workflow_response(result)

        assert out["findings"] == ["kept"]

    def test_non_dict_non_list_findings_value_yields_empty(self):
        result = self._empty_report_result(metadata={"findings": "prose"})
        out = _workflow_response(result)

        assert out["findings"] == []


# ==================================================================
# _workflow_response — errored runs surface the real reason
# ==================================================================


class TestWorkflowResponseError:
    """An errored run must carry the real failure message, never swallow it.

    Regression for the QA session 2026-06-29 finding: an SDK-native auth
    failure came back as {success:false, findings:[], cost:0} with NO
    error field, indistinguishable from a clean empty result.
    """

    def test_sdk_is_error_surfaces_raw_result_text(self):
        # SDK-native failure: result.error is None, message lives in metadata.
        result = _make_result(
            success=False,
            final_output="",
            total_cost=0.0,
            metadata={"is_error": True, "raw_result_text": "Invalid API key"},
        )
        result.error = None
        out = _workflow_response(result, findings=("findings", []))

        assert out["success"] is False
        assert out["error"] == "Invalid API key"

    def test_is_error_surfaces_even_when_success_true(self):
        # Adapter can mark success=True while is_error=True; still surface it.
        result = _make_result(
            success=True,
            final_output="",
            metadata={"is_error": True, "raw_result_text": "boom"},
        )
        result.error = None
        out = _workflow_response(result)

        assert out["error"] == "boom"

    def test_canonical_error_field_takes_precedence(self):
        result = _make_result(success=False, final_output="")
        result.error = "config: missing path"
        result.error_type = "config"
        out = _workflow_response(result)

        assert out["error"] == "config: missing path"
        assert out["error_type"] == "config"

    def test_clean_success_has_no_error_key(self):
        result = _make_result(final_output={"health_score": 90})
        result.error = None
        out = _workflow_response(result, score="health_score")

        assert "error" not in out
        assert "error_type" not in out

    def test_errored_without_message_omits_error_key(self):
        # No extractable str message -> don't inject a garbage/empty error.
        result = _make_result(success=False, final_output="")
        result.error = None
        out = _workflow_response(result)

        assert "error" not in out


# ==================================================================
# Handler-level round-trips
# ==================================================================


class TestHandlerReportPath:
    """A report-dict final_output flows through a real handler."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_security_audit_report_response(self):
        server = _make_server()
        report_dict = _make_report().to_dict()
        result = _make_result(final_output=report_dict, total_cost=0.05)
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            out = await server._run_security_audit({"path": "/src"})

        expected = render_safe(
            WorkflowReport.from_dict(report_dict),
            disclosure="summary",
            show_cost=False,
        )
        assert out["summary_markdown"] == expected
        assert out["report"] == report_dict
        assert out["score"] == 72
        assert len(out["findings"]) == 2
        assert out["cost"] == 0.05
        assert out["provider"] == "anthropic"

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_deep_review_output_is_summary_markdown(self):
        server = _make_server()
        report_dict = _make_report().to_dict()
        result = _make_result(final_output=report_dict)
        mod = _make_workflow_module(
            "attune.workflows.deep_review", "DeepReviewAgentSDKWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.deep_review": mod}):
            out = await server._run_deep_review({"path": "/src"})

        assert out["output"] == out["summary_markdown"]
        assert out["report"] == report_dict

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_bypass_path_validation")
    async def test_legacy_flat_dict_shape_unchanged(self):
        """Pre-report (legacy flat-dict) workflows keep the exact shape.

        A flat-dict final_output never hits the report path, so it gets
        no ``panel_html`` — the legacy keys stay exactly as before. (The
        universal ``panel_html`` only attaches on the WorkflowReport path,
        tested in TestWorkflowResponseReport.)
        """
        server = _make_server()
        result = _make_result(
            final_output={"health_score": 85, "findings": ["issue-1"]},
            total_cost=0.05,
        )
        mod = _make_workflow_module(
            "attune.workflows.security_audit", "SecurityAuditWorkflow", result
        )

        with patch.dict(sys.modules, {"attune.workflows.security_audit": mod}):
            out = await server._run_security_audit({"path": "/src"})

        assert out == {
            "success": True,
            "score": 85,
            "findings": ["issue-1"],
            "cost": 0.05,
            "provider": "anthropic",
        }
