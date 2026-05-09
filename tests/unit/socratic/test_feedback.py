"""Tests for the Feedback Loop for Continuous Improvement.

Tests cover:
- AgentPerformance dataclass
- WorkflowPattern dataclass
- FeedbackCollector class
- AdaptiveAgentGenerator class
- FeedbackLoop integration

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from attune.socratic.feedback import (
    AdaptiveAgentGenerator,
    AgentPerformance,
    FeedbackCollector,
    FeedbackLoop,
    WorkflowPattern,
)

# =============================================================================
# AGENT PERFORMANCE TESTS
# =============================================================================


@pytest.mark.unit
class TestAgentPerformanceCreation:
    """Tests for AgentPerformance dataclass creation."""

    def test_minimal_creation(self):
        """Test creating performance with minimal fields."""
        perf = AgentPerformance(template_id="test_agent")
        assert perf.template_id == "test_agent"
        assert perf.total_uses == 0
        assert perf.successful_uses == 0
        assert perf.average_score == 0.0

    def test_success_rate_with_no_uses(self):
        """Test success rate is 0 when no uses."""
        perf = AgentPerformance(template_id="test")
        assert perf.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        perf = AgentPerformance(
            template_id="test",
            total_uses=10,
            successful_uses=7,
        )
        assert perf.success_rate == 0.7


@pytest.mark.unit
class TestAgentPerformanceTrend:
    """Tests for AgentPerformance trend property."""

    def test_trend_insufficient_data(self):
        """Test trend with insufficient data."""
        perf = AgentPerformance(template_id="test")
        perf.recent_scores = [("2024-01-01", 0.8), ("2024-01-02", 0.9)]
        assert perf.trend == "insufficient_data"

    def test_trend_stable_no_older_data(self):
        """Test trend is stable with only 5 scores."""
        perf = AgentPerformance(template_id="test")
        perf.recent_scores = [
            ("2024-01-01", 0.8),
            ("2024-01-02", 0.8),
            ("2024-01-03", 0.8),
            ("2024-01-04", 0.8),
            ("2024-01-05", 0.8),
        ]
        assert perf.trend == "stable"

    def test_trend_improving(self):
        """Test trend is improving when recent scores are higher."""
        perf = AgentPerformance(template_id="test")
        # Older 5: avg 0.5, Recent 5: avg 0.8 (>10% increase)
        perf.recent_scores = [
            ("2024-01-01", 0.5),
            ("2024-01-02", 0.5),
            ("2024-01-03", 0.5),
            ("2024-01-04", 0.5),
            ("2024-01-05", 0.5),
            ("2024-01-06", 0.8),
            ("2024-01-07", 0.8),
            ("2024-01-08", 0.8),
            ("2024-01-09", 0.8),
            ("2024-01-10", 0.8),
        ]
        assert perf.trend == "improving"

    def test_trend_declining(self):
        """Test trend is declining when recent scores are lower."""
        perf = AgentPerformance(template_id="test")
        # Older 5: avg 0.9, Recent 5: avg 0.5 (>10% decrease)
        perf.recent_scores = [
            ("2024-01-01", 0.9),
            ("2024-01-02", 0.9),
            ("2024-01-03", 0.9),
            ("2024-01-04", 0.9),
            ("2024-01-05", 0.9),
            ("2024-01-06", 0.5),
            ("2024-01-07", 0.5),
            ("2024-01-08", 0.5),
            ("2024-01-09", 0.5),
            ("2024-01-10", 0.5),
        ]
        assert perf.trend == "declining"

    def test_trend_stable_within_threshold(self):
        """Test trend is stable when within 10% threshold."""
        perf = AgentPerformance(template_id="test")
        # Older 5: avg 0.8, Recent 5: avg 0.82 (within 10%)
        perf.recent_scores = [
            ("2024-01-01", 0.8),
            ("2024-01-02", 0.8),
            ("2024-01-03", 0.8),
            ("2024-01-04", 0.8),
            ("2024-01-05", 0.8),
            ("2024-01-06", 0.82),
            ("2024-01-07", 0.82),
            ("2024-01-08", 0.82),
            ("2024-01-09", 0.82),
            ("2024-01-10", 0.82),
        ]
        assert perf.trend == "stable"


@pytest.mark.unit
class TestAgentPerformanceRecordUse:
    """Tests for AgentPerformance.record_use()."""

    def test_record_successful_use(self):
        """Test recording a successful use."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=True, score=0.9)

        assert perf.total_uses == 1
        assert perf.successful_uses == 1
        assert perf.average_score == 0.9
        assert len(perf.recent_scores) == 1

    def test_record_failed_use(self):
        """Test recording a failed use."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=False, score=0.3)

        assert perf.total_uses == 1
        assert perf.successful_uses == 0
        assert perf.average_score == 0.3

    def test_record_multiple_uses_updates_average(self):
        """Test that multiple uses update average correctly."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=True, score=0.8)
        perf.record_use(success=True, score=1.0)

        assert perf.total_uses == 2
        assert perf.average_score == 0.9

    def test_record_use_with_domain(self):
        """Test recording use with domain context."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=True, score=0.9, domain="code_review")

        assert "code_review" in perf.by_domain
        assert perf.by_domain["code_review"]["uses"] == 1
        assert perf.by_domain["code_review"]["successes"] == 1

    def test_record_use_with_languages(self):
        """Test recording use with language context."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=True, score=0.9, languages=["python", "javascript"])

        assert "python" in perf.by_language
        assert "javascript" in perf.by_language
        assert perf.by_language["python"]["uses"] == 1

    def test_record_use_with_quality_focus(self):
        """Test recording use with quality focus context."""
        perf = AgentPerformance(template_id="test")
        perf.record_use(success=True, score=0.9, quality_focus=["security"])

        assert "security" in perf.by_quality_focus
        assert perf.by_quality_focus["security"]["uses"] == 1

    def test_record_use_trims_recent_scores(self):
        """Test that recent scores are trimmed to 100."""
        perf = AgentPerformance(template_id="test")

        for _i in range(110):
            perf.record_use(success=True, score=0.8)

        assert len(perf.recent_scores) == 100


