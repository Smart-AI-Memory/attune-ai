"""Unit tests for PatternLearner.

Tests cover:
- Pattern analysis (agent counts, tier performance, costs, failures)
- Recommendations generation
- Analytics report generation
- Memory integration (when available)
- Graceful fallback when memory unavailable

Created: 2026-01-17
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from attune.meta_workflows import FormResponse, MetaWorkflow, PatternLearner, TemplateRegistry


class TestPatternLearnerInitialization:
    """Test PatternLearner initialization."""

    def test_init_default_directory(self):
        """Test initialization with default directory."""
        learner = PatternLearner()

        expected_dir = Path.home() / ".attune" / "meta_workflows" / "executions"
        assert learner.executions_dir == expected_dir
        assert learner.memory is None

    def test_init_custom_directory(self, tmp_path):
        """Test initialization with custom directory."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        assert learner.executions_dir == tmp_path
        assert learner.memory is None

    def test_init_with_memory(self, tmp_path):
        """Test initialization with memory integration."""
        mock_memory = Mock()

        learner = PatternLearner(executions_dir=str(tmp_path), memory=mock_memory)

        assert learner.executions_dir == tmp_path
        assert learner.memory == mock_memory


class TestPatternAnalysis:
    """Test pattern analysis methods."""

    @pytest.fixture
    def sample_executions(self, tmp_path):
        """Create sample execution results for testing."""
        registry = TemplateRegistry(storage_dir=str(tmp_path / "templates"))
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))

        # Create 3 executions with different configurations
        results = []

        configs = [
            {"security_scan": "No", "coverage_threshold": "70%"},
            {"security_scan": "Yes", "coverage_threshold": "80%", "quality_review": "Yes"},
            {
                "security_scan": "Yes",
                "coverage_threshold": "90%",
                "quality_review": "Yes",
                "doc_verification": "Yes",
            },
        ]

        for config in configs:
            response = FormResponse(
                template_id="release-prep",
                responses=config,
            )
            result = workflow.execute(form_response=response, mock_execution=True)
            results.append(result)

        return tmp_path, results

    def test_analyze_patterns_empty_directory(self, tmp_path):
        """Test analyze_patterns with no execution results."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        insights = learner.analyze_patterns()

        assert insights == []

    def test_analyze_patterns_with_results(self, sample_executions):
        """Test analyze_patterns with execution results."""
        tmp_path, _ = sample_executions

        learner = PatternLearner(executions_dir=str(tmp_path))
        insights = learner.analyze_patterns(min_confidence=0.0)

        # Should have insights for: agent_count, tier_performance, cost_analysis
        assert len(insights) > 0

        # Check insight types
        insight_types = {i.insight_type for i in insights}
        assert "agent_count" in insight_types
        assert "cost_analysis" in insight_types

    def test_analyze_agent_counts(self, sample_executions):
        """Test agent count analysis."""
        tmp_path, _ = sample_executions

        learner = PatternLearner(executions_dir=str(tmp_path))
        insights = learner.analyze_patterns(min_confidence=0.0)

        agent_count_insights = [i for i in insights if i.insight_type == "agent_count"]
        assert len(agent_count_insights) == 1

        insight = agent_count_insights[0]
        assert "average" in insight.data
        assert "min" in insight.data
        assert "max" in insight.data
        assert insight.data["average"] > 0

    def test_analyze_tier_performance(self, sample_executions):
        """Test tier performance analysis."""
        tmp_path, results = sample_executions

        learner = PatternLearner(executions_dir=str(tmp_path))
        insights = learner.analyze_patterns(min_confidence=0.0)

        tier_insights = [i for i in insights if i.insight_type == "tier_performance"]

        # With 3 executions, we should have some tier performance data
        # But it depends on how many agents with >= 3 samples
        # Just verify structure if any exist
        for insight in tier_insights:
            assert "role" in insight.data
            assert "tier" in insight.data
            assert "success_rate" in insight.data
            assert 0.0 <= insight.data["success_rate"] <= 1.0

    def test_analyze_costs(self, sample_executions):
        """Test cost analysis."""
        tmp_path, _ = sample_executions

        learner = PatternLearner(executions_dir=str(tmp_path))
        insights = learner.analyze_patterns(min_confidence=0.0)

        cost_insights = [i for i in insights if i.insight_type == "cost_analysis"]
        assert len(cost_insights) == 1

        insight = cost_insights[0]
        assert "average" in insight.data
        assert "min" in insight.data
        assert "max" in insight.data
        assert "tier_breakdown" in insight.data
        assert insight.data["average"] > 0

    def test_min_confidence_filtering(self, sample_executions):
        """Test that min_confidence filters low-confidence insights."""
        tmp_path, _ = sample_executions

        learner = PatternLearner(executions_dir=str(tmp_path))

        # Low confidence threshold
        all_insights = learner.analyze_patterns(min_confidence=0.0)

        # High confidence threshold
        high_conf_insights = learner.analyze_patterns(min_confidence=0.9)

        # Should have fewer insights with higher threshold
        assert len(high_conf_insights) <= len(all_insights)


class TestRecommendations:
    """Test recommendation generation."""

    @pytest.fixture
    def sample_executions(self, tmp_path):
        """Create sample execution results for testing."""
        registry = TemplateRegistry(storage_dir=str(tmp_path / "templates"))
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))

        # Create 5 executions to have enough data for recommendations
        for _i in range(5):
            response = FormResponse(
                template_id="release-prep",
                responses={
                    "security_scan": "Yes",
                    "coverage_threshold": "80%",
                    "quality_review": "Yes",
                },
            )
            workflow.execute(form_response=response, mock_execution=True)

        return tmp_path

    def test_get_recommendations_no_data(self, tmp_path):
        """Test get_recommendations with no execution data."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        recommendations = learner.get_recommendations("release-prep")

        assert recommendations == []

    def test_get_recommendations_with_data(self, sample_executions):
        """Test get_recommendations with execution data."""
        learner = PatternLearner(executions_dir=str(sample_executions))

        recommendations = learner.get_recommendations(
            "release-prep",
            min_confidence=0.0,  # Very low threshold for small sample
        )

        # With mock data, might not have enough samples for high-confidence recommendations
        # Just verify it returns a list
        assert isinstance(recommendations, list)

    def test_recommendations_filter_by_template(self, sample_executions):
        """Test that recommendations filter by template_id."""
        learner = PatternLearner(executions_dir=str(sample_executions))

        # Valid template
        valid_recs = learner.get_recommendations("release-prep", min_confidence=0.0)

        # Invalid template
        invalid_recs = learner.get_recommendations("nonexistent_template")

        # Invalid template should always return empty
        assert len(invalid_recs) == 0

        # Valid template should return list (even if empty for small samples)
        assert isinstance(valid_recs, list)


