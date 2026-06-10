"""Tests for T3 voice wiring: WorkflowReport detection, the safety
net, and resolve_show_cost (workflow-result-formatting design D2/D3).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from unittest.mock import patch

from attune.config import AttuneConfig
from attune.voice.formatter import (
    _extract_from_workflow_result,
    _safety_net_text,
    format_output,
    resolve_show_cost,
)
from attune.workflows.data_classes import CostReport, WorkflowResult
from attune.workflows.output import (
    Finding,
    ProseSection,
    WorkflowReport,
)


def _make_result(final_output, success: bool = True) -> WorkflowResult:
    now = datetime.now(timezone.utc)
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output,
        cost_report=CostReport(
            total_cost=0.0042,
            baseline_cost=0.01,
            savings=0.0058,
            savings_percent=58.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=1500,
    )


def _report(**kwargs) -> WorkflowReport:
    defaults = {
        "title": "Security Audit",
        "summary": "Looked at 12 files, found 2 issues worth your time.",
        "score": 87,
        "sections": [
            ProseSection(title="Overview", tier="essential", text="All quiet."),
        ],
    }
    defaults.update(kwargs)
    return WorkflowReport(**defaults)


class TestWorkflowReportBranch:
    """_extract_from_workflow_result detects serialized WorkflowReports."""

    def test_renders_report_dict_as_markdown(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(_report().to_dict())

        success, score, report_text, cost_line, error = _extract_from_workflow_result(result)

        assert success is True
        assert "# Security Audit" in report_text
        assert "All quiet." in report_text
        assert error is None

    def test_score_comes_from_report(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(_report(score=64).to_dict())

        _, score, _, _, _ = _extract_from_workflow_result(result)

        assert score == 64

    def test_cost_line_suppressed_for_rendered_report(self, monkeypatch):
        """The renderer owns cost for migrated workflows — no double display."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result(_report().to_dict())

        _, _, _, cost_line, _ = _extract_from_workflow_result(result)

        assert cost_line is None

    def test_no_cost_line_when_cost_report_missing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = _make_result({"formatted_report": "plain report text " * 5})
        result.cost_report = None

        _, _, _, cost_line, _ = _extract_from_workflow_result(result)

        assert cost_line is None

    def test_minimal_report_not_overridden_by_sparse_fallback(self, monkeypatch):
        """A rendered report under 50 chars is authoritative, not 'sparse'."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        tiny = WorkflowReport(title="Hi")
        result = _make_result(tiny.to_dict())
        result.metadata = {"findings": {"bugs": ["should not appear"]}}

        _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert report_text.strip() == "# Hi"
        assert "should not appear" not in report_text

    def test_show_cost_true_renders_cost_line_from_metadata(self, monkeypatch):
        report = _report(metadata={"cost_usd": 0.42, "duration_s": 12.5})
        result = _make_result(report.to_dict())

        with patch("attune.voice.formatter.resolve_show_cost", return_value=True):
            _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert "Cost & time" in report_text
        assert "$0.42" in report_text

    def test_show_cost_false_hides_cost_line(self, monkeypatch):
        report = _report(metadata={"cost_usd": 0.42, "duration_s": 12.5})
        result = _make_result(report.to_dict())

        with patch("attune.voice.formatter.resolve_show_cost", return_value=False):
            _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert "Cost & time" not in report_text

    def test_malformed_report_dict_degrades_without_crash(self, monkeypatch):
        """from_dict failure falls through to plain-dict handling."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        bad = {"_type": "WorkflowReport", "title": "X", "sections": 42}
        result = _make_result(bad)

        success, score, report_text, _, _ = _extract_from_workflow_result(result)

        assert success is True  # no exception escaped

    def test_format_output_end_to_end_with_report(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        report = WorkflowReport.from_findings(
            "Bug Predict",
            [Finding(severity="high", file="a.py", line=1, message="eval misuse")],
            score=70,
        )
        result = _make_result(report.to_dict())

        with patch("attune.voice.formatter.get_next_steps", return_value=[]):
            out = format_output("bug-predict", result)

        assert "# Bug Predict" in out
        assert "eval misuse" in out
        assert "object at 0x" not in out


class _Confidence(Enum):
    HIGH = "high"


@dataclass
class _BespokeReport:
    approved: bool = True
    confidence: _Confidence = _Confidence.HIGH
    blockers: list = field(default_factory=list)
    gates: list = field(default_factory=lambda: ["a", "b", "c"])


class TestSafetyNet:
    """The bare str() branch is now a banner'd pretty-printer."""

    def test_bespoke_dataclass_gets_banner_and_fields(self):
        result = _make_result(_BespokeReport())

        _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert "Renderer not yet migrated for _BespokeReport" in report_text
        assert "approved: True" in report_text
        assert "confidence: high" in report_text  # enum -> .value
        assert "blockers: (empty)" in report_text
        assert "gates: [3 items]" in report_text
        assert "object at 0x" not in report_text

    def test_plain_string_passes_through_without_banner(self):
        result = _make_result("Everything looks great. " * 5)

        _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert "Renderer not yet migrated" not in report_text
        assert "Everything looks great." in report_text

    def test_primitive_gets_banner_with_value(self):
        text = _safety_net_text(42)

        assert "Renderer not yet migrated for int" in text
        assert "42" in text

    def test_plain_object_lists_public_attrs_only(self):
        class Thing:
            def __init__(self):
                self.visible = "yes"
                self._hidden = "no"

        text = _safety_net_text(Thing())

        assert "visible: yes" in text
        assert "_hidden" not in text

    def test_dict_and_nested_dataclass_values(self):
        @dataclass
        class Inner:
            x: int = 1

        @dataclass
        class Outer:
            meta: dict = field(default_factory=lambda: {"a": 1, "b": 2})
            empty_meta: dict = field(default_factory=dict)
            child: Inner = field(default_factory=Inner)

        text = _safety_net_text(Outer())

        assert "meta: [2 keys]" in text
        assert "empty_meta: (empty)" in text
        assert "child: Inner" in text
        assert "object at 0x" not in text

    def test_none_final_output_uses_summary_fallback(self):
        result = _make_result(None)
        result.metadata = {"findings": {"bugs": ["found one"]}}

        _, _, report_text, _, _ = _extract_from_workflow_result(result)

        assert "found one" in report_text
        assert "Renderer not yet migrated" not in report_text


class TestResolveShowCost:
    """Design D3: explicit config wins; None means auto via API key."""

    def test_explicit_true_wins_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cfg = AttuneConfig(show_cost_metrics=True)

        assert resolve_show_cost(cfg) is True

    def test_explicit_false_wins_over_api_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        cfg = AttuneConfig(show_cost_metrics=False)

        assert resolve_show_cost(cfg) is False

    def test_auto_on_for_api_key_users(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        cfg = AttuneConfig()  # show_cost_metrics defaults to None

        assert resolve_show_cost(cfg) is True

    def test_auto_off_for_subscription_users(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cfg = AttuneConfig()

        assert resolve_show_cost(cfg) is False

    def test_empty_api_key_counts_as_absent(self, monkeypatch):
        """CI sets the secret to '' — empty must mean off, not on."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        cfg = AttuneConfig()

        assert resolve_show_cost(cfg) is False

    def test_loads_config_when_omitted(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)  # no repo config files in scope
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        assert resolve_show_cost() is False

    def test_config_load_failure_degrades_to_auto(self, monkeypatch):
        """A broken config must never break output formatting."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        def _boom(*args, **kwargs):
            raise RuntimeError("config exploded")

        monkeypatch.setattr("attune.config.load_config", _boom)

        assert resolve_show_cost() is True


class TestConfigField:
    """AttuneConfig.show_cost_metrics field + env parsing."""

    def test_defaults_to_none(self):
        assert AttuneConfig().show_cost_metrics is None

    def test_from_env_parses_true(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_SHOW_COST_METRICS", "true")

        assert AttuneConfig.from_env().show_cost_metrics is True

    def test_from_env_parses_false(self, monkeypatch):
        monkeypatch.setenv("ATTUNE_SHOW_COST_METRICS", "false")

        assert AttuneConfig.from_env().show_cost_metrics is False

    def test_from_env_absent_stays_none(self, monkeypatch):
        monkeypatch.delenv("ATTUNE_SHOW_COST_METRICS", raising=False)
        monkeypatch.delenv("EMPATHY_SHOW_COST_METRICS", raising=False)

        assert AttuneConfig.from_env().show_cost_metrics is None
