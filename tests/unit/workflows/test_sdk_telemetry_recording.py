"""Regression tests for SDK-workflow telemetry recording.

Pre-2026-05-19: SDK-native workflows (bug_predict, code_review, etc.) bypassed
the legacy ``llm_mixin`` path that calls ``_track_telemetry()``. As a result,
``usage.jsonl`` was never written for SDK runs and the dashboard's home /
telemetry KPIs went stale.

The fix added ``_track_sdk_run_telemetry()`` on ``TelemetryMixin`` and wired
each SDK workflow to call it after the message-collection loop. These tests
pin that contract.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.workflows.agent_sdk_adapter import AgentRunResult
from attune.workflows.telemetry_mixin import TelemetryMixin


@pytest.fixture
def wired_mixin() -> TelemetryMixin:
    """A TelemetryMixin with a mocked tracker, ready to record."""
    mixin = TelemetryMixin()
    mixin._telemetry_tracker = MagicMock()
    mixin._enable_telemetry = True
    mixin.name = "bug-predict"
    mixin._provider_str = "anthropic"
    return mixin


@pytest.mark.unit
class TestSdkRunTelemetryRecording:
    """Pin the SDK telemetry wiring contract."""

    def test_records_successful_run(self, wired_mixin):
        """Successful runs with non-zero cost write to the tracker."""
        result = AgentRunResult(
            result_text="ok",
            total_cost_usd=3.62,
            usage={"input_tokens": 12345, "output_tokens": 678},
            duration_ms=77800,
        )

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        wired_mixin._telemetry_tracker.track_llm_call.assert_called_once()
        kwargs = wired_mixin._telemetry_tracker.track_llm_call.call_args.kwargs
        assert kwargs["workflow"] == "bug-predict"
        assert kwargs["stage"] == "agent"
        assert kwargs["cost"] == 3.62
        assert kwargs["tokens"] == {"input": 12345, "output": 678}
        assert kwargs["duration_ms"] == 77800
        assert kwargs["tier"] == "SDK"
        assert kwargs["model"] == "agent-sdk"

    def test_skips_errored_run(self, wired_mixin):
        """is_error=True runs are skipped (cost is unreliable)."""
        result = AgentRunResult(
            result_text="",
            total_cost_usd=2.50,
            is_error=True,
        )

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        wired_mixin._telemetry_tracker.track_llm_call.assert_not_called()

    def test_skips_zero_cost_run(self, wired_mixin):
        """Zero-cost runs (startup failures) are skipped."""
        result = AgentRunResult(
            result_text="",
            total_cost_usd=0.0,
        )

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        wired_mixin._telemetry_tracker.track_llm_call.assert_not_called()

    def test_skips_none_cost_run(self, wired_mixin):
        """None cost (no ResultMessage received) is skipped."""
        result = AgentRunResult(result_text="")  # total_cost_usd defaults to None

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        wired_mixin._telemetry_tracker.track_llm_call.assert_not_called()

    def test_skips_when_tracker_unavailable(self, wired_mixin):
        """No-op when telemetry tracker hasn't been initialized."""
        wired_mixin._telemetry_tracker = None
        result = AgentRunResult(result_text="ok", total_cost_usd=1.0)

        # Should not raise
        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

    def test_skips_when_telemetry_disabled(self, wired_mixin):
        """No-op when telemetry is explicitly disabled."""
        wired_mixin._enable_telemetry = False
        result = AgentRunResult(result_text="ok", total_cost_usd=1.0)

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        wired_mixin._telemetry_tracker.track_llm_call.assert_not_called()

    def test_records_prompt_cache_tokens(self, wired_mixin):
        """Cache-creation and cache-read tokens flow through when present."""
        result = AgentRunResult(
            result_text="ok",
            total_cost_usd=1.0,
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 300,
            },
        )

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        kwargs = wired_mixin._telemetry_tracker.track_llm_call.call_args.kwargs
        assert kwargs["prompt_cache_creation_tokens"] == 200
        assert kwargs["prompt_cache_read_tokens"] == 300

    def test_handles_missing_usage_dict(self, wired_mixin):
        """Missing usage dict yields zero token counts, not a crash."""
        result = AgentRunResult(result_text="ok", total_cost_usd=1.0, usage=None)

        wired_mixin._track_sdk_run_telemetry(stage="agent", agent_run_result=result)

        kwargs = wired_mixin._telemetry_tracker.track_llm_call.call_args.kwargs
        assert kwargs["tokens"] == {"input": 0, "output": 0}


@pytest.mark.unit
class TestSdkWorkflowsCallTelemetry:
    """Drift guard: every SDK workflow must invoke ``_track_sdk_run_telemetry``."""

    SDK_WORKFLOW_FILES = [
        "src/attune/workflows/bug_predict.py",
        "src/attune/workflows/code_review.py",
        "src/attune/workflows/dependency_check.py",
        "src/attune/workflows/deep_review.py",
        "src/attune/workflows/perf_audit.py",
        "src/attune/workflows/release_prep.py",
        "src/attune/workflows/rag_code_gen.py",
        "src/attune/workflows/security_audit.py",
        "src/attune/workflows/research_synthesis.py",
        "src/attune/workflows/refactor_plan.py",
        "src/attune/workflows/simplify_code.py",
        "src/attune/workflows/doc_audit/workflow.py",
        "src/attune/workflows/document_gen/workflow.py",
        "src/attune/workflows/test_gen/workflow.py",
        "src/attune/workflows/test_audit/workflow.py",
    ]

    @pytest.mark.parametrize("workflow_path", SDK_WORKFLOW_FILES)
    def test_workflow_wires_sdk_telemetry(self, workflow_path):
        """Each SDK workflow must call ``_track_sdk_run_telemetry``.

        If a future workflow is added that uses ``claude_agent_sdk.query()``
        without this call, ``usage.jsonl`` silently goes stale for that
        workflow. Update this list AND wire the call when adding new SDK
        workflows.
        """
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[3]
        text = (repo_root / workflow_path).read_text(encoding="utf-8")
        assert "_track_sdk_run_telemetry" in text, (
            f"{workflow_path} uses the SDK but never calls "
            "_track_sdk_run_telemetry() — usage.jsonl won't reflect "
            "this workflow's runs."
        )