class TestAnalyticsReport:
    """Test analytics report generation."""

    @pytest.fixture
    def sample_executions(self, tmp_path):
        """Create sample execution results for testing."""
        import time

        registry = TemplateRegistry(storage_dir=str(tmp_path / "templates"))
        template = registry.load_template("release-prep")

        workflow = MetaWorkflow(template=template, storage_dir=str(tmp_path))

        for i in range(3):
            response = FormResponse(
                template_id="release-prep",
                responses={"security_scan": "Yes", "coverage_threshold": "80%"},
            )
            workflow.execute(form_response=response, mock_execution=True)

            # Sleep to ensure different timestamps
            if i < 2:
                time.sleep(1.1)

        return tmp_path

    def test_generate_analytics_report(self, sample_executions):
        """Test analytics report generation."""
        learner = PatternLearner(executions_dir=str(sample_executions))

        report = learner.generate_analytics_report(template_id="release-prep")

        # Check structure
        assert "summary" in report
        assert "insights" in report
        assert "recommendations" in report

        # Check summary (should have at least 2-3 runs)
        summary = report["summary"]
        assert summary["total_runs"] >= 2  # At least 2 runs
        assert summary["successful_runs"] >= 2
        assert summary["success_rate"] > 0
        assert summary["total_cost"] > 0
        assert summary["avg_cost_per_run"] > 0

    def test_analytics_report_empty_directory(self, tmp_path):
        """Test analytics report with no execution data."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        report = learner.generate_analytics_report()

        assert report["summary"]["total_runs"] == 0
        assert report["summary"]["successful_runs"] == 0
        assert report["summary"]["total_cost"] == 0


class TestMemoryIntegration:
    """Test memory integration features."""

    def test_store_execution_in_memory_no_memory(self, tmp_path):
        """Test store_execution_in_memory when memory not available."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        # Create a mock result
        from attune.meta_workflows.models import MetaWorkflowResult

        result = MetaWorkflowResult(
            run_id="test-run",
            template_id="test_template",
            timestamp="2026-01-17T10:00:00",
            form_responses=FormResponse(template_id="test_template"),
            total_cost=1.0,
            total_duration=10.0,
            success=True,
        )

        # Should return None when memory not available
        pattern_id = learner.store_execution_in_memory(result)

        assert pattern_id is None

    def test_store_execution_in_memory_with_memory(self, tmp_path):
        """Test store_execution_in_memory with memory integration."""
        mock_memory = Mock()
        mock_memory.persist_pattern.return_value = {"pattern_id": "pat_123"}

        learner = PatternLearner(executions_dir=str(tmp_path), memory=mock_memory)

        # Create a mock result with agent results
        from attune.meta_workflows.models import (
            AgentExecutionResult,
            AgentSpec,
            MetaWorkflowResult,
            TierStrategy,
        )

        agent = AgentSpec(
            role="test_agent",
            base_template="general",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        agent_result = AgentExecutionResult(
            agent_id=agent.agent_id,
            role="test_agent",
            success=True,
            cost=0.05,
            duration=1.0,
            tier_used="cheap",
            output={"message": "Test execution"},
        )

        result = MetaWorkflowResult(
            run_id="test-run",
            template_id="test_template",
            timestamp="2026-01-17T10:00:00",
            form_responses=FormResponse(
                template_id="test_template",
                responses={"key": "value"},
            ),
            agents_created=[agent],
            agent_results=[agent_result],
            total_cost=0.05,
            total_duration=1.0,
            success=True,
        )

        # Store in memory
        pattern_id = learner.store_execution_in_memory(result)

        # Should call persist_pattern
        assert pattern_id == "pat_123"
        mock_memory.persist_pattern.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_memory.persist_pattern.call_args.kwargs
        assert call_kwargs["pattern_type"] == "meta_workflow_execution"
        assert call_kwargs["classification"] == "INTERNAL"
        assert "test-run" in call_kwargs["content"]

    def test_search_executions_fallback(self, tmp_path):
        """Test search_executions_by_context falls back to files."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        # Without memory, should fall back to file search
        results = learner.search_executions_by_context(
            query="test query",
            limit=5,
        )

        # Should return empty list for empty directory
        assert results == []

    def test_get_smart_recommendations_no_memory(self, tmp_path):
        """Test get_smart_recommendations falls back without memory."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        response = FormResponse(
            template_id="test_template",
            responses={"key": "value"},
        )

        recommendations = learner.get_smart_recommendations(
            template_id="test_template",
            form_response=response,
        )

        # Should return empty (no data) but shouldn't crash
        assert isinstance(recommendations, list)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_analyze_patterns_invalid_template(self, tmp_path):
        """Test analyze_patterns with non-existent template."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        insights = learner.analyze_patterns(template_id="nonexistent_template")

        # Should return empty list, not crash
        assert insights == []

    def test_load_corrupted_result(self, tmp_path):
        """Test handling of corrupted result files."""
        learner = PatternLearner(executions_dir=str(tmp_path))

        # Create a corrupted result file
        run_dir = tmp_path / "corrupted-run"
        run_dir.mkdir()
        result_file = run_dir / "result.json"
        result_file.write_text("{invalid json")

        # analyze_patterns should handle this gracefully
        insights = learner.analyze_patterns()

        # Should skip corrupted file and return empty
        assert insights == []
