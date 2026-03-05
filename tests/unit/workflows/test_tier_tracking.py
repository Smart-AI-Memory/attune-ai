"""Unit tests for tier tracking module.

Tests WorkflowTierTracker, TierAttempt, and
WorkflowTierProgression dataclasses.
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from attune.workflows.tier_tracking import (
    TierAttempt,
    WorkflowTierProgression,
    WorkflowTierTracker,
    auto_recommend_tier,
)


@pytest.mark.unit
class TestTierAttempt:
    """Test TierAttempt dataclass."""

    def test_required_fields(self):
        """Test construction with required fields."""
        attempt = TierAttempt(tier="CHEAP", attempt=1, success=True)
        assert attempt.tier == "CHEAP"
        assert attempt.attempt == 1
        assert attempt.success is True
        assert attempt.quality_gate_failed is None
        assert attempt.quality_gates_passed is None

    def test_optional_fields(self):
        """Test construction with optional fields."""
        attempt = TierAttempt(
            tier="CAPABLE",
            attempt=2,
            success=False,
            quality_gate_failed="validation",
            quality_gates_passed=["syntax", "imports"],
        )
        assert attempt.quality_gate_failed == "validation"
        assert attempt.quality_gates_passed == ["syntax", "imports"]


@pytest.mark.unit
class TestWorkflowTierProgression:
    """Test WorkflowTierProgression dataclass."""

    def test_required_fields(self):
        """Test construction with all required fields."""
        progression = WorkflowTierProgression(
            workflow_name="security-audit",
            workflow_id="abc-123",
            bug_description="Audit security",
            files_affected=["src/main.py"],
            bug_type="audit",
            recommended_tier="CHEAP",
            starting_tier="CHEAP",
            successful_tier="CAPABLE",
            total_attempts=2,
            tier_history=[{"tier": "CHEAP", "attempts": 1}],
            total_cost=0.12,
            cost_if_always_premium=0.60,
            savings_percent=80.0,
            tests_passed=True,
            error_occurred=False,
            started_at="2026-01-01T00:00:00",
            completed_at="2026-01-01T00:01:00",
            duration_seconds=60.0,
        )
        assert progression.workflow_name == "security-audit"
        assert progression.successful_tier == "CAPABLE"
        assert progression.error_message is None

    def test_optional_error_message(self):
        """Test error_message optional field."""
        progression = WorkflowTierProgression(
            workflow_name="test",
            workflow_id="x",
            bug_description="d",
            files_affected=[],
            bug_type="t",
            recommended_tier="CHEAP",
            starting_tier="CHEAP",
            successful_tier="CHEAP",
            total_attempts=1,
            tier_history=[],
            total_cost=0.0,
            cost_if_always_premium=0.0,
            savings_percent=0.0,
            tests_passed=False,
            error_occurred=True,
            started_at="",
            completed_at="",
            duration_seconds=0.0,
            error_message="Something failed",
        )
        assert progression.error_message == "Something failed"


@pytest.mark.unit
class TestWorkflowTierTracker:
    """Test WorkflowTierTracker class."""

    def test_init_defaults(self, tmp_path):
        """Test tracker initializes with defaults."""
        tracker = WorkflowTierTracker(
            "test-workflow",
            "Test description",
            patterns_dir=tmp_path / "patterns",
        )
        assert tracker.workflow_name == "test-workflow"
        assert tracker.workflow_description == "Test description"
        assert tracker.recommended_tier is None
        assert tracker.tier_attempts == []
        assert (tmp_path / "patterns").exists()

    def test_record_tier_attempt(self, tmp_path):
        """Test recording a tier attempt."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path / "p")
        tracker.record_tier_attempt(
            tier="CHEAP",
            attempt=1,
            success=False,
            quality_gate_failed="validation",
        )
        tracker.record_tier_attempt(
            tier="CAPABLE",
            attempt=2,
            success=True,
            quality_gates_passed=["validation", "output"],
        )
        assert len(tracker.tier_attempts) == 2
        assert tracker.tier_attempts[0].success is False
        assert tracker.tier_attempts[1].success is True

    def test_save_progression_happy_path(self, tmp_path):
        """Test saving progression creates a JSON file."""
        tracker = WorkflowTierTracker("test-wf", "desc", patterns_dir=tmp_path)
        tracker.recommended_tier = "CHEAP"
        tracker.starting_tier = "CHEAP"

        # Mock a minimal WorkflowResult
        stage = SimpleNamespace(
            tier=SimpleNamespace(value="cheap"),
            cost=0.03,
            input_tokens=100,
            output_tokens=50,
            error=None,
        )
        result = SimpleNamespace(
            stages=[stage],
            error=None,
            cost_report={"total": 0.03},
        )

        saved = tracker.save_progression(result, files_affected=["a.py"])
        assert saved is not None

        # Verify file was written
        pattern_files = list(tmp_path.glob("workflow_*.json"))
        assert len(pattern_files) >= 1

        data = json.loads(pattern_files[0].read_text())
        assert data["source"] == "workflow_tracking"
        assert "tier_progression" in data

    def test_save_progression_creates_directory(self, tmp_path):
        """Test __init__ creates patterns_dir if it doesn't exist."""
        patterns = tmp_path / "deep" / "nested" / "dir"
        WorkflowTierTracker("test", "desc", patterns_dir=patterns)
        assert patterns.exists()

    def test_save_progression_path_validation_blocks_system_dirs(self, tmp_path):
        """Test that path validation blocks system directory writes."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path)
        # Override patterns_dir to a system path after init
        tracker.patterns_dir = Path("/etc")
        stage = SimpleNamespace(
            tier=SimpleNamespace(value="cheap"),
            cost=0.0,
            input_tokens=0,
            output_tokens=0,
            error=None,
        )
        result = SimpleNamespace(
            stages=[stage],
            error=None,
            cost_report={"total": 0},
        )
        # save_progression catches exceptions and returns None
        saved = tracker.save_progression(result)
        assert saved is None

    def test_cleanup_old_workflow_files(self, tmp_path):
        """Test cleanup removes old workflow files beyond limit."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path)
        tracker.MAX_WORKFLOW_FILES = 3

        # Create 5 workflow files
        for i in range(5):
            f = tmp_path / f"workflow_2026010{i}_test.json"
            f.write_text("{}")

        tracker._cleanup_old_workflow_files()

        remaining = list(tmp_path.glob("workflow_*.json"))
        assert len(remaining) == 3

    def test_cleanup_preserves_recent_files(self, tmp_path):
        """Test cleanup keeps the most recent files."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path)
        tracker.MAX_WORKFLOW_FILES = 2

        import time

        for i in range(4):
            f = tmp_path / f"workflow_{i:04d}_test.json"
            f.write_text(json.dumps({"index": i}))
            time.sleep(0.01)  # Ensure distinct mtimes

        tracker._cleanup_old_workflow_files()

        remaining = sorted(
            tmp_path.glob("workflow_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        assert len(remaining) == 2
        # Most recent files should survive
        data = json.loads(remaining[0].read_text())
        assert data["index"] == 3

    def test_determine_successful_tier_empty_stages(self, tmp_path):
        """Test _determine_successful_tier with no stages."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path)
        result = SimpleNamespace(stages=[])
        assert tracker._determine_successful_tier(result) == "CHEAP"

    def test_determine_successful_tier_premium(self, tmp_path):
        """Test _determine_successful_tier picks highest tier."""
        tracker = WorkflowTierTracker("test", "desc", patterns_dir=tmp_path)
        stages = [
            SimpleNamespace(tier=SimpleNamespace(value="cheap")),
            SimpleNamespace(tier=SimpleNamespace(value="premium")),
        ]
        result = SimpleNamespace(stages=stages)
        assert tracker._determine_successful_tier(result) == "PREMIUM"


@pytest.mark.unit
class TestAutoRecommendTier:
    """Test auto_recommend_tier helper."""

    @patch("attune.workflows.tier_tracking.WorkflowTierTracker.show_recommendation")
    def test_returns_recommendation(self, mock_rec):
        """Test auto_recommend_tier delegates to tracker."""
        mock_rec.return_value = "CAPABLE"
        tier = auto_recommend_tier("wf", "desc", ["a.py"])
        assert tier == "CAPABLE"
        mock_rec.assert_called_once_with(["a.py"], show_ui=False)
