"""Unit tests for the rag_knowledge_query MCP tool.

Skipped when the [rag] extra is not installed (attune-rag
is an optional dep of attune-ai; see pyproject.toml). The
MCP tool itself is always registered in the schema and
returns a structured "install [rag] extra" error when
called without attune-rag available — the dispatcher side
of that contract is unit-tested separately.
"""

from __future__ import annotations

import pytest

pytest.importorskip("attune_rag")

import asyncio  # noqa: E402
from collections.abc import Iterable  # noqa: E402

from attune.mcp.server import AttuneMCPServer  # noqa: E402


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


@pytest.fixture(autouse=True)
def _patch_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    from attune_rag import pipeline

    monkeypatch.setattr(pipeline.RagPipeline, "_default_corpus", staticmethod(_make_fake_corpus))


@pytest.fixture
def server() -> AttuneMCPServer:
    return AttuneMCPServer()


def test_tool_registered_in_schemas(server: AttuneMCPServer) -> None:
    names = {t["name"] for t in server.get_tool_list()}
    assert "rag_knowledge_query" in names


def test_tool_schema_shape(server: AttuneMCPServer) -> None:
    tool = next(t for t in server.get_tool_list() if t["name"] == "rag_knowledge_query")
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert schema["required"] == ["query"]


def test_happy_path_returns_hits(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit"}))
    assert result["success"] is True
    assert result["fallback_used"] is False
    assert result["confidence"] > 0
    assert result["hits"]
    assert result["hits"][0]["template_path"] == "concepts/tool-security-audit.md"
    assert "### CONTEXT" in result["augmented_prompt"]


def test_no_match_returns_fallback(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "zzzzz asdfgh qwerty"}))
    assert result["success"] is True
    assert result["fallback_used"] is True
    assert result["hits"] == []
    assert result["confidence"] == 0.0


def test_missing_query_is_rejected(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({}))
    assert result["success"] is False
    assert "query" in result["error"].lower()


def test_empty_query_is_rejected(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "  "}))
    assert result["success"] is False


def test_k_out_of_range_rejected(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit", "k": 0}))
    assert result["success"] is False
    assert "between 1 and 10" in result["error"]

    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit", "k": 11}))
    assert result["success"] is False


def test_k_non_integer_rejected(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit", "k": "bogus"}))
    assert result["success"] is False
    assert "integer" in result["error"]


def test_k_respected_in_hits(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit", "k": 1}))
    assert len(result["hits"]) <= 1


def test_response_includes_corpus_and_retriever_metadata(server: AttuneMCPServer) -> None:
    result = asyncio.run(server._run_rag_knowledge_query({"query": "security audit"}))
    assert result["corpus"] == "fake-corpus"
    assert result["retriever"] == "KeywordRetriever"