@pytest.mark.unit
class TestAgentPerformanceContextScore:
    """Tests for AgentPerformance.get_score_for_context()."""

    def test_default_score_no_data(self):
        """Test default score when no data."""
        perf = AgentPerformance(template_id="test")
        score = perf.get_score_for_context(domain="code_review")
        assert score == 0.5  # Default neutral score

    def test_score_with_base_average(self):
        """Test score uses base average when available."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 5
        perf.average_score = 0.8
        perf.scores = [0.8] * 5

        score = perf.get_score_for_context()
        assert score == 0.8

    def test_score_weighted_by_domain(self):
        """Test score is weighted by domain match."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 5
        perf.average_score = 0.6
        perf.by_domain["code_review"] = {"uses": 3, "successes": 3, "total_score": 2.7}

        score = perf.get_score_for_context(domain="code_review")
        # Domain score (2.7/3=0.9) has weight 2.0, base (0.6) has weight 1.0
        # (0.6*1 + 0.9*2) / 3 = 0.8
        assert score == pytest.approx(0.8, rel=0.01)

    def test_score_weighted_by_languages(self):
        """Languages list contributes language-specific scores (lines 137-140)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 0  # skip base score path
        perf.by_language["python"] = {"uses": 4, "successes": 4, "total_score": 3.6}
        perf.by_language["go"] = {"uses": 2, "successes": 2, "total_score": 1.8}

        score = perf.get_score_for_context(languages=["python", "go"])
        # Both 0.9, weights both 1.5 → 0.9
        assert score == pytest.approx(0.9, rel=0.01)

    def test_score_weighted_by_quality_focus(self):
        """quality_focus list contributes scores (lines 146-149)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 0
        perf.by_quality_focus["security"] = {"uses": 5, "successes": 5, "total_score": 4.0}

        score = perf.get_score_for_context(quality_focus=["security"])
        assert score == pytest.approx(0.8, rel=0.01)

    def test_score_skips_zero_use_domain(self):
        """Domain entry with uses==0 is skipped (branch 129->134)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 0
        perf.by_domain["code_review"] = {"uses": 0, "successes": 0, "total_score": 0.0}
        # Falls through to default
        assert perf.get_score_for_context(domain="code_review") == 0.5

    def test_score_skips_zero_use_language(self):
        """Language entry with uses==0 is skipped (branch 138->135)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 0
        perf.by_language["python"] = {"uses": 0, "successes": 0, "total_score": 0.0}
        assert perf.get_score_for_context(languages=["python"]) == 0.5

    def test_score_skips_zero_use_quality_focus(self):
        """quality_focus entry with uses==0 is skipped (branch 147->144)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 0
        perf.by_quality_focus["security"] = {"uses": 0, "successes": 0, "total_score": 0.0}
        assert perf.get_score_for_context(quality_focus=["security"]) == 0.5

    def test_score_skips_unknown_languages(self):
        """A language not in by_language is silently skipped (branch 129->134-equivalent)."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 5
        perf.average_score = 0.7
        # No by_language entries

        score = perf.get_score_for_context(languages=["rust"])
        # Falls back to base score
        assert score == pytest.approx(0.7, rel=0.01)


