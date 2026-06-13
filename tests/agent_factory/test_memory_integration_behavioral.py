"""Behavioral tests for MemoryAwareAgent graph-integration branches.

The existing suite (test_agent_factory_memory.py) exercises construction and
the no-result happy path with a real MemoryGraph. This file drives the
graph-PRESENT branches deterministically with a mocked graph: similar-finding
formatting, resolution lookup, implicit/explicit finding storage, streaming
with context injection, stats, and the best-effort error handlers.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.agent_factory.base import AgentConfig, AgentRole, BaseAgent
from attune.agent_factory.memory_integration import MemoryAwareAgent

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeAgent(BaseAgent):
    """Minimal wrapped agent that records the context it was invoked with."""

    def __init__(self, config, output="ok", metadata=None):
        super().__init__(config)
        self._output = output
        self._metadata = metadata or {}
        self.last_context = None
        self.added_tools: list = []
        self.cleared = False

    async def invoke(self, input_data, context=None):
        self.last_context = context
        return {"output": self._output, "metadata": dict(self._metadata)}

    async def stream(self, input_data, context=None):
        self.last_context = context
        yield {"output": self._output}

    def add_tool(self, tool):
        self.added_tools.append(tool)

    def get_conversation_history(self):
        return [{"role": "user", "content": "history"}]

    def clear_history(self):
        self.cleared = True

    @property
    def model(self):
        return "fake-model"


def _config():
    return AgentConfig(name="hunter", role=AgentRole.DEBUGGER)


def _node(*, name="bug-x", type_value="bug", node_id="n1", source="wiz", metadata=None):
    """Build a graph node stand-in matching the attributes the code reads."""
    node = MagicMock()
    node.name = name
    node.type = MagicMock()
    node.type.value = type_value
    node.id = node_id
    node.source_wizard = source
    node.metadata = {} if metadata is None else metadata
    return node


def _agent_with_graph(graph, **kwargs):
    """Construct a MemoryAwareAgent whose _graph is the provided mock."""
    with patch("attune.memory.MemoryGraph", return_value=graph):
        return MemoryAwareAgent(_FakeAgent(_config(), **_split_agent_kwargs(kwargs)), **kwargs)


def _agent_without_graph(side_effect=ImportError, **kwargs):
    """Construct a MemoryAwareAgent whose graph init fails (so _graph is None)."""
    with patch("attune.memory.MemoryGraph", side_effect=side_effect):
        return MemoryAwareAgent(_FakeAgent(_config(), **_split_agent_kwargs(kwargs)), **kwargs)


def _split_agent_kwargs(kwargs):
    """Pop wrapped-agent kwargs (output/metadata) out of the wrapper kwargs."""
    agent_kwargs = {}
    for key in ("output", "metadata"):
        if key in kwargs:
            agent_kwargs[key] = kwargs.pop(key)
    return agent_kwargs


# ---------------------------------------------------------------------------
# _init_graph fallbacks
# ---------------------------------------------------------------------------


class TestInitGraph:
    def test_import_error_disables_graph(self):
        """Given attune.memory unavailable, _graph stays None."""
        agent = _agent_without_graph(side_effect=ImportError)
        assert agent.graph is None

    def test_generic_error_disables_graph(self):
        """Given graph load raising, _graph stays None (best-effort)."""
        agent = _agent_without_graph(side_effect=RuntimeError("corrupt"))
        assert agent.graph is None


# ---------------------------------------------------------------------------
# invoke with graph present
# ---------------------------------------------------------------------------


class TestInvokeWithGraph:
    @pytest.mark.asyncio()
    async def test_invoke_injects_similar_and_metadata(self):
        """A graph hit is injected into context and reflected in metadata."""
        graph = MagicMock()
        graph.find_similar.return_value = [(_node(), 0.9)]
        graph.find_related.return_value = []
        agent = _agent_with_graph(graph)

        result = await agent.invoke("find the crash")

        meta = result["metadata"]["memory_graph"]
        assert meta["enabled"] is True
        assert meta["similar_found"] == 1
        assert agent._wrapped.last_context["memory_graph_hits"] == 1
        assert agent._wrapped.last_context["similar_findings"][0]["name"] == "bug-x"

    @pytest.mark.asyncio()
    async def test_invoke_stores_explicit_findings(self):
        """Explicit findings in result metadata are written to the graph."""
        graph = MagicMock()
        graph.find_similar.return_value = []
        graph.add_finding.return_value = "fid-1"
        agent = _agent_with_graph(
            graph,
            metadata={"findings": [{"type": "bug", "name": "n", "description": "d"}]},
        )

        await agent.invoke("scan")

        graph.add_finding.assert_called_once()
        graph._save.assert_called_once()

    @pytest.mark.asyncio()
    async def test_invoke_without_graph_marks_disabled(self):
        """With no graph, metadata reports disabled and zero hits."""
        agent = _agent_without_graph()
        result = await agent.invoke("hi")

        meta = result["metadata"]["memory_graph"]
        assert meta["enabled"] is False
        assert meta["similar_found"] == 0


# ---------------------------------------------------------------------------
# stream with graph present
# ---------------------------------------------------------------------------


class TestStreamWithGraph:
    @pytest.mark.asyncio()
    async def test_stream_injects_similar_findings(self):
        """Streaming injects similar findings into the wrapped agent's context."""
        graph = MagicMock()
        graph.find_similar.return_value = [(_node(), 0.8)]
        graph.find_related.return_value = []
        agent = _agent_with_graph(graph)

        chunks = [c async for c in agent.stream("err")]

        assert len(chunks) == 1
        assert "similar_findings" in agent._wrapped.last_context

    @pytest.mark.asyncio()
    async def test_stream_without_graph(self):
        """Streaming works when no graph is configured."""
        agent = _agent_without_graph()
        chunks = [c async for c in agent.stream("err")]
        assert chunks == [{"output": "ok"}]


