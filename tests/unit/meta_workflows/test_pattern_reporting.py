"""Unit tests for attune.meta_workflows.pattern_reporting."""

from __future__ import annotations

from attune.meta_workflows.pattern_reporting import print_analytics_report


def _summary(**overrides):
    base = {
        "total_runs": 10,
        "successful_runs": 8,
        "success_rate": 0.8,
        "total_cost": 1.23,
        "avg_cost_per_run": 0.12,
        "total_agents_created": 30,
        "avg_agents_per_run": 3.0,
    }
    base.update(overrides)
    return base


class TestPrintAnalyticsReport:
    def test_summary_only(self, capsys):
        """Minimal report with just summary section."""
        report = {"summary": _summary()}
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "META-WORKFLOW ANALYTICS REPORT" in out
        assert "Total Runs: 10" in out
        assert "Successful: 8 (80%)" in out
        assert "Total Cost: $1.23" in out
        assert "Avg Cost/Run: $0.12" in out
        assert "Total Agents: 30" in out
        assert "Avg Agents/Run: 3.0" in out

    def test_with_recommendations(self, capsys):
        """recommendations key triggers Recommendations section."""
        report = {
            "summary": _summary(),
            "recommendations": ["Use cheaper tier", "Reduce agent count"],
        }
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Recommendations" in out
        assert "Use cheaper tier" in out
        assert "Reduce agent count" in out

    def test_empty_recommendations_skipped(self, capsys):
        """Empty list is falsy → section skipped."""
        report = {"summary": _summary(), "recommendations": []}
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Recommendations" not in out

    def test_with_tier_performance_insights(self, capsys):
        report = {
            "summary": _summary(),
            "insights": {
                "tier_performance": [
                    {
                        "description": "premium tier has 95% success",
                        "confidence": 0.92,
                        "sample_size": 50,
                    }
                ],
            },
        }
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Tier Performance" in out
        assert "premium tier has 95% success" in out
        assert "Confidence: 92% (n=50)" in out

    def test_with_cost_analysis_insights(self, capsys):
        report = {
            "summary": _summary(),
            "insights": {
                "cost_analysis": [
                    {"description": "Cost increased 30% over last week"},
                ],
            },
        }
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Cost Analysis" in out
        assert "Cost increased 30%" in out

    def test_with_failure_analysis_insights(self, capsys):
        report = {
            "summary": _summary(),
            "insights": {
                "failure_analysis": [
                    {"description": "Most failures occur in security stage"},
                ],
            },
        }
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Failure Analysis" in out
        assert "Most failures occur in security" in out

    def test_all_insight_categories_together(self, capsys):
        report = {
            "summary": _summary(),
            "recommendations": ["Optimize"],
            "insights": {
                "tier_performance": [{"description": "tp", "confidence": 0.5, "sample_size": 10}],
                "cost_analysis": [{"description": "ca"}],
                "failure_analysis": [{"description": "fa"}],
            },
        }
        print_analytics_report(report)
        out = capsys.readouterr().out
        for header in (
            "## Recommendations",
            "## Tier Performance",
            "## Cost Analysis",
            "## Failure Analysis",
        ):
            assert header in out

    def test_empty_insights_dict(self, capsys):
        """All insight buckets empty/missing → none rendered."""
        report = {"summary": _summary(), "insights": {}}
        print_analytics_report(report)
        out = capsys.readouterr().out
        assert "## Tier Performance" not in out
        assert "## Cost Analysis" not in out
        assert "## Failure Analysis" not in out

    def test_no_insights_key(self, capsys):
        """No 'insights' key at all → safe default."""
        report = {"summary": _summary()}
        print_analytics_report(report)
        # Should not raise
