"""Integration tests for RagCodeGenWorkflow.

The Claude Agent SDK is mocked so tests don't hit the
network. The RAG pipeline is exercised end-to-end against
an in-memory corpus to prove retrieval -> prompt assembly
-> workflow-result wiring works.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from unittest.mock import patch

import pytest

from attune.workflows.rag_code_gen import RagCodeGenWorkflow

pytest_plugins: list[str] = []


# ---------------------------------------------------------------------------
# Fixtures: in-memory corpus + mocked Claude Agent SDK stream
# ---------------------------------------------------------------------------


def _make_fake_corpus():
    from attune_rag import RetrievalEntry
    from attune_rag.corpus.base import CorpusProtocol

    class _FakeCorpus(CorpusProtocol):
        def __init__(self) -> None:
            self._entries = {
                "concepts/tool-security-audit.md": RetrievalEntry(
                    path="concepts/tool-security-audit.md",
                    category="concepts",
                    content="Security audit scans for vulnerabilities.",
                    summary="Run a security audit",
                ),
                "concepts/other.md": RetrievalEntry(
                    path="concepts/other.md",
                    category="concepts",
                    content="Unrelated content.",
                ),
            }

        def entries(self) -> Iterable:
            return tuple(self._entries.values())

        def get(self, path: str):
            return self._entries.get(path)

        @property
        def name(self) -> str:
            return "fake-corpus"

        @property
        def version(self) -> str:
            return "test-1"

    return _FakeCorpus()


def _make_assistant_message(text: str):
    """Build a real claude_agent_sdk.AssistantMessage so the
    isinstance checks in collect_agent_output pass."""
    import claude_agent_sdk

    return claude_agent_sdk.AssistantMessage(
        content=[claude_agent_sdk.types.TextBlock(text=text)],
        model="claude-sonnet-4-6",
        parent_tool_use_id=None,
    )


def _make_result_message(result: str | None = None):
    import claude_agent_sdk

    return claude_agent_sdk.ResultMessage(
        subtype="success",
        duration_ms=250,
        duration_api_ms=200,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        total_cost_usd=0.001,
        usage={"input_tokens": 100, "output_tokens": 50},
        result=result,
        structured_output=None,
    )


def _make_fake_sdk_stream(
    generated_text: str = "Here is your grounded code.",
) -> AsyncIterator:
    """Yields a minimal assistant + result message pair."""

    async def stream(*args, **kwargs):  # noqa: ARG001
        yield _make_assistant_message(generated_text)
        yield _make_result_message(result=None)

    return stream


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_default_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the workflow's pipeline to use an in-memory corpus."""
    from attune_rag import pipeline

    monkeypatch.setattr(pipeline.RagPipeline, "_default_corpus", staticmethod(_make_fake_corpus))


def test_execute_returns_workflow_result_with_citations() -> None:
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("Here is your grounded code snippet.")

    with patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream):
        result = asyncio.run(workflow.execute(query="security audit"))

    assert result.success is True
    assert result.error is None
    assert "grounded code snippet" in str(result.final_output)
    # Metadata carries the citation dict
    assert "citation" in result.metadata
    citation = result.metadata["citation"]
    assert citation["retriever_name"] == "KeywordRetriever"
    assert any("security-audit" in h["template_path"] for h in citation["hits"])


def test_execute_emits_sources_block_in_output() -> None:
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("generated answer")

    with patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream):
        result = asyncio.run(workflow.execute(query="security audit"))

    output = str(result.final_output)
    assert "## Sources" in output


def test_execute_empty_query_returns_error_result() -> None:
    workflow = RagCodeGenWorkflow()
    result = asyncio.run(workflow.execute(query=""))
    assert result.success is False
    assert result.error is not None
    assert "query" in result.error.lower()


def test_fallback_when_no_matching_context() -> None:
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("I don't know about that.")

    with patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream):
        result = asyncio.run(workflow.execute(query="zzzzz asdfgh qwerty"))

    assert result.success is True
    assert result.metadata["fallback_used"] is True
    assert result.metadata["confidence"] == 0.0
    # No citations when fallback was used
    assert result.metadata["citation"]["hits"] == []
    # "No grounding sources" message still appears in output
    assert "No grounding sources" in str(result.final_output)


def test_depth_controls_max_turns() -> None:
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("result")

    with patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream):
        result = asyncio.run(workflow.execute(query="security audit", depth="deep"))
    assert result.metadata["max_turns"] == 24

    with patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream):
        result = asyncio.run(workflow.execute(query="security audit", depth="quick"))
    assert result.metadata["max_turns"] == 6


def test_feedback_kwarg_recorded() -> None:
    """feedback='good' fires record_template_feedback for each cited template."""
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("result")

    with (
        patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream),
        patch("attune.help.feedback.record_template_feedback") as mock_record,
    ):
        result = asyncio.run(workflow.execute(query="security audit", feedback="good"))

    assert result.metadata["feedback_recorded"] == "good"
    # One call per cited hit
    assert mock_record.call_count == len(result.metadata["citation"]["hits"])
    for call in mock_record.call_args_list:
        assert call.args[1] == "good"


def test_no_feedback_kwarg_leaves_backend_untouched() -> None:
    workflow = RagCodeGenWorkflow()
    fake_stream = _make_fake_sdk_stream("result")

    with (
        patch("attune.workflows.rag_code_gen.claude_agent_sdk.query", fake_stream),
        patch("attune.help.feedback.record_template_feedback") as mock_record,
    ):
        result = asyncio.run(workflow.execute(query="security audit"))

    assert result.metadata["feedback_recorded"] is None
    mock_record.assert_not_called()


def test_workflow_registered_in_registry() -> None:
    """rag-code-gen must be listed in _DEFAULT_WORKFLOW_NAMES so
    `attune workflow list` shows it and the resolver can look it up."""
    from attune.workflows import _DEFAULT_WORKFLOW_NAMES

    assert "rag-code-gen" in _DEFAULT_WORKFLOW_NAMES
    assert _DEFAULT_WORKFLOW_NAMES["rag-code-gen"] == "RagCodeGenWorkflow"


def test_workflow_class_has_expected_attributes() -> None:
    assert RagCodeGenWorkflow.name == "rag-code-gen"
    assert "retrieve" in RagCodeGenWorkflow.stages
    assert "generate" in RagCodeGenWorkflow.stages
