"""Tests for the `path=` kwarg migration in RagCodeGenWorkflow.

PR-4 of workflow-path-arg-unification (2026-05-13) renames the
`cwd=` kwarg on `RagCodeGenWorkflow.execute()` to `path=`, with
`cwd=` preserved as a deprecated alias. The two are semantically
identical for this workflow (both bound the Agent SDK's
filesystem-tool reach via `ClaudeAgentOptions(cwd=...)`).

These tests exercise just the kwarg-handling logic — the warning
fires before the empty-query early-return, so we don't need the
RAG pipeline wired up to validate behavior.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import warnings

import pytest

from attune.workflows.rag_code_gen import RagCodeGenWorkflow


class TestExecutePathKwarg:
    """Tests for the `path=` kwarg migration."""

    def test_execute_accepts_path_kwarg_without_warning(self):
        """execute(path=..., query="") does not emit DeprecationWarning."""
        workflow = RagCodeGenWorkflow()

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            result = asyncio.run(workflow.execute(path="/tmp/scope", query=""))

        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert deprecations == []
        # Empty query triggers the next guard (proves we reached the body).
        assert result.success is False
        assert "query argument is required" in result.error

    def test_execute_legacy_cwd_warns(self):
        """execute(cwd=...) emits DeprecationWarning AND still routes the value."""
        workflow = RagCodeGenWorkflow()

        with pytest.warns(DeprecationWarning, match="cwd"):
            result = asyncio.run(workflow.execute(cwd="/tmp/scope", query=""))

        # Workflow still proceeds past the kwarg-handling block.
        assert result.success is False
        assert "query argument is required" in result.error

    def test_execute_both_kwargs_path_wins(self):
        """execute(path=A, cwd=B) emits a both-supplied warning."""
        workflow = RagCodeGenWorkflow()

        with pytest.warns(DeprecationWarning, match="both"):
            result = asyncio.run(
                workflow.execute(path="/tmp/via_path", cwd="/tmp/via_cwd", query="")
            )

        assert result.success is False
        assert "query argument is required" in result.error

    def test_execute_no_path_or_cwd_no_warning(self):
        """execute() with neither path nor cwd defaults to os.getcwd() silently."""
        workflow = RagCodeGenWorkflow()

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            result = asyncio.run(workflow.execute(query=""))

        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert deprecations == []
        assert result.success is False
        assert "query argument is required" in result.error
