#!/usr/bin/env python3
"""Unit tests for tier pattern analysis system.

Tests:
- Pattern loading and validation
- Cost analysis calculations
- Tier recommendation logic
- Quality gate analysis
- XML protocol compliance tracking
"""

import json
import sys
from pathlib import Path

import pytest

# Add scripts to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from analyze_tier_patterns import TierPatternAnalyzer, TierRecommendation


@pytest.fixture
def sample_pattern():
    """Sample enhanced pattern for testing."""
    return {
        "pattern_id": "bug_test_001",
        "bug_type": "integration_error",
        "status": "resolved",
        "tier_progression": {
            "methodology": "AI-ADDIE",
            "starting_tier": "CHEAP",
            "successful_tier": "CHEAP",
            "total_attempts": 1,
            "tier_history": [
                {
                    "tier": "CHEAP",
                    "attempts": 1,
                    "success": {"attempt": 1, "quality_gates_passed": ["tests", "lint", "types"]},
                },
            ],
            "cost_breakdown": {
                "total_cost": 0.030,
                "cost_if_always_premium": 0.930,
                "savings_percent": 96.8,
            },
            "quality_metrics": {
                "tests_passed": True,
                "health_score_before": 73,
                "health_score_after": 73,
            },
            "xml_protocol_compliance": {
                "prompt_used_xml": True,
                "response_used_xml": True,
                "all_sections_present": True,
                "test_evidence_provided": True,
                "false_complete_avoided": True,
            },
        },
    }


@pytest.fixture
def sample_pattern_with_failures():
    """Pattern with quality gate failures for testing."""
    return {
        "pattern_id": "bug_test_002",
        "bug_type": "type_mismatch",
        "status": "resolved",
        "tier_progression": {
            "methodology": "AI-ADDIE",
            "starting_tier": "CHEAP",
            "successful_tier": "CAPABLE",
            "total_attempts": 5,
            "tier_history": [
                {
                    "tier": "CHEAP",
                    "attempts": 3,
                    "failures": [
                        {"attempt": 1, "quality_gate_failed": "mypy"},
                        {"attempt": 2, "quality_gate_failed": "mypy"},
                        {"attempt": 3, "quality_gate_failed": "tests"},
                    ],
                },
                {
                    "tier": "CAPABLE",
                    "attempts": 2,
                    "failures": [{"attempt": 1, "quality_gate_failed": "lint"}],
                    "success": {"attempt": 2, "quality_gates_passed": ["tests", "lint", "types"]},
                },
            ],
            "cost_breakdown": {
                "total_cost": 0.225,
                "cost_if_always_premium": 0.450,
                "savings_percent": 50.0,
            },
            "quality_metrics": {
                "tests_passed": True,
                "health_score_before": 49,
                "health_score_after": 73,
            },
            "xml_protocol_compliance": {
                "prompt_used_xml": True,
                "response_used_xml": True,
                "all_sections_present": True,
                "test_evidence_provided": True,
                "false_complete_avoided": True,
            },
        },
    }


