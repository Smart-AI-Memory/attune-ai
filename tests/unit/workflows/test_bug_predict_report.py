"""Tests for bug_predict_report module — format_bug_predict_report."""

from __future__ import annotations

from attune.workflows.bug_predict_report import format_bug_predict_report


def _base_result(**overrides):
    """Build a minimal result dict."""
    base = {
        "overall_risk_score": 0,
        "recommendations": "",
        "model_tier_used": "capable",
    }
    base.update(overrides)
    return base


def _base_input(**overrides):
    """Build a minimal input_data dict."""
    base = {
        "file_count": 0,
        "pattern_count": 0,
        "patterns_found": [],
        "predictions": [],
        "correlations": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Risk level classification
# ---------------------------------------------------------------------------


class TestRiskLevel:
    """Risk icon and text based on overall_risk_score thresholds."""

    def test_high_risk(self):
        report = format_bug_predict_report(_base_result(overall_risk_score=0.85), _base_input())
        assert "HIGH RISK" in report

    def test_moderate_risk(self):
        report = format_bug_predict_report(_base_result(overall_risk_score=0.55), _base_input())
        assert "MODERATE RISK" in report

    def test_low_risk(self):
        report = format_bug_predict_report(_base_result(overall_risk_score=0.35), _base_input())
        assert "LOW RISK" in report

    def test_minimal_risk(self):
        report = format_bug_predict_report(_base_result(overall_risk_score=0.1), _base_input())
        assert "MINIMAL RISK" in report


# ---------------------------------------------------------------------------
# Scan summary
# ---------------------------------------------------------------------------


class TestScanSummary:
    """Scan summary section."""

    def test_file_and_pattern_count(self):
        report = format_bug_predict_report(
            _base_result(),
            _base_input(file_count=42, pattern_count=7),
        )
        assert "Files Scanned: 42" in report
        assert "Patterns Found: 7" in report


# ---------------------------------------------------------------------------
# Pattern breakdown
# ---------------------------------------------------------------------------


class TestPatternBreakdown:
    """Patterns found breakdown by severity."""

    def test_shows_severity_counts(self):
        patterns = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "low"},
            {"severity": "low"},
        ]
        report = format_bug_predict_report(_base_result(), _base_input(patterns_found=patterns))
        assert "High: 2" in report
        assert "Medium: 1" in report
        assert "Low: 3" in report

    def test_no_breakdown_when_no_patterns(self):
        report = format_bug_predict_report(_base_result(), _base_input(patterns_found=[]))
        assert "Pattern Breakdown:" not in report


# ---------------------------------------------------------------------------
# High risk files
# ---------------------------------------------------------------------------


class TestHighRiskFiles:
    """High risk files section (risk_score > 0.7)."""

    def test_renders_high_risk_predictions(self):
        predictions = [
            {
                "file": "src/danger.py",
                "risk_score": 0.9,
                "patterns": [
                    {"pattern": "eval_usage", "severity": "high"},
                ],
            },
        ]
        report = format_bug_predict_report(_base_result(), _base_input(predictions=predictions))
        assert "HIGH RISK FILES" in report
        assert "src/danger.py" in report
        assert "eval_usage" in report

    def test_no_section_when_no_high_risk(self):
        predictions = [{"file": "ok.py", "risk_score": 0.3, "patterns": []}]
        report = format_bug_predict_report(_base_result(), _base_input(predictions=predictions))
        assert "HIGH RISK FILES" not in report

    def test_limits_to_10_files(self):
        predictions = [{"file": f"f{i}.py", "risk_score": 0.95, "patterns": []} for i in range(15)]
        report = format_bug_predict_report(_base_result(), _base_input(predictions=predictions))
        assert "f9.py" in report
        assert "f10.py" not in report

    def test_limits_patterns_per_file_to_3(self):
        predictions = [
            {
                "file": "big.py",
                "risk_score": 0.85,
                "patterns": [{"pattern": f"p{i}", "severity": "medium"} for i in range(5)],
            },
        ]
        report = format_bug_predict_report(_base_result(), _base_input(predictions=predictions))
        assert "p2" in report
        assert "p3" not in report


# ---------------------------------------------------------------------------
# Historical correlations
# ---------------------------------------------------------------------------


class TestHistoricalCorrelations:
    """Historical bug correlations section."""

    def test_renders_high_confidence_correlations(self):
        correlations = [
            {
                "confidence": 0.8,
                "historical_bug": {
                    "type": "null_reference",
                    "root_cause": "Missing null check in parser",
                },
                "current_pattern": {"pattern": "unchecked_access"},
            },
        ]
        report = format_bug_predict_report(_base_result(), _base_input(correlations=correlations))
        assert "HISTORICAL BUG CORRELATIONS" in report
        assert "null_reference" in report
        assert "Missing null check" in report

    def test_no_section_when_no_high_confidence(self):
        correlations = [
            {"confidence": 0.3, "historical_bug": {"type": "x"}, "current_pattern": {}},
        ]
        report = format_bug_predict_report(_base_result(), _base_input(correlations=correlations))
        assert "HISTORICAL BUG CORRELATIONS" not in report

    def test_skips_entries_without_historical_bug(self):
        correlations = [
            {"confidence": 0.9, "historical_bug": None, "current_pattern": {}},
        ]
        report = format_bug_predict_report(_base_result(), _base_input(correlations=correlations))
        assert "HISTORICAL BUG CORRELATIONS" not in report

    def test_truncates_root_cause_to_80_chars(self):
        long_cause = "X" * 120
        correlations = [
            {
                "confidence": 0.9,
                "historical_bug": {"type": "bug", "root_cause": long_cause},
                "current_pattern": {"pattern": "test"},
            },
        ]
        report = format_bug_predict_report(_base_result(), _base_input(correlations=correlations))
        # The truncated root cause should be at most 80 chars
        lines = [line for line in report.split("\n") if "Root cause:" in line]
        assert len(lines) == 1
        # Extract value after "Root cause: "
        root_text = lines[0].split("Root cause: ")[1]
        assert len(root_text) == 80


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class TestRecommendations:
    """Recommendations section."""

    def test_renders_recommendations(self):
        report = format_bug_predict_report(
            _base_result(recommendations="Add tests for edge cases."),
            _base_input(),
        )
        assert "RECOMMENDATIONS" in report
        assert "Add tests for edge cases." in report

    def test_no_section_when_empty(self):
        report = format_bug_predict_report(_base_result(recommendations=""), _base_input())
        assert "RECOMMENDATIONS" not in report


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------


class TestFooter:
    """Report footer."""

    def test_footer_shows_model_tier(self):
        report = format_bug_predict_report(_base_result(model_tier_used="premium"), _base_input())
        assert "premium" in report
        assert "BUG PREDICTION REPORT" in report
