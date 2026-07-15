"""Characterization pins closing RagCodeGenWorkflow.execute() coverage gaps.

Batch-4 D-block cut (docs/reports/d-block-triage-2026-07-14.md).
``execute()`` (D24) is being decomposed into stage helpers; these pins
cover branches the existing suites (test_rag_code_gen_security.py,
test_rag_code_gen_path_kwarg.py, test_task_budget_wiring.py,
test_sdk_error_fidelity_phase5.py) left unexercised: the full
happy-path result assembly (citations + model kwarg threading +
feedback recording) and the ImportError/ConnectionError branches of
the Agent SDK generation call.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

pytest.importorskip("claude_agent_sdk")
pytest.importorskip("attune_rag")

from attune.workflows.rag_code_gen import RagCodeGenWorkflow  # noqa: E402


class _FakeHit:
    template_path = "templates/howto/security-audit.md"
    category = "howto"
    score = 0.87
    excerpt = None


class _FakeCitation:
    query = "how do I run a security audit?"
    hits = [_FakeHit()]
    retriever_name = "attune-help"
    retrieved_at = datetime.now(timezone.utc)


class _FakeRagResult:
    augmented_prompt = "### CONTEXT\n\n<passage>x</passage>\n\n### USER REQUEST\n\nhi"
    context = "<passage>x</passage>"
    citation = _FakeCitation()
    confidence = 0.9
    fallback_used = False
    elapsed_ms = 3.0


class _FakePipeline:
    def run(self, *a, **k):
        return _FakeRagResult()


def _capture_options(kwargs_bucket: dict):
    """Patch ClaudeAgentOptions so its kwargs are recorded before delegating."""
    import claude_agent_sdk

    real = claude_agent_sdk.ClaudeAgentOptions

    def _capture(**kw):
        kwargs_bucket.update(kw)
        return real(**kw)

    return patch("attune.workflows.rag_code_gen.claude_agent_sdk.ClaudeAgentOptions", _capture)


def _fake_stream(*_a, **_k):
    import claude_agent_sdk

    async def _gen():
        yield claude_agent_sdk.ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=0,
            session_id=None,
            total_cost_usd=0.0,
            usage={"input_tokens": 0, "output_tokens": 0},
            result="generated code",
            structured_output=None,
        )

    return _gen()


class TestExecuteHappyPathAssembly:
    """Full run: citations appended, model threaded through, feedback recorded."""

    def test_happy_path_appends_citations_and_threads_model(self):
        workflow = RagCodeGenWorkflow()
        captured: dict[str, object] = {}

        with (
            patch.object(workflow, "_get_pipeline", return_value=_FakePipeline()),
            _capture_options(captured),
            patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", _fake_stream),
        ):
            result = asyncio.run(
                workflow.execute(query="how do I run a security audit?", model="claude-sonnet-5")
            )

        assert result.success is True
        assert "## Sources" in result.final_output
        assert "templates/howto/security-audit.md" in result.final_output
        assert captured.get("model") == "claude-sonnet-5"
        assert result.metadata["citation"]["retriever_name"] == "attune-help"
        assert result.metadata["fallback_used"] is False

    def test_happy_path_records_feedback_for_each_cited_hit(self):
        workflow = RagCodeGenWorkflow()

        with (
            patch.object(workflow, "_get_pipeline", return_value=_FakePipeline()),
            patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", _fake_stream),
            patch.object(workflow, "_record_feedback") as mock_feedback,
        ):
            result = asyncio.run(
                workflow.execute(query="how do I run a security audit?", feedback="good")
            )

        assert result.success is True
        mock_feedback.assert_called_once()
        args, _ = mock_feedback.call_args
        assert args[1] == "good"
        assert result.metadata["feedback_recorded"] == "good"

    def test_happy_path_skips_feedback_when_not_requested(self):
        workflow = RagCodeGenWorkflow()

        with (
            patch.object(workflow, "_get_pipeline", return_value=_FakePipeline()),
            patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", _fake_stream),
            patch.object(workflow, "_record_feedback") as mock_feedback,
        ):
            result = asyncio.run(workflow.execute(query="how do I run a security audit?"))

        mock_feedback.assert_not_called()
        assert result.metadata["feedback_recorded"] is None


class TestRunAgentGenerateExceptionBranches:
    """execute() wraps _run_agent_generate in three distinct except clauses."""

    def test_import_error_returns_structured_unavailable_error(self):
        workflow = RagCodeGenWorkflow()

        with (
            patch.object(workflow, "_get_pipeline", return_value=_FakePipeline()),
            patch.object(
                workflow,
                "_run_agent_generate",
                AsyncMock(side_effect=ImportError("claude_agent_sdk missing")),
            ),
        ):
            result = asyncio.run(workflow.execute(query="hello"))

        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    @pytest.mark.parametrize(
        "exc",
        [ConnectionError("host unreachable"), TimeoutError("agent run timed out")],
        ids=["ConnectionError", "TimeoutError"],
    )
    def test_network_error_returns_structured_connection_error(self, exc):
        workflow = RagCodeGenWorkflow()

        with (
            patch.object(workflow, "_get_pipeline", return_value=_FakePipeline()),
            patch.object(workflow, "_run_agent_generate", AsyncMock(side_effect=exc)),
        ):
            result = asyncio.run(workflow.execute(query="hello"))

        assert result.success is False
        assert "Agent SDK connection failed" in result.error


class TestRecordFeedbackMethod:
    """_record_feedback: best-effort per-hit recording, never raises."""

    def test_records_feedback_for_every_hit(self):
        workflow = RagCodeGenWorkflow()
        with patch("attune.help.feedback.record_template_feedback") as mock_record:
            workflow._record_feedback(_FakeRagResult(), "good")

        mock_record.assert_called_once_with("templates/howto/security-audit.md", "good")

    def test_swallows_per_hit_recording_exception(self):
        workflow = RagCodeGenWorkflow()
        with patch(
            "attune.help.feedback.record_template_feedback",
            side_effect=RuntimeError("backend unavailable"),
        ):
            # Must not raise — best-effort per the docstring contract.
            workflow._record_feedback(_FakeRagResult(), "bad")