class TestTierPatternAnalyzer:
    """Test suite for TierPatternAnalyzer class."""

    def test_load_patterns_empty_directory(self, tmp_path):
        """Test loading from empty patterns directory."""
        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        assert analyzer.patterns == []

    def test_load_patterns_with_enhanced_data(self, tmp_path, sample_pattern):
        """Test loading patterns with tier_progression data."""
        pattern_file = tmp_path / "bug_test_001.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        assert len(analyzer.patterns) == 1
        assert analyzer.patterns[0]["pattern_id"] == "bug_test_001"

    def test_load_patterns_skips_legacy_format(self, tmp_path):
        """Test that patterns without tier_progression are skipped."""
        legacy_pattern = {
            "pattern_id": "bug_legacy_001",
            "bug_type": "unknown",
            "status": "resolved",
        }

        pattern_file = tmp_path / "bug_legacy_001.json"
        with open(pattern_file, "w") as f:
            json.dump(legacy_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        assert len(analyzer.patterns) == 0

    def test_analyze_by_bug_type_all(self, tmp_path, sample_pattern):
        """Test analysis across all bug types."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        analysis = analyzer.analyze_by_bug_type()

        assert analysis["bug_type"] == "all"
        assert analysis["total_patterns"] == 1
        assert analysis["tier_distribution"]["CHEAP"] == 1
        assert analysis["avg_cost"] == 0.030
        assert analysis["avg_attempts"] == 1.0

    def test_analyze_by_bug_type_filtered(self, tmp_path, sample_pattern):
        """Test analysis filtered by specific bug type."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        analysis = analyzer.analyze_by_bug_type("integration_error")

        assert analysis["bug_type"] == "integration_error"
        assert analysis["total_patterns"] == 1

    def test_analyze_by_bug_type_no_matches(self, tmp_path, sample_pattern):
        """Test analysis with no matching bug types."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        analysis = analyzer.analyze_by_bug_type("nonexistent_type")

        assert "error" in analysis

    def test_calculate_savings(self, tmp_path, sample_pattern):
        """Test cost savings calculation."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        savings = analyzer.calculate_savings()

        assert savings["total_patterns"] == 1
        assert savings["actual_cost"] == 0.03
        assert savings["cost_if_always_premium"] == 0.93
        assert savings["total_savings"] == 0.9
        assert savings["savings_percent"] == 96.8

    def test_calculate_savings_multiple_patterns(
        self,
        tmp_path,
        sample_pattern,
        sample_pattern_with_failures,
    ):
        """Test savings calculation with multiple patterns."""
        with open(tmp_path / "bug1.json", "w") as f:
            json.dump(sample_pattern, f)
        with open(tmp_path / "bug2.json", "w") as f:
            json.dump(sample_pattern_with_failures, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        savings = analyzer.calculate_savings()

        assert savings["total_patterns"] == 2
        # 0.030 + 0.225 = 0.255
        assert savings["actual_cost"] == 0.26  # rounded
        # 0.930 + 0.450 = 1.380
        assert savings["cost_if_always_premium"] == 1.38

    def test_quality_gate_report_no_failures(self, tmp_path, sample_pattern):
        """Test quality gate report with no failures."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        report = analyzer.quality_gate_report()

        assert "message" in report
        assert "No failures" in report["message"]

    def test_quality_gate_report_with_failures(self, tmp_path, sample_pattern_with_failures):
        """Test quality gate report with failures."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern_with_failures, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        report = analyzer.quality_gate_report()

        assert report["total_failures"] == 4
        assert len(report["gate_effectiveness"]) == 3

        # Check mypy caught most failures
        mypy_data = next((g for g in report["gate_effectiveness"] if g["gate"] == "mypy"), None)
        assert mypy_data is not None
        assert mypy_data["failures_caught"] == 2

    def test_xml_protocol_effectiveness(self, tmp_path, sample_pattern):
        """Test XML protocol compliance tracking."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        report = analyzer.xml_protocol_effectiveness()

        assert report["total_analyzed"] == 1
        assert report["prompt_used_xml"] == 1
        assert report["response_used_xml"] == 1
        assert report["prompt_used_xml_percent"] == 100.0
        assert report["false_complete_avoided_percent"] == 100.0

    def test_recommend_tier_integration_error(self, tmp_path, sample_pattern):
        """Test tier recommendation for integration errors."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        rec = analyzer.recommend_tier("integration test failure with import error")

        assert rec.recommended_tier == "CHEAP"
        assert rec.confidence == 1.0
        assert rec.historical_success_rate == 1.0
        assert rec.avg_cost == 0.030

    def test_recommend_tier_type_mismatch(self, tmp_path, sample_pattern_with_failures):
        """Test tier recommendation for type errors."""
        pattern_file = tmp_path / "bug_test.json"
        with open(pattern_file, "w") as f:
            json.dump(sample_pattern_with_failures, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        rec = analyzer.recommend_tier("type annotation missing in function")

        assert rec.recommended_tier == "CAPABLE"
        assert rec.confidence == 1.0
        assert rec.avg_cost == 0.225

    def test_recommend_tier_unknown_pattern(self, tmp_path):
        """Test tier recommendation with no historical data."""
        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        rec = analyzer.recommend_tier("completely new bug type")

        assert rec.recommended_tier == "CHEAP"  # Default
        assert rec.confidence == 0.5  # Low confidence
        assert rec.reasoning == "No historical data, defaulting to CHEAP tier"

    def test_tier_distribution_calculation(
        self,
        tmp_path,
        sample_pattern,
        sample_pattern_with_failures,
    ):
        """Test tier distribution across multiple patterns."""
        with open(tmp_path / "bug1.json", "w") as f:
            json.dump(sample_pattern, f)
        with open(tmp_path / "bug2.json", "w") as f:
            json.dump(sample_pattern_with_failures, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        analysis = analyzer.analyze_by_bug_type()

        assert analysis["tier_distribution"]["CHEAP"] == 1
        assert analysis["tier_distribution"]["CAPABLE"] == 1

    def test_avg_attempts_calculation(self, tmp_path, sample_pattern, sample_pattern_with_failures):
        """Test average attempts calculation."""
        with open(tmp_path / "bug1.json", "w") as f:
            json.dump(sample_pattern, f)
        with open(tmp_path / "bug2.json", "w") as f:
            json.dump(sample_pattern_with_failures, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        analysis = analyzer.analyze_by_bug_type()

        # (1 + 5) / 2 = 3.0
        assert analysis["avg_attempts"] == 3.0


class TestTierRecommendation:
    """Test TierRecommendation dataclass."""

    def test_recommendation_creation(self):
        """Test creating a tier recommendation."""
        rec = TierRecommendation(
            recommended_tier="CAPABLE",
            confidence=0.85,
            reasoning="85% of similar bugs resolved at CAPABLE",
            historical_success_rate=0.85,
            avg_cost=0.090,
            avg_attempts=2.5,
        )

        assert rec.recommended_tier == "CAPABLE"
        assert rec.confidence == 0.85
        assert rec.avg_cost == 0.090


class TestPatternValidation:
    """Test enhanced pattern schema validation."""

    def test_valid_enhanced_pattern(self, sample_pattern):
        """Test that sample pattern has all required fields."""
        required_fields = ["pattern_id", "bug_type", "status", "tier_progression"]

        for field in required_fields:
            assert field in sample_pattern

        tp = sample_pattern["tier_progression"]
        required_tp_fields = [
            "methodology",
            "starting_tier",
            "successful_tier",
            "total_attempts",
            "tier_history",
            "cost_breakdown",
            "quality_metrics",
            "xml_protocol_compliance",
        ]

        for field in required_tp_fields:
            assert field in tp

    def test_cost_breakdown_structure(self, sample_pattern):
        """Test cost breakdown has required fields."""
        cb = sample_pattern["tier_progression"]["cost_breakdown"]

        assert "total_cost" in cb
        assert "cost_if_always_premium" in cb
        assert "savings_percent" in cb
        assert cb["total_cost"] < cb["cost_if_always_premium"]

    def test_xml_protocol_compliance_structure(self, sample_pattern):
        """Test XML protocol compliance tracking structure."""
        xpc = sample_pattern["tier_progression"]["xml_protocol_compliance"]

        required_fields = [
            "prompt_used_xml",
            "response_used_xml",
            "all_sections_present",
            "test_evidence_provided",
            "false_complete_avoided",
        ]

        for field in required_fields:
            assert field in xpc
            assert isinstance(xpc[field], bool)


class TestBackwardCompatibility:
    """Test backward compatibility with existing patterns."""

    def test_mixed_pattern_formats(self, tmp_path, sample_pattern):
        """Test loading mix of enhanced and legacy patterns."""
        # Enhanced pattern
        with open(tmp_path / "enhanced.json", "w") as f:
            json.dump(sample_pattern, f)

        # Legacy pattern
        legacy = {"pattern_id": "bug_legacy", "bug_type": "unknown", "status": "resolved"}
        with open(tmp_path / "legacy.json", "w") as f:
            json.dump(legacy, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)

        # Only enhanced pattern should be loaded
        assert len(analyzer.patterns) == 1
        assert analyzer.patterns[0]["pattern_id"] == "bug_test_001"

    def test_patterns_array_format(self, tmp_path, sample_pattern):
        """Test loading from patterns.json array format."""
        patterns_data = {"patterns": [sample_pattern], "last_updated": "2026-01-07"}

        with open(tmp_path / "patterns.json", "w") as f:
            json.dump(patterns_data, f)

        analyzer = TierPatternAnalyzer(patterns_dir=tmp_path)
        assert len(analyzer.patterns) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
