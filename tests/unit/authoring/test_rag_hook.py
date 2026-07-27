"""Tests for the optional RAG grounding hook.

Covers both states:

1. attune_rag NOT importable — rag_enabled() returns False,
   ground_polish_context() returns None, generation falls
   back to the bare polish prompt.
2. attune_rag importable — rag_enabled() honors the
   ATTUNE_AUTHOR_RAG env var, ground_polish_context()
   returns a context block when hits are found, None on
   fallback.

Uses the sys.modules[name] = None sentinel (stable across
Python 3.10-3.13; the deprecated MetaPathFinder API no
longer fires in 3.12+) to simulate attune_rag absence
without mutating the venv.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.authoring import rag_hook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _block_attune_rag() -> dict[str, object]:
    """Force `import attune_rag` to raise ImportError."""
    saved: dict[str, object] = {}
    for key in list(sys.modules):
        if key == "attune_rag" or key.startswith("attune_rag."):
            saved[key] = sys.modules.pop(key)
    sys.modules["attune_rag"] = None  # type: ignore[assignment]
    return saved


def _unblock_attune_rag(saved: dict[str, object]) -> None:
    sys.modules.pop("attune_rag", None)
    sys.modules.update(saved)


# ---------------------------------------------------------------------------
# rag_enabled()
# ---------------------------------------------------------------------------


def test_rag_enabled_false_when_env_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATTUNE_AUTHOR_RAG", "0")
    assert rag_hook.rag_enabled() is False


def test_rag_enabled_respects_truthy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any value other than '0' means "not disabled"; actual
    enablement still depends on attune_rag being importable."""
    monkeypatch.setenv("ATTUNE_AUTHOR_RAG", "1")
    # With attune_rag importable in dev, this is True. Guard
    # against environments where it isn't by checking the
    # contract rather than a fixed value.
    pytest.importorskip("attune_rag")
    assert rag_hook.rag_enabled() is True


def test_rag_enabled_false_when_attune_rag_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)
    saved = _block_attune_rag()
    try:
        assert rag_hook.rag_enabled() is False
    finally:
        _unblock_attune_rag(saved)


def test_rag_enabled_env_disable_takes_priority_over_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ATTUNE_AUTHOR_RAG=0 wins even when attune_rag is
    perfectly importable. Env is the kill switch."""
    monkeypatch.setenv("ATTUNE_AUTHOR_RAG", "0")
    pytest.importorskip("attune_rag")
    assert rag_hook.rag_enabled() is False


# ---------------------------------------------------------------------------
# ground_polish_context()
# ---------------------------------------------------------------------------


def test_ground_polish_context_returns_none_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ATTUNE_AUTHOR_RAG", "0")
    assert rag_hook.ground_polish_context("security-audit", "concept") is None


def test_ground_polish_context_returns_none_when_attune_rag_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)
    saved = _block_attune_rag()
    try:
        result = rag_hook.ground_polish_context("security-audit", "concept")
        assert result is None
    finally:
        _unblock_attune_rag(saved)


def test_ground_polish_context_returns_none_on_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the retrieval produces the fallback (no-match)
    result, no context is injected."""
    pytest.importorskip("attune_rag")
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)

    fake_result = MagicMock()
    fake_result.fallback_used = True
    fake_result.citation.hits = ()

    with patch("attune_rag.RagPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = fake_result
        mock_pipeline_cls.return_value = mock_pipeline

        result = rag_hook.ground_polish_context("zzzzz", "concept")
    assert result is None


def test_ground_polish_context_returns_markdown_when_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: retrieval returns hits, the hook composes a
    markdown context block with a header and the joined
    template bodies."""
    pytest.importorskip("attune_rag")
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)

    from attune_rag.provenance import CitationRecord, CitedSource

    cited = CitedSource(
        template_path="concepts/tool-security-audit.md",
        category="concepts",
        score=9.0,
    )
    from datetime import datetime, timezone

    citation = CitationRecord(
        query="concept template for security-audit",
        hits=(cited,),
        retrieved_at=datetime.now(timezone.utc),
        retriever_name="KeywordRetriever",
    )
    # attune-rag 0.1.3+ exposes the joined context directly on
    # RagResult. The hook no longer walks the corpus — it just
    # reads `result.context`. We stage a realistic context string
    # here so the assertions below can exercise the real hook
    # output, not a MagicMock.
    fake_result = MagicMock()
    fake_result.fallback_used = False
    fake_result.citation = citation
    fake_result.context = (
        "[P1] source: concepts/tool-security-audit.md\n" "Security audit scans for vulnerabilities."
    )

    with patch("attune_rag.RagPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = fake_result
        mock_pipeline_cls.return_value = mock_pipeline

        result = rag_hook.ground_polish_context("security-audit", "concept")

    assert result is not None
    assert "## Related existing templates" in result
    assert "concepts/tool-security-audit.md" in result
    assert "Security audit scans for vulnerabilities." in result
    # Safety rails: don't let retrieved content be interpreted as directives
    assert "Use them as style" in result
    assert "do NOT copy content" in result


def test_ground_polish_context_returns_none_on_pipeline_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any exception from the pipeline degrades to None so the
    polish pass continues unchanged."""
    pytest.importorskip("attune_rag")
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)

    with patch("attune_rag.RagPipeline") as mock_pipeline_cls:
        mock_pipeline_cls.side_effect = RuntimeError("corpus unavailable")
        result = rag_hook.ground_polish_context("security-audit", "concept")
    assert result is None


def test_ground_polish_context_query_includes_feature_and_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrieval query shape matters — must include both the
    feature name and the template type so hits are same-shape."""
    pytest.importorskip("attune_rag")
    monkeypatch.delenv("ATTUNE_AUTHOR_RAG", raising=False)

    fake_result = MagicMock()
    fake_result.fallback_used = True
    fake_result.citation.hits = ()

    with patch("attune_rag.RagPipeline") as mock_pipeline_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = fake_result
        mock_pipeline_cls.return_value = mock_pipeline

        rag_hook.ground_polish_context("smart-test", "quickstart")

    run_call = mock_pipeline.run.call_args
    passed_query = run_call.args[0] if run_call.args else run_call.kwargs["query"]
    assert "smart-test" in passed_query
    assert "quickstart" in passed_query
