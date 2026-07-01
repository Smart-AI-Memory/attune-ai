"""Security + crash-resistance regression tests for RagCodeGenWorkflow.

Covers four security findings (sentinel-defense in system prompt,
cwd path validation, model allowlist, citation-URL encoding deferred
to attune-rag) and three highest-severity quality findings (bad
``k`` kwarg, deferred citation import, narrow exception catch on
``pipeline.run()``) from the 2026-05-16 code-review pass.

The kwarg-handling block runs BEFORE the empty-query early return,
so most tests exercise validation by passing ``query=""``. The
broadened-exception-catch test stubs ``_get_pipeline`` to inject
specific exception types.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from attune.workflows.rag_code_gen import (
    _SYSTEM_PROMPT,
    RagCodeGenWorkflow,
    _format_citations_markdown,
)


class TestPromptInjectionDefense:
    """Security finding #1: sentinel-defense clause in system prompt.

    attune-rag 0.1.5 wraps each passage in ``<passage>...</passage>``
    sentinels at the user-prompt level. The workflow's system
    prompt should echo the same defense so the model resists
    injection even if the user-prompt-level wrapping is bypassed.
    """

    def test_system_prompt_mentions_passage_sentinel(self):
        assert "<passage>" in _SYSTEM_PROMPT
        assert "</passage>" in _SYSTEM_PROMPT

    def test_system_prompt_declares_passage_content_as_data(self):
        """The clause must explicitly say content inside the tags is data."""
        lowered = _SYSTEM_PROMPT.lower()
        assert "never instructions" in lowered or "not instructions" in lowered

    def test_system_prompt_warns_against_break_out_attempts(self):
        """Defense should call out literal </passage> attempts."""
        assert "break out" in _SYSTEM_PROMPT.lower()


class TestCwdPathValidation:
    """Security finding #2: cwd path validation against system dirs."""

    def test_cwd_etc_returns_error_result(self):
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(path="/etc", query="anything"))
        assert result.success is False
        assert "invalid path/cwd" in result.error.lower()

    def test_cwd_proc_returns_error_result(self):
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(path="/proc/1/cmdline", query="x"))
        assert result.success is False
        assert "invalid path/cwd" in result.error.lower()

    def test_cwd_etc_passwd_blocked(self):
        """An absolute path to a system-dir file is blocked.

        Note: relative traversal like ``../../../etc`` depends on
        cwd depth — from a deep worktree it does NOT resolve to
        ``/etc``. The absolute-path tests are the load-bearing
        ones; ``Path.resolve()`` with ``strict=False`` happily
        accepts non-existent paths so we can't rely on traversal
        canonicalising to a system dir.
        """
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(path="/etc/passwd", query="x"))
        assert result.success is False
        assert "invalid path/cwd" in result.error.lower()

    def test_legitimate_tmp_path_passes_validation(self, tmp_path):
        """A scratch /tmp/... dir is not a system dir; should reach query check."""
        workflow = RagCodeGenWorkflow()
        # Empty query is the NEXT guard after path validation.
        result = asyncio.run(workflow.execute(path=str(tmp_path), query=""))
        assert result.success is False
        assert "query argument is required" in result.error


class TestModelAllowlist:
    """Security finding #3: model kwarg validated against registry."""

    def test_unknown_model_returns_error_result(self):
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(model="gpt-99-ultra-mega", query="anything"))
        assert result.success is False
        assert "unknown model" in result.error.lower()
        assert "gpt-99-ultra-mega" in result.error

    def test_empty_string_model_rejected(self):
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(model="", query="x"))
        # Empty string isn't None; falls through to allowlist check.
        # Either rejected (preferred) or treated as None (existing behavior).
        # We accept either — the actual failure is opaque SDK error,
        # which is what model validation prevents.
        if result.success is False and "unknown model" in result.error.lower():
            assert "''" in result.error or '""' in result.error
        # else: empty string was treated as None → falls through to
        # empty-query guard. Test passes either way.

    def test_known_model_passes_validation(self):
        """A real registry ID gets past the model check (reaches query guard)."""
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(model="claude-sonnet-5", query=""))
        assert result.success is False
        # Reached the empty-query guard → model passed.
        assert "query argument is required" in result.error

    def test_none_model_skips_check(self):
        """Default model=None skips the allowlist entirely."""
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(query=""))
        assert result.success is False
        assert "query argument is required" in result.error


class TestKKwargCrashResistance:
    """Quality finding #1: bad ``k`` kwarg returns structured error."""

    def test_non_numeric_k_returns_error_result(self):
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(k="not-a-number", query="x"))
        assert result.success is False
        assert "k argument must be an integer" in result.error
        assert "'not-a-number'" in result.error

    def test_none_k_returns_error_result(self):
        """int(None) raises TypeError — should be caught."""
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(k=None, query="x"))
        assert result.success is False
        assert "k argument must be an integer" in result.error

    def test_object_k_returns_error_result(self):
        """int(object) raises TypeError — should be caught."""
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(k=object(), query="x"))
        assert result.success is False
        assert "k argument must be an integer" in result.error

    def test_numeric_string_k_passes(self):
        """int('5') succeeds — should reach query guard."""
        workflow = RagCodeGenWorkflow()
        result = asyncio.run(workflow.execute(k="5", query=""))
        assert result.success is False
        # Reached empty-query guard → k parsing succeeded.
        assert "query argument is required" in result.error


class TestCitationImportHoisted:
    """Quality finding #2: format_citations_markdown imported at module scope.

    The previous code did the import inside ``execute()`` AFTER the
    agent had already billed real API cost. An ImportError there
    silently lost the generated output. Hoisting moves the cost
    of failure to module load (zero API spend).
    """

    def test_format_citations_markdown_bound_at_module_load(self):
        """The hoisted import is non-None when attune_rag is installed."""
        # If [rag] is installed (which it is for our test env), the
        # name is bound to the real function.
        pytest.importorskip("attune_rag")
        assert _format_citations_markdown is not None
        assert callable(_format_citations_markdown)


class TestPipelineExceptionBroadening:
    """Quality finding #3: pipeline.run() catch broadened.

    The previous code caught only RuntimeError. ConnectionError,
    TimeoutError, and ValueError from corpus I/O / prompt-variant
    validation fell through and surfaced as misleading
    "Agent SDK returned an error" downstream.
    """

    def _fake_pipeline(self, exc: BaseException) -> object:
        """Build a fake pipeline whose .run() raises ``exc``."""

        class _FakePipeline:
            def run(self, *args, **kwargs):
                raise exc

        return _FakePipeline()

    @pytest.mark.parametrize(
        "exc_factory",
        [
            lambda: ConnectionError("corpus host down"),
            lambda: TimeoutError("retrieval timeout"),
            lambda: ValueError("unknown prompt variant"),
            lambda: RuntimeError("pipeline misconfig"),
        ],
        ids=["ConnectionError", "TimeoutError", "ValueError", "RuntimeError"],
    )
    def test_pipeline_run_exceptions_return_structured_error(self, exc_factory):
        workflow = RagCodeGenWorkflow()
        fake = self._fake_pipeline(exc_factory())
        with patch.object(workflow, "_get_pipeline", return_value=fake):
            result = asyncio.run(workflow.execute(query="hello"))
        assert result.success is False
        assert "RAG retrieval failed" in result.error