# ---------------------------------------------------------------------------
# _get_similar_findings
# ---------------------------------------------------------------------------


class TestGetSimilarFindings:
    def test_no_graph_returns_empty(self):
        """No graph short-circuits to an empty list."""
        agent = _agent_without_graph()
        assert agent._get_similar_findings("x") == []

    def test_dict_input_builds_query_from_task(self):
        """Dict input uses the 'task' key for the query name."""
        graph = MagicMock()
        graph.find_similar.return_value = []
        agent = _agent_with_graph(graph)

        agent._get_similar_findings({"task": "race condition"})

        query = graph.find_similar.call_args.args[0]
        assert query["name"] == "race condition"

    def test_filters_results_below_threshold(self):
        """Results scoring below the threshold are dropped during formatting."""
        graph = MagicMock()
        graph.find_similar.return_value = [(_node(), 0.30)]
        agent = _agent_with_graph(graph, similarity_threshold=0.40)

        assert agent._get_similar_findings("q") == []

    def test_includes_resolutions_when_present(self):
        """A finding with FIXED_BY edges carries a 'resolutions' list."""
        res = MagicMock()
        res.name = "the-fix"
        res.metadata = {"description": "patched it"}
        graph = MagicMock()
        graph.find_similar.return_value = [(_node(), 0.95)]
        graph.find_related.return_value = [res]
        agent = _agent_with_graph(graph)

        findings = agent._get_similar_findings("q")

        assert findings[0]["resolutions"][0]["name"] == "the-fix"
        assert findings[0]["similarity"] == 0.95

    def test_handles_query_error(self):
        """A graph error during query degrades to an empty list."""
        graph = MagicMock()
        graph.find_similar.side_effect = RuntimeError("graph down")
        agent = _agent_with_graph(graph)

        assert agent._get_similar_findings("q") == []


# ---------------------------------------------------------------------------
# _get_resolutions
# ---------------------------------------------------------------------------


class TestGetResolutions:
    def test_no_graph_returns_empty(self):
        agent = _agent_without_graph()
        assert agent._get_resolutions("n1") == []

    def test_success_maps_name_and_description(self):
        res = MagicMock()
        res.name = "fix-a"
        res.metadata = {"description": "did the thing"}
        graph = MagicMock()
        graph.find_related.return_value = [res]
        agent = _agent_with_graph(graph)

        out = agent._get_resolutions("n1")

        assert out == [{"name": "fix-a", "description": "did the thing"}]

    def test_handles_error(self):
        graph = MagicMock()
        graph.find_related.side_effect = RuntimeError("boom")
        agent = _agent_with_graph(graph)

        assert agent._get_resolutions("n1") == []


# ---------------------------------------------------------------------------
# _store_agent_findings
# ---------------------------------------------------------------------------


