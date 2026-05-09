"""Unit tests for attune.socratic.adaptive_generator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.socratic.adaptive_generator import AdaptiveAgentGenerator, FeedbackLoop


def _agent(template_id="t1", spec_id="t1"):
    """Build a fake agent with template_id and spec.id."""
    a = MagicMock()
    a.template_id = template_id
    a.spec.id = spec_id
    return a


class TestAdaptiveAgentGenerator:
    def test_use_feedback_false_returns_base_agents(self):
        """Lines 65-66: use_feedback=False → just base agents."""
        gen = AdaptiveAgentGenerator()
        base = [_agent("a"), _agent("b")]
        with patch.object(
            gen.base_generator,
            "generate_agents_for_requirements",
            return_value=base,
        ):
            result = gen.generate_agents_for_requirements({}, use_feedback=False)
        assert result is base

    def test_no_best_agents_returns_base(self):
        """Lines 81-82: feedback returns no best agents → base agents."""
        gen = AdaptiveAgentGenerator()
        base = [_agent("a")]
        with (
            patch.object(
                gen.base_generator,
                "generate_agents_for_requirements",
                return_value=base,
            ),
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[],
            ),
        ):
            result = gen.generate_agents_for_requirements({})
        assert result is base

    def test_reorders_by_feedback_score(self):
        """Lines 85-95: agents reordered by feedback score."""
        gen = AdaptiveAgentGenerator()
        a = _agent("low")
        b = _agent("high")
        # feedback gives b a higher score than a
        with (
            patch.object(
                gen.base_generator,
                "generate_agents_for_requirements",
                return_value=[a, b],
            ),
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("high", 0.9), ("low", 0.3)],
            ),
        ):
            result = gen.generate_agents_for_requirements({})
        # b first (higher score)
        assert result[0] is b
        assert result[1] is a

    def test_adds_high_performing_missing_agent(self):
        """Lines 97-113: agent in feedback but not base, score > 0.7 → add."""
        gen = AdaptiveAgentGenerator()
        base = [_agent("a")]
        new_agent = _agent("new")
        with (
            patch.object(
                gen.base_generator,
                "generate_agents_for_requirements",
                return_value=base,
            ),
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("a", 0.5), ("new", 0.85)],
            ),
            patch.object(
                gen.base_generator,
                "generate_agent_from_template",
                return_value=new_agent,
            ),
        ):
            result = gen.generate_agents_for_requirements(
                {"languages": ["py"], "quality_focus": ["security"]}
            )
        # 'new' was added
        assert any(a is new_agent for a in result)

    def test_high_performing_template_not_found(self):
        """Lines 112-113: generate_agent_from_template raises ValueError → skip."""
        gen = AdaptiveAgentGenerator()
        base = [_agent("a")]
        with (
            patch.object(
                gen.base_generator,
                "generate_agents_for_requirements",
                return_value=base,
            ),
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("a", 0.5), ("missing", 0.9)],
            ),
            patch.object(
                gen.base_generator,
                "generate_agent_from_template",
                side_effect=ValueError("not found"),
            ),
        ):
            # Should not raise — missing agent skipped
            result = gen.generate_agents_for_requirements({})
        # base agent still present, missing not added
        assert len(result) == 1

    def test_low_score_agent_not_added(self):
        """Line 100 branch: feedback agent with score <= 0.7 not added."""
        gen = AdaptiveAgentGenerator()
        base = [_agent("a")]
        with (
            patch.object(
                gen.base_generator,
                "generate_agents_for_requirements",
                return_value=base,
            ),
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("low", 0.5)],
            ),
            patch.object(
                gen.base_generator,
                "generate_agent_from_template",
            ) as mock_gen,
        ):
            result = gen.generate_agents_for_requirements({})
        # generate_agent_from_template never called
        mock_gen.assert_not_called()
        assert len(result) == 1


class TestGetRecommendationExplanation:
    def test_returns_explanation(self):
        gen = AdaptiveAgentGenerator()
        # Mock feedback methods
        perf = MagicMock()
        perf.to_dict.return_value = {"score": 0.8}
        perf.total_uses = 10

        with (
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("t1", 0.8)],
            ),
            patch.object(
                gen.feedback,
                "get_successful_patterns",
                return_value=[],
            ),
            patch.object(
                gen.feedback,
                "get_agent_performance",
                return_value=perf,
            ),
            patch.object(
                gen.feedback,
                "get_all_performance",
                return_value={"t1": perf},
            ),
        ):
            result = gen.get_recommendation_explanation(
                {"domain": "code_review", "languages": ["py"], "quality_focus": ["sec"]}
            )

        assert result["context"]["domain"] == "code_review"
        assert len(result["recommended_agents"]) == 1
        assert result["recommended_agents"][0]["template_id"] == "t1"
        assert result["data_quality"]["total_executions"] == 10
        assert result["data_quality"]["agents_with_data"] == 1

    def test_recommended_agent_with_no_performance(self):
        """Line 158-160: get_agent_performance returns None → performance: None."""
        gen = AdaptiveAgentGenerator()
        with (
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[("t1", 0.8)],
            ),
            patch.object(
                gen.feedback,
                "get_successful_patterns",
                return_value=[],
            ),
            patch.object(
                gen.feedback,
                "get_agent_performance",
                return_value=None,
            ),
            patch.object(
                gen.feedback,
                "get_all_performance",
                return_value={},
            ),
        ):
            result = gen.get_recommendation_explanation({})
        assert result["recommended_agents"][0]["performance"] is None

    def test_truncates_patterns_to_three(self):
        """Line 164: patterns truncated to first 3."""
        gen = AdaptiveAgentGenerator()
        patterns = []
        for i in range(5):
            p = MagicMock()
            p.to_dict.return_value = {"id": i}
            patterns.append(p)

        with (
            patch.object(
                gen.feedback,
                "get_best_agents_for_context",
                return_value=[],
            ),
            patch.object(
                gen.feedback,
                "get_successful_patterns",
                return_value=patterns,
            ),
            patch.object(
                gen.feedback,
                "get_all_performance",
                return_value={},
            ),
        ):
            result = gen.get_recommendation_explanation({})
        assert len(result["successful_patterns"]) == 3


class TestFeedbackLoop:
    def test_init(self, tmp_path):
        """Construction creates collector + adaptive_generator."""
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        assert loop.collector is not None
        assert loop.adaptive_generator is not None

    def test_record_delegates_to_collector(self, tmp_path):
        """record() forwards to collector.record_execution."""
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        bp = MagicMock()
        ev = MagicMock()
        with patch.object(loop.collector, "record_execution") as mock_rec:
            loop.record(bp, ev)
        mock_rec.assert_called_once_with(bp, ev)

    def test_get_recommended_agents(self, tmp_path):
        """Line 238: delegates to adaptive_generator."""
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        with patch.object(
            loop.adaptive_generator,
            "generate_agents_for_requirements",
            return_value=["a"],
        ) as mock_gen:
            result = loop.get_recommended_agents({"x": "y"})
        assert result == ["a"]
        mock_gen.assert_called_once_with({"x": "y"})

    def test_get_insights(self, tmp_path):
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        with patch.object(loop.collector, "get_insights", return_value={"k": "v"}):
            assert loop.get_insights() == {"k": "v"}

    def test_get_agent_stats_with_perf(self, tmp_path):
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        perf = MagicMock()
        perf.to_dict.return_value = {"score": 0.9}
        with patch.object(loop.collector, "get_agent_performance", return_value=perf):
            assert loop.get_agent_stats("t1") == {"score": 0.9}

    def test_get_agent_stats_no_perf(self, tmp_path):
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        with patch.object(loop.collector, "get_agent_performance", return_value=None):
            assert loop.get_agent_stats("t1") is None

    def test_explain_recommendations_delegates(self, tmp_path):
        loop = FeedbackLoop(storage_path=str(tmp_path / "fb"))
        with patch.object(
            loop.adaptive_generator,
            "get_recommendation_explanation",
            return_value={"explanation": "x"},
        ) as mock_exp:
            assert loop.explain_recommendations({}) == {"explanation": "x"}
        mock_exp.assert_called_once_with({})