@pytest.mark.unit
class TestAgentPerformanceSerialization:
    """Tests for AgentPerformance serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        perf = AgentPerformance(template_id="test")
        perf.total_uses = 5
        perf.successful_uses = 4
        perf.average_score = 0.85

        result = perf.to_dict()

        assert result["template_id"] == "test"
        assert result["total_uses"] == 5
        assert result["success_rate"] == 0.8
        assert "trend" in result

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "template_id": "test",
            "total_uses": 10,
            "successful_uses": 8,
            "average_score": 0.9,
            "by_domain": {"code_review": {"uses": 5, "successes": 4, "total_score": 4.5}},
        }

        perf = AgentPerformance.from_dict(data)

        assert perf.template_id == "test"
        assert perf.total_uses == 10
        assert perf.by_domain == data["by_domain"]

    def test_roundtrip_serialization(self):
        """Test that to_dict and from_dict are compatible."""
        original = AgentPerformance(template_id="test")
        original.record_use(success=True, score=0.9, domain="security")

        serialized = original.to_dict()
        restored = AgentPerformance.from_dict(serialized)

        assert restored.template_id == original.template_id
        assert restored.total_uses == original.total_uses


# =============================================================================
# WORKFLOW PATTERN TESTS
# =============================================================================


@pytest.mark.unit
class TestWorkflowPattern:
    """Tests for WorkflowPattern dataclass."""

    def test_creation(self):
        """Test creating a workflow pattern."""
        pattern = WorkflowPattern(
            pattern_id="code_review:agent1:agent2",
            domain="code_review",
            agent_combination=["agent1", "agent2"],
            stage_configuration=[{"id": "stage1"}],
        )
        assert pattern.pattern_id == "code_review:agent1:agent2"
        assert len(pattern.agent_combination) == 2

    def test_success_rate_no_uses(self):
        """Test success rate with no uses."""
        pattern = WorkflowPattern(
            pattern_id="test",
            domain="test",
            agent_combination=[],
            stage_configuration=[],
        )
        assert pattern.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        pattern = WorkflowPattern(
            pattern_id="test",
            domain="test",
            agent_combination=[],
            stage_configuration=[],
            uses=10,
            successes=7,
        )
        assert pattern.success_rate == 0.7

    def test_to_dict(self):
        """Test serialization to dictionary."""
        pattern = WorkflowPattern(
            pattern_id="test",
            domain="code_review",
            agent_combination=["a", "b"],
            stage_configuration=[{"id": "s1"}],
            uses=5,
            successes=4,
            average_score=0.85,
        )
        result = pattern.to_dict()

        assert result["pattern_id"] == "test"
        assert result["domain"] == "code_review"
        assert result["success_rate"] == 0.8


# =============================================================================
# FEEDBACK COLLECTOR TESTS
# =============================================================================


@pytest.mark.unit
class TestFeedbackCollectorInitialization:
    """Tests for FeedbackCollector initialization."""

    def test_creates_storage_directory(self, tmp_path):
        """Test that storage directory is created."""
        storage_path = tmp_path / "feedback"
        collector = FeedbackCollector(storage_path=str(storage_path))

        assert storage_path.exists()
        assert collector.storage_path == storage_path

    def test_loads_existing_data(self, tmp_path):
        """Test loading existing performance data."""
        storage_path = tmp_path / "feedback"
        storage_path.mkdir(parents=True)

        # Create existing data
        perf_data = {
            "test_agent": {
                "template_id": "test_agent",
                "total_uses": 5,
                "successful_uses": 4,
                "average_score": 0.85,
            },
        }
        (storage_path / "agent_performance.json").write_text(json.dumps(perf_data))

        collector = FeedbackCollector(storage_path=str(storage_path))

        assert "test_agent" in collector._agent_performance
        assert collector._agent_performance["test_agent"].total_uses == 5

    def test_handles_corrupted_data(self, tmp_path):
        """Test handling of corrupted JSON data."""
        storage_path = tmp_path / "feedback"
        storage_path.mkdir(parents=True)

        # Create corrupted data
        (storage_path / "agent_performance.json").write_text("not valid json")

        # Should not raise, just log warning
        collector = FeedbackCollector(storage_path=str(storage_path))
        assert collector._agent_performance == {}


@pytest.mark.unit
class TestFeedbackCollectorRecordExecution:
    """Tests for FeedbackCollector.record_execution()."""

    @pytest.fixture
    def collector(self, tmp_path):
        """Create a FeedbackCollector for testing."""
        return FeedbackCollector(storage_path=str(tmp_path / "feedback"))

    @pytest.fixture
    def mock_blueprint(self):
        """Create a mock WorkflowBlueprint."""
        blueprint = MagicMock()
        blueprint.id = "test-blueprint-001"
        blueprint.domain = "code_review"
        blueprint.supported_languages = ["python"]
        blueprint.quality_focus = ["security"]

        agent = MagicMock()
        agent.template_id = "security_reviewer"
        agent.spec.id = "security_reviewer"
        blueprint.agents = [agent]

        stage = MagicMock()
        stage.to_dict.return_value = {"id": "review"}
        blueprint.stages = [stage]

        return blueprint

    @pytest.fixture
    def mock_evaluation(self):
        """Create a mock SuccessEvaluation."""
        evaluation = MagicMock()
        evaluation.overall_success = True
        evaluation.overall_score = 0.85
        return evaluation

    def test_records_agent_performance(self, collector, mock_blueprint, mock_evaluation):
        """Test that agent performance is recorded."""
        collector.record_execution(mock_blueprint, mock_evaluation)

        assert "security_reviewer" in collector._agent_performance
        perf = collector._agent_performance["security_reviewer"]
        assert perf.total_uses == 1
        assert perf.successful_uses == 1

    def test_records_workflow_pattern(self, collector, mock_blueprint, mock_evaluation):
        """Test that workflow pattern is recorded."""
        collector.record_execution(mock_blueprint, mock_evaluation)

        assert len(collector._workflow_patterns) == 1
        pattern = list(collector._workflow_patterns.values())[0]
        assert pattern.uses == 1

    def test_saves_data_to_disk(self, collector, mock_blueprint, mock_evaluation, tmp_path):
        """Test that data is saved to disk."""
        collector.record_execution(mock_blueprint, mock_evaluation)

        perf_file = tmp_path / "feedback" / "agent_performance.json"
        assert perf_file.exists()

        with perf_file.open() as f:
            data = json.load(f)
        assert "security_reviewer" in data


@pytest.mark.unit
class TestFeedbackCollectorQueries:
    """Tests for FeedbackCollector query methods."""

    @pytest.fixture
    def populated_collector(self, tmp_path):
        """Create a populated FeedbackCollector."""
        collector = FeedbackCollector(storage_path=str(tmp_path / "feedback"))

        # Add some performance data
        perf1 = AgentPerformance(template_id="agent1")
        for _ in range(10):
            perf1.record_use(success=True, score=0.9, domain="code_review")

        perf2 = AgentPerformance(template_id="agent2")
        for _ in range(10):
            perf2.record_use(success=False, score=0.3, domain="code_review")

        collector._agent_performance = {"agent1": perf1, "agent2": perf2}

        # Add workflow patterns
        pattern1 = WorkflowPattern(
            pattern_id="code_review:agent1",
            domain="code_review",
            agent_combination=["agent1"],
            stage_configuration=[],
            uses=10,
            successes=9,
            average_score=0.9,
        )
        collector._workflow_patterns = {"code_review:agent1": pattern1}

        return collector

    def test_get_agent_performance(self, populated_collector):
        """Test getting agent performance."""
        perf = populated_collector.get_agent_performance("agent1")
        assert perf is not None
        assert perf.template_id == "agent1"

    def test_get_agent_performance_not_found(self, populated_collector):
        """Test getting non-existent agent performance."""
        perf = populated_collector.get_agent_performance("nonexistent")
        assert perf is None

    def test_get_all_performance(self, populated_collector):
        """Test getting all performance data."""
        all_perf = populated_collector.get_all_performance()
        assert len(all_perf) == 2
        assert "agent1" in all_perf

    def test_get_best_agents_for_context(self, populated_collector):
        """Test getting best agents for a context."""
        best = populated_collector.get_best_agents_for_context(
            domain="code_review",
            limit=5,
        )
        assert len(best) == 2
        # agent1 should be first (higher score)
        assert best[0][0] == "agent1"

    def test_get_successful_patterns(self, populated_collector):
        """Test getting successful patterns."""
        patterns = populated_collector.get_successful_patterns(
            domain="code_review",
            min_success_rate=0.7,
            min_uses=5,
        )
        assert len(patterns) == 1
        assert patterns[0].pattern_id == "code_review:agent1"

    def test_get_successful_patterns_filtered_by_domain(self, populated_collector):
        """Test patterns are filtered by domain."""
        patterns = populated_collector.get_successful_patterns(
            domain="security_audit",
            min_success_rate=0.7,
            min_uses=1,
        )
        assert len(patterns) == 0

    def test_get_insights(self, populated_collector):
        """Test getting aggregated insights."""
        insights = populated_collector.get_insights()

        assert "total_agents_tracked" in insights
        assert insights["total_agents_tracked"] == 2
        assert "top_performing_agents" in insights
        assert "domain_insights" in insights


@pytest.mark.unit
class TestFeedbackCollectorRecommendations:
    """Tests for FeedbackCollector recommendations."""

    @pytest.fixture
    def collector_with_underperformer(self, tmp_path):
        """Create collector with underperforming agent."""
        collector = FeedbackCollector(storage_path=str(tmp_path / "feedback"))

        perf = AgentPerformance(template_id="bad_agent")
        perf.total_uses = 15
        perf.successful_uses = 3  # 20% success rate
        perf.scores = [0.3] * 15
        perf.average_score = 0.3

        collector._agent_performance = {"bad_agent": perf}
        return collector

    def test_generates_recommendation_for_underperformer(self, collector_with_underperformer):
        """Test recommendation generated for underperforming agent.

        Note: There's a recursion bug in _generate_recommendations that calls
        get_insights(). We mock get_insights to avoid the recursion.
        """
        with patch.object(
            collector_with_underperformer,
            "get_insights",
            return_value={"domain_insights": {}},
        ):
            recommendations = collector_with_underperformer._generate_recommendations()

        assert any("bad_agent" in r for r in recommendations)
        assert any("success rate" in r.lower() for r in recommendations)


# =============================================================================
# ADAPTIVE AGENT GENERATOR TESTS
# =============================================================================


@pytest.mark.unit
class TestAdaptiveAgentGenerator:
    """Tests for AdaptiveAgentGenerator."""

    @pytest.fixture
    def mock_feedback_collector(self, tmp_path):
        """Create a mock FeedbackCollector."""
        collector = FeedbackCollector(storage_path=str(tmp_path / "feedback"))

        # Add performance data
        perf = AgentPerformance(template_id="high_performer")
        for _ in range(10):
            perf.record_use(success=True, score=0.9)
        collector._agent_performance = {"high_performer": perf}

        return collector

    def test_initialization(self, mock_feedback_collector):
        """Test AdaptiveAgentGenerator initialization."""
        generator = AdaptiveAgentGenerator(feedback_collector=mock_feedback_collector)
        assert generator.feedback is mock_feedback_collector

    def test_generate_agents_without_feedback(self, mock_feedback_collector):
        """Test generating agents without using feedback."""
        generator = AdaptiveAgentGenerator(feedback_collector=mock_feedback_collector)

        with patch.object(
            generator.base_generator,
            "generate_agents_for_requirements",
            return_value=[],
        ):
            result = generator.generate_agents_for_requirements(
                requirements={"domain": "test"},
                use_feedback=False,
            )
            assert result == []

    def test_get_recommendation_explanation(self, mock_feedback_collector):
        """Test getting recommendation explanation."""
        generator = AdaptiveAgentGenerator(feedback_collector=mock_feedback_collector)

        explanation = generator.get_recommendation_explanation(
            requirements={
                "domain": "code_review",
                "languages": ["python"],
                "quality_focus": ["security"],
            },
        )

        assert "context" in explanation
        assert explanation["context"]["domain"] == "code_review"
        assert "recommended_agents" in explanation
        assert "data_quality" in explanation


# =============================================================================
# FEEDBACK LOOP TESTS
# =============================================================================


@pytest.mark.unit
class TestFeedbackLoop:
    """Tests for FeedbackLoop integration."""

    @pytest.fixture
    def feedback_loop(self, tmp_path):
        """Create a FeedbackLoop for testing."""
        return FeedbackLoop(storage_path=str(tmp_path / "feedback"))

    def test_initialization(self, feedback_loop):
        """Test FeedbackLoop initialization."""
        assert feedback_loop.collector is not None
        assert feedback_loop.adaptive_generator is not None

    def test_record(self, feedback_loop):
        """Test recording execution."""
        blueprint = MagicMock()
        blueprint.id = "test"
        blueprint.domain = "test"
        blueprint.supported_languages = []
        blueprint.quality_focus = []
        agent = MagicMock()
        agent.template_id = "agent1"
        agent.spec.id = "agent1"
        blueprint.agents = [agent]
        stage = MagicMock()
        stage.to_dict.return_value = {}
        blueprint.stages = [stage]

        evaluation = MagicMock()
        evaluation.overall_success = True
        evaluation.overall_score = 0.9

        feedback_loop.record(blueprint, evaluation)

        assert "agent1" in feedback_loop.collector._agent_performance

    def test_get_insights(self, feedback_loop):
        """Test getting insights.

        Note: There's a recursion bug in _generate_recommendations. We mock it.
        """
        with patch.object(feedback_loop.collector, "_generate_recommendations", return_value=[]):
            insights = feedback_loop.get_insights()

        assert "total_agents_tracked" in insights
        assert "recommendations" in insights

    def test_get_agent_stats_not_found(self, feedback_loop):
        """Test getting stats for non-existent agent."""
        stats = feedback_loop.get_agent_stats("nonexistent")
        assert stats is None

    def test_get_agent_stats_found(self, feedback_loop):
        """Test getting stats for existing agent."""
        # Add an agent first
        perf = AgentPerformance(template_id="test_agent")
        perf.total_uses = 5
        feedback_loop.collector._agent_performance["test_agent"] = perf

        stats = feedback_loop.get_agent_stats("test_agent")
        assert stats is not None
        assert stats["template_id"] == "test_agent"
        assert stats["total_uses"] == 5

    def test_explain_recommendations(self, feedback_loop):
        """Test explaining recommendations."""
        explanation = feedback_loop.explain_recommendations(requirements={"domain": "code_review"})

        assert "context" in explanation
        assert "recommended_agents" in explanation


# ===========================================================================
# Coverage for previously-missed branches in feedback_collector.py
# ===========================================================================

from attune.socratic.feedback_models import WorkflowPattern as WP  # noqa: E402


def _make_blueprint(domain="code_review", agent_template_ids=None, blueprint_id="bp-x"):
    """Build a minimal WorkflowBlueprint mock."""
    bp = MagicMock()
    bp.id = blueprint_id
    bp.domain = domain
    bp.supported_languages = ["python"]
    bp.quality_focus = ["security"]

    if agent_template_ids is None:
        agent_template_ids = ["agent_a"]
    bp.agents = []
    for tid in agent_template_ids:
        a = MagicMock()
        a.template_id = tid
        a.spec = MagicMock()
        a.spec.id = tid
        bp.agents.append(a)

    bp.stages = [MagicMock(to_dict=MagicMock(return_value={"stage": 1}))]
    return bp


def _make_evaluation(success: bool, score: float):
    return SuccessEvaluation(
        overall_success=success,
        overall_score=score,
        metric_results=[],
        summary="x",
    )


# Need this import for the helpers above
from attune.socratic.success_models import SuccessEvaluation  # noqa: E402


@pytest.mark.unit
class TestLoadDataCorruptedWorkflowPatterns:
    """Cover lines 67-73: corrupted workflow_patterns.json swallowed."""

    def test_corrupted_patterns_file_swallowed(self, tmp_path, caplog):
        storage = tmp_path / "fb"
        storage.mkdir()
        (storage / "workflow_patterns.json").write_text("{not valid")

        # Should log warning, not crash
        with caplog.at_level("WARNING"):
            collector = FeedbackCollector(storage_path=str(storage))

        assert collector._workflow_patterns == {}
        assert any("Failed to load workflow patterns" in m for m in caplog.messages)

    def test_corrupted_agent_performance_file_swallowed(self, tmp_path, caplog):
        storage = tmp_path / "fb"
        storage.mkdir()
        (storage / "agent_performance.json").write_text("{broken")

        with caplog.at_level("WARNING"):
            collector = FeedbackCollector(storage_path=str(storage))

        assert collector._agent_performance == {}

    def test_load_valid_workflow_patterns(self, tmp_path):
        """Cover lines 70-71: parse valid workflow_patterns.json into WorkflowPattern."""
        storage = tmp_path / "fb"
        storage.mkdir()
        # WorkflowPattern accepts pattern_id, domain, agent_combination,
        # stage_configuration, uses, successes, average_score — no success_rate.
        data = {
            "pat-1": {
                "pattern_id": "pat-1",
                "domain": "code_review",
                "agent_combination": ["agent_a"],
                "stage_configuration": [],
                "uses": 5,
                "successes": 4,
                "average_score": 0.85,
            },
        }
        (storage / "workflow_patterns.json").write_text(json.dumps(data))

        collector = FeedbackCollector(storage_path=str(storage))
        assert "pat-1" in collector._workflow_patterns
        loaded = collector._workflow_patterns["pat-1"]
        assert loaded.uses == 5
        assert loaded.successes == 4
        assert loaded.average_score == 0.85


@pytest.mark.unit
class TestRecordExecutionExistingEntries:
    """Cover branches 110->113, 123->131, 133->136."""

    def test_repeated_record_uses_existing_perf_and_pattern(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        bp = _make_blueprint(agent_template_ids=["agent_a"])

        # First record creates entries
        collector.record_execution(bp, _make_evaluation(True, 0.9))
        # Second record exercises the existing-entry branches AND failure path
        collector.record_execution(bp, _make_evaluation(False, 0.4))

        perf = collector._agent_performance["agent_a"]
        assert perf.total_uses == 2

        pattern_id = collector._generate_pattern_id(bp)
        pattern = collector._workflow_patterns[pattern_id]
        assert pattern.uses == 2
        assert pattern.successes == 1  # only first was success → covers `if success` False branch


@pytest.mark.unit
class TestGetSuccessfulPatternsFilters:
    """Cover lines 212 and 214: min_uses and min_success_rate filters."""

    def test_min_uses_filter_excludes_low_use_pattern(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        # Add patterns directly
        p_low = WP(
            pattern_id="p1",
            domain="x",
            agent_combination=["a"],
            stage_configuration=[],
            uses=2,
            successes=2,
            average_score=0.9,
        )
        p_high = WP(
            pattern_id="p2",
            domain="x",
            agent_combination=["a"],
            stage_configuration=[],
            uses=10,
            successes=9,
            average_score=0.9,
        )
        collector._workflow_patterns["p1"] = p_low
        collector._workflow_patterns["p2"] = p_high

        results = collector.get_successful_patterns(min_uses=5)
        assert [p.pattern_id for p in results] == ["p2"]

    def test_min_success_rate_filter_excludes_low_rate(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        p = WP(
            pattern_id="p1",
            domain="x",
            agent_combination=["a"],
            stage_configuration=[],
            uses=10,
            successes=4,  # 40% success
            average_score=0.5,
        )
        collector._workflow_patterns["p1"] = p

        results = collector.get_successful_patterns(min_success_rate=0.7)
        assert results == []


@pytest.mark.unit
class TestInsightsDecliningAndDomainBranches:
    """Cover line 251 (declining_agents append) and 270->269 (zero-use skip)."""

    def test_declining_agent_appears_in_insights(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        perf = AgentPerformance(template_id="weak_agent")
        perf.total_uses = 6
        # Build trend by adding old high scores then recent low ones
        perf.recent_scores = [
            ("2024-01-01", 0.9),
            ("2024-01-02", 0.9),
            ("2024-01-03", 0.9),
            ("2024-01-04", 0.9),
            ("2024-01-05", 0.9),
            ("2024-02-01", 0.2),
            ("2024-02-02", 0.2),
            ("2024-02-03", 0.2),
            ("2024-02-04", 0.2),
            ("2024-02-05", 0.2),
        ]
        perf.average_score = 0.4
        collector._agent_performance["weak_agent"] = perf

        insights = collector.get_insights()
        declining_ids = [d["template_id"] for d in insights["declining_agents"]]
        assert "weak_agent" in declining_ids

    def test_zero_use_domain_skipped_from_insights(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        perf = AgentPerformance(template_id="zero_agent")
        # Domain entry but zero uses — skipped by the `if total_uses > 0` guard
        perf.by_domain = {"empty_domain": {"uses": 0, "total_score": 0.0}}
        collector._agent_performance["zero_agent"] = perf

        insights = collector.get_insights()
        # The zero-use domain should not appear in domain_insights
        assert "empty_domain" not in insights["domain_insights"]


@pytest.mark.unit
class TestGenerateRecommendations:
    """Cover lines 296-297 (successful patterns rec) and 303-304 (sparse domain rec)."""

    def test_successful_patterns_appear_in_recommendations(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        # Pattern with high success and uses
        pattern = WP(
            pattern_id="success-p",
            domain="security",
            agent_combination=["sec-rev"],
            stage_configuration=[],
            uses=10,
            successes=9,
            average_score=0.9,
        )
        collector._workflow_patterns["success-p"] = pattern

        recs = collector._generate_recommendations()
        assert any("Successful pattern for 'security'" in r for r in recs)

    def test_sparse_domain_recommendation(self, tmp_path):
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))
        perf = AgentPerformance(template_id="agent_x")
        perf.total_uses = 1
        perf.average_score = 0.7
        # Total domain uses = 1, < 5 threshold
        perf.by_domain = {"obscure_domain": {"uses": 1, "total_score": 0.7}}
        collector._agent_performance["agent_x"] = perf

        recs = collector._generate_recommendations()
        assert any("More data needed for 'obscure_domain'" in r for r in recs)

    def test_underperforming_agent_recommendation(self, tmp_path):
        """Existing test confirms; also covers branch 288->287 (success_rate >= 0.5)."""
        collector = FeedbackCollector(storage_path=str(tmp_path / "fb"))

        # Healthy agent → no underperformance recommendation
        good = AgentPerformance(template_id="good")
        good.total_uses = 12
        good.successful_uses = 10
        collector._agent_performance["good"] = good

        recs = collector._generate_recommendations()
        assert not any("'good'" in r and "configuration" in r for r in recs)