class TestStoreAgentFindings:
    def test_no_graph_is_noop(self):
        """No graph means storing is a silent no-op."""
        agent = _agent_without_graph()
        agent._store_agent_findings("in", {"output": "found a bug"})  # no raise

    def test_implicit_finding_from_output_patterns_str_input(self):
        """A finding-like output with str input creates and saves an implicit finding."""
        graph = MagicMock()
        graph.add_finding.return_value = "fid"
        agent = _agent_with_graph(graph)

        agent._store_agent_findings("audit task", {"output": "found a critical bug"})

        graph.add_finding.assert_called_once()
        stored = graph.add_finding.call_args.args[1]
        assert stored["name"].startswith("hunter: audit task")
        graph._save.assert_called_once()

    def test_implicit_finding_dict_input_uses_task_name(self):
        """Dict input draws the finding name from the 'task' key."""
        graph = MagicMock()
        graph.add_finding.return_value = "fid"
        agent = _agent_with_graph(graph)

        agent._store_agent_findings({"task": "scan-x"}, {"output": "detected an issue"})

        stored = graph.add_finding.call_args.args[1]
        assert "scan-x" in stored["name"]

    def test_no_findings_when_output_clean(self):
        """A benign output with no finding patterns stores nothing."""
        graph = MagicMock()
        agent = _agent_with_graph(graph)

        agent._store_agent_findings("task", {"output": "all good here"})

        graph.add_finding.assert_not_called()
        graph._save.assert_not_called()

    def test_handles_store_error(self):
        """An error while storing is swallowed (best-effort)."""
        graph = MagicMock()
        graph.add_finding.side_effect = RuntimeError("write failed")
        agent = _agent_with_graph(graph)

        agent._store_agent_findings("t", {"output": "found a bug"})  # no raise


# ---------------------------------------------------------------------------
# Delegation + stats + property
# ---------------------------------------------------------------------------


class TestDelegationAndStats:
    def test_get_conversation_history_delegates(self):
        agent = _agent_without_graph()
        assert agent.get_conversation_history() == [{"role": "user", "content": "history"}]

    def test_clear_history_delegates(self):
        agent = _agent_without_graph()
        agent.clear_history()
        assert agent._wrapped.cleared is True

    def test_graph_property_returns_graph(self):
        graph = MagicMock()
        agent = _agent_with_graph(graph)
        assert agent.graph is graph

    def test_get_graph_stats_no_graph(self):
        agent = _agent_without_graph()
        assert agent.get_graph_stats() == {"enabled": False}

    def test_get_graph_stats_success(self):
        graph = MagicMock()
        graph.nodes = [1, 2, 3]
        graph.edges = [1]
        graph.path = "/tmp/graph.json"
        agent = _agent_with_graph(graph)

        stats = agent.get_graph_stats()

        assert stats == {
            "enabled": True,
            "node_count": 3,
            "edge_count": 1,
            "path": "/tmp/graph.json",
        }

    def test_get_graph_stats_handles_error(self):
        graph = MagicMock()
        type(graph).nodes = property(lambda self: (_ for _ in ()).throw(RuntimeError("x")))
        agent = _agent_with_graph(graph)

        stats = agent.get_graph_stats()

        assert stats["enabled"] is True
        assert "error" in stats

    def test_add_tool_delegates(self):
        agent = _agent_without_graph()
        tool = object()
        agent.add_tool(tool)
        assert agent._wrapped.added_tools == [tool]

    def test_model_property_delegates(self):
        agent = _agent_without_graph()
        assert agent.model == "fake-model"


# ---------------------------------------------------------------------------
# Edge branches: metadata-absent result + finding-type inference
# ---------------------------------------------------------------------------


class TestMetadataAndInference:
    @pytest.mark.asyncio()
    async def test_invoke_creates_metadata_when_absent(self):
        """A wrapped result lacking 'metadata' still gets the memory_graph block."""

        async def _no_metadata(_input, _context=None):
            return {"output": "bare"}

        agent = _agent_without_graph()
        agent._wrapped.invoke = _no_metadata

        result = await agent.invoke("x")

        assert result["metadata"]["memory_graph"]["enabled"] is False

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("we fixed the regression", "fix"),
            ("found a SQL injection vulnerability", "vulnerability"),
            ("uncaught exception in handler", "bug"),
            ("the query is slow / high latency", "performance_issue"),
            ("just a neutral observation", "pattern"),
        ],
    )
    def test_infer_finding_type(self, text, expected):
        """_infer_finding_type maps keywords to the right category (fix wins)."""
        agent = _agent_without_graph()
        assert agent._infer_finding_type(text) == expected
