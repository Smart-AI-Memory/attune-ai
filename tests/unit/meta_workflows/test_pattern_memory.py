"""Unit tests for attune.meta_workflows.pattern_memory.

Covers PatternMemoryMixin: store_execution_in_memory, search_executions_by_context,
_search_executions_files, get_smart_recommendations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from attune.meta_workflows.pattern_memory import PatternMemoryMixin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_host(memory=None, executions_dir="/tmp/exec", base_recs=None):
    """Build a minimal PatternMemoryMixin instance with required attributes."""
    host = PatternMemoryMixin()
    host.memory = memory
    host.executions_dir = Path(executions_dir)
    host.get_recommendations = MagicMock(return_value=base_recs or [])
    return host


def _agent_result(role="security", success=True, tier="cheap", cost=0.10):
    return SimpleNamespace(
        agent_id=f"agent-{role}",
        role=role,
        success=success,
        cost=cost,
        duration=1.5,
        tier_used=tier,
        output={},
        error=None,
    )


def _form_responses(**kw):
    defaults = {"q1": "yes", "q2": "no"}
    defaults.update(kw)
    return SimpleNamespace(
        template_id="t1",
        responses=defaults,
        timestamp="2026-01-01T00:00:00Z",
        response_id="resp-1",
    )


def _meta_result(
    success=True,
    error=None,
    run_id="run-1",
    template_id="t1",
    agents=None,
    form_responses=None,
):
    if agents is None:
        agents = [_agent_result()]
    return SimpleNamespace(
        run_id=run_id,
        template_id=template_id,
        timestamp="2026-01-01T00:00:00Z",
        success=success,
        error=error,
        total_cost=0.42,
        total_duration=12.5,
        agents_created=["a1"],
        agent_results=agents,
        form_responses=form_responses or _form_responses(),
    )


# ---------------------------------------------------------------------------
# store_execution_in_memory
# ---------------------------------------------------------------------------


class TestStoreExecutionInMemory:
    def test_no_memory_returns_none(self):
        """Lines 49-51: memory=None → None, log debug."""
        host = _make_host(memory=None)
        assert host.store_execution_in_memory(_meta_result()) is None

    def test_persists_pattern_and_returns_id(self):
        """Lines 53-103: happy path → metadata + content built, persist_pattern called."""
        memory = MagicMock()
        memory.persist_pattern.return_value = {"pattern_id": "p-123"}
        host = _make_host(memory=memory)

        result = _meta_result(
            agents=[
                _agent_result(role="sec", tier="cheap"),
                _agent_result(role="qa", tier="capable", success=False),
            ],
        )
        pattern_id = host.store_execution_in_memory(result)

        assert pattern_id == "p-123"
        # persist_pattern called with the right pattern_type and content
        call_kwargs = memory.persist_pattern.call_args.kwargs
        assert call_kwargs["pattern_type"] == "meta_workflow_execution"
        assert call_kwargs["classification"] == "INTERNAL"
        meta = call_kwargs["metadata"]
        assert meta["run_id"] == "run-1"
        assert meta["agents_succeeded"] == 1
        assert meta["tier_distribution"] == {"cheap": 1, "capable": 1}

    def test_persist_returns_falsy_returns_none(self):
        """Lines 94-105: storage_result is None → return None."""
        memory = MagicMock()
        memory.persist_pattern.return_value = None
        host = _make_host(memory=memory)
        assert host.store_execution_in_memory(_meta_result()) is None

    def test_persist_returns_dict_without_pattern_id(self):
        """storage_result truthy but missing pattern_id → returns None for that key."""
        memory = MagicMock()
        memory.persist_pattern.return_value = {"other_key": "x"}
        host = _make_host(memory=memory)
        assert host.store_execution_in_memory(_meta_result()) is None

    def test_exception_swallowed_returns_none(self):
        """Lines 107-109: persist raises → caught + logged + return None."""
        memory = MagicMock()
        memory.persist_pattern.side_effect = RuntimeError("memory broken")
        host = _make_host(memory=memory)
        assert host.store_execution_in_memory(_meta_result()) is None

    def test_failed_run_status_in_content(self):
        """Lines 72-84: failed status reflected in content string."""
        memory = MagicMock()
        memory.persist_pattern.return_value = {"pattern_id": "p-1"}
        host = _make_host(memory=memory)
        host.store_execution_in_memory(_meta_result(success=False))
        content = memory.persist_pattern.call_args.kwargs["content"]
        assert "FAILED" in content


# ---------------------------------------------------------------------------
# _format_agents_for_content & _format_responses_for_content
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    def test_format_agents(self):
        host = _make_host()
        result = _meta_result(
            agents=[
                _agent_result(role="r1", success=True, tier="cheap", cost=0.10),
                _agent_result(role="r2", success=False, tier="capable", cost=0.50),
            ]
        )
        text = host._format_agents_for_content(result)
        assert "ok r1" in text
        assert "fail r2" in text
        assert "$0.10" in text
        assert "$0.50" in text

    def test_format_responses(self):
        host = _make_host()
        text = host._format_responses_for_content({"a": 1, "b": "two"})
        assert "- a: 1" in text
        assert "- b: two" in text


# ---------------------------------------------------------------------------
# search_executions_by_context
# ---------------------------------------------------------------------------


class TestSearchExecutionsByContext:
    def test_no_memory_falls_back_to_files(self):
        """Lines 151-153: memory None → file-based fallback."""
        host = _make_host(memory=None)
        with patch.object(
            host, "_search_executions_files", return_value=["fake-result"]
        ) as mock_fb:
            result = host.search_executions_by_context("query")
        assert result == ["fake-result"]
        mock_fb.assert_called_once_with("query", None, 10)

    def test_returns_results_for_matching_run_ids(self):
        """Lines 155-178: patterns with run_id → load + return."""
        memory = MagicMock()
        memory.search_patterns.return_value = [
            {"metadata": {"run_id": "r1", "template_id": "t1"}},
            {"metadata": {"run_id": "r2", "template_id": "t1"}},
        ]
        host = _make_host(memory=memory)

        loaded = {"r1": _meta_result(run_id="r1"), "r2": _meta_result(run_id="r2")}
        with patch(
            "attune.meta_workflows.pattern_memory.load_execution_result",
            side_effect=lambda rid, storage_dir: loaded[rid],
        ):
            result = host.search_executions_by_context("query")
        assert len(result) == 2

    def test_skips_patterns_without_run_id(self):
        """Lines 167: patterns without run_id are skipped."""
        memory = MagicMock()
        memory.search_patterns.return_value = [
            {"metadata": {}},  # no run_id
            {"metadata": {"run_id": "r1", "template_id": "t1"}},
        ]
        host = _make_host(memory=memory)
        with patch(
            "attune.meta_workflows.pattern_memory.load_execution_result",
            return_value=_meta_result(run_id="r1"),
        ):
            result = host.search_executions_by_context("q")
        assert len(result) == 1

    def test_filters_by_template_id(self):
        """Lines 168-169: template_id mismatch → skip."""
        memory = MagicMock()
        memory.search_patterns.return_value = [
            {"metadata": {"run_id": "r1", "template_id": "other"}},
            {"metadata": {"run_id": "r2", "template_id": "t1"}},
        ]
        host = _make_host(memory=memory)
        with patch(
            "attune.meta_workflows.pattern_memory.load_execution_result",
            return_value=_meta_result(run_id="r2"),
        ):
            result = host.search_executions_by_context("q", template_id="t1")
        assert len(result) == 1

    def test_file_not_found_swallowed(self):
        """Lines 174-176: FileNotFoundError → logged, continue."""
        memory = MagicMock()
        memory.search_patterns.return_value = [
            {"metadata": {"run_id": "r1", "template_id": "t1"}},
            {"metadata": {"run_id": "r2", "template_id": "t1"}},
        ]
        host = _make_host(memory=memory)

        def fake_load(rid, storage_dir):
            if rid == "r1":
                raise FileNotFoundError("missing")
            return _meta_result(run_id=rid)

        with patch(
            "attune.meta_workflows.pattern_memory.load_execution_result",
            side_effect=fake_load,
        ):
            result = host.search_executions_by_context("q")
        assert len(result) == 1
        assert result[0].run_id == "r2"

    def test_search_exception_falls_back_to_files(self):
        """Lines 180-182: search_patterns raises → fallback."""
        memory = MagicMock()
        memory.search_patterns.side_effect = RuntimeError("memory failed")
        host = _make_host(memory=memory)
        with patch.object(host, "_search_executions_files", return_value=["fb"]):
            result = host.search_executions_by_context("q")
        assert result == ["fb"]


# ---------------------------------------------------------------------------
# _search_executions_files
# ---------------------------------------------------------------------------


class TestSearchExecutionsFiles:
    def test_returns_query_matching_results(self):
        """Lines 192-209: file-based query: filter by content match + template_id."""
        host = _make_host()

        results_by_id = {
            "r1": MagicMock(template_id="t1", to_json=lambda: '{"text": "FOO bar"}'),
            "r2": MagicMock(template_id="t1", to_json=lambda: '{"text": "baz"}'),
            "r3": MagicMock(template_id="other", to_json=lambda: '{"text": "FOO"}'),
        }

        with (
            patch(
                "attune.meta_workflows.pattern_memory.list_execution_results",
                return_value=["r1", "r2", "r3"],
            ),
            patch(
                "attune.meta_workflows.pattern_memory.load_execution_result",
                side_effect=lambda rid, storage_dir: results_by_id[rid],
            ),
        ):
            result = host._search_executions_files("foo", "t1", 10)
        # r1 matches (foo + t1); r3 has 'FOO' but wrong template; r2 doesn't match
        assert len(result) == 1
        assert result[0] is results_by_id["r1"]

    def test_load_exception_swallowed(self):
        """Lines 205-207: load_execution_result raises → logged, continue."""
        host = _make_host()
        good = MagicMock(template_id="t1", to_json=lambda: '{"x": "match"}')

        def fake_load(rid, storage_dir):
            if rid == "bad":
                raise RuntimeError("corrupt")
            return good

        with (
            patch(
                "attune.meta_workflows.pattern_memory.list_execution_results",
                return_value=["bad", "ok"],
            ),
            patch(
                "attune.meta_workflows.pattern_memory.load_execution_result",
                side_effect=fake_load,
            ),
        ):
            result = host._search_executions_files("match", None, 10)
        assert len(result) == 1

    def test_no_template_filter_when_none(self):
        """Lines 198-199: template_id=None → no template filtering."""
        host = _make_host()
        a = MagicMock(template_id="anything", to_json=lambda: '{"k": "match"}')
        with (
            patch(
                "attune.meta_workflows.pattern_memory.list_execution_results",
                return_value=["r1"],
            ),
            patch(
                "attune.meta_workflows.pattern_memory.load_execution_result",
                return_value=a,
            ),
        ):
            result = host._search_executions_files("match", None, 10)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_smart_recommendations
# ---------------------------------------------------------------------------


class TestGetSmartRecommendations:
    def test_no_memory_returns_base_only(self):
        """Lines 233-234: memory None → just base recs."""
        host = _make_host(memory=None, base_recs=["base1"])
        assert host.get_smart_recommendations("t1") == ["base1"]

    def test_no_form_response_returns_base_only(self):
        """Lines 233-234: form_response None → just base recs."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base1"])
        assert host.get_smart_recommendations("t1", form_response=None) == ["base1"]

    def test_with_high_success_rate_prepends_insight(self):
        """Lines 250-260: similar executions with success rate >= 80% → insight prepended."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base"])

        # 4 of 5 succeed → 80%
        similar = [
            _meta_result(success=True, agents=[_agent_result(tier="cheap")]),
            _meta_result(success=True, agents=[_agent_result(tier="cheap")]),
            _meta_result(success=True, agents=[_agent_result(tier="capable")]),
            _meta_result(success=True, agents=[_agent_result(tier="cheap")]),
            _meta_result(success=False, agents=[_agent_result(tier="cheap")]),
        ]
        with patch.object(host, "search_executions_by_context", return_value=similar):
            result = host.get_smart_recommendations("t1", form_response=_form_responses())

        # First entry should be the insight string
        assert "5 similar workflows" in result[0]
        assert "80% success rate" in result[0]
        # Tier recommendation appended (cheap is most common)
        assert any("'cheap' tier" in r for r in result)

    def test_low_success_rate_skips_prepend(self):
        """Lines 255-260: success rate < 80% → no prepend."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base"])

        similar = [
            _meta_result(success=False, agents=[_agent_result(tier="cheap")]),
            _meta_result(success=False, agents=[_agent_result(tier="capable")]),
            _meta_result(success=True, agents=[_agent_result(tier="capable")]),
        ]
        with patch.object(host, "search_executions_by_context", return_value=similar):
            result = host.get_smart_recommendations("t1", form_response=_form_responses())

        # No "similar workflows" insight prepended
        assert all("similar workflows found" not in r for r in result)
        # But tier_usage non-empty → tier rec still appended
        assert any("tier" in r.lower() for r in result)

    def test_empty_similar_skips_block(self):
        """Lines 250: no similar executions → no extra recs."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base"])
        with patch.object(host, "search_executions_by_context", return_value=[]):
            result = host.get_smart_recommendations("t1", form_response=_form_responses())
        assert result == ["base"]

    def test_tier_usage_empty_skips_tier_rec(self):
        """Lines 267-269: empty tier_usage → no tier recommendation."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base"])

        # Similar executions but with no agent_results
        similar = [_meta_result(success=True, agents=[])]
        with patch.object(host, "search_executions_by_context", return_value=similar):
            result = host.get_smart_recommendations("t1", form_response=_form_responses())
        # tier_usage empty → no tier rec appended
        assert all("tier" not in r.lower() for r in result)

    def test_query_includes_form_keys(self):
        """Lines 238-242: form_response keys appear in query."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=[])
        captured = {}

        def fake_search(query, template_id, limit):
            captured["query"] = query
            return []

        with patch.object(host, "search_executions_by_context", side_effect=fake_search):
            host.get_smart_recommendations(
                "tmpl",
                form_response=_form_responses(level="high"),
            )
        assert "tmpl" in captured["query"]
        # First 3 form keys appended
        assert "q1=yes" in captured["query"]

    def test_exception_during_enhancement_returns_base(self):
        """Lines 271-272: exception during memory enhancement → base recs only."""
        memory = MagicMock()
        host = _make_host(memory=memory, base_recs=["base"])
        with patch.object(
            host,
            "search_executions_by_context",
            side_effect=RuntimeError("boom"),
        ):
            result = host.get_smart_recommendations("t1", form_response=_form_responses())
        assert result == ["base"]
