"""Unit tests for ReleasePreparationWorkflow (SDK-native).

Tests cover class attributes, construction, re-exports,
and format_release_prep_report().
"""

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.release_prep import (
    RELEASE_PREP_STEPS,
    ReleasePreparationWorkflow,
    format_release_prep_report,
)

# ---------------------------------------------------------------------------
# Class attributes
# ---------------------------------------------------------------------------


class TestWorkflowInstantiation:
    """Tests for ReleasePreparationWorkflow class attributes."""

    @pytest.fixture
    def workflow(self):
        """Create a default ReleasePreparationWorkflow."""
        return ReleasePreparationWorkflow()

    def test_default_instantiation(self, workflow):
        """Default constructor succeeds."""
        assert workflow.name == "release-prep"

    def test_description_mentions_agent_sdk(self, workflow):
        """Description mentions Agent SDK."""
        assert "Agent SDK" in workflow.description

    def test_stages(self, workflow):
        """SDK-native workflow has single agent-prep stage."""
        assert workflow.stages == ["agent-prep"]

    def test_tier_map(self, workflow):
        """Tier map maps agent-prep to CAPABLE."""
        assert workflow.tier_map == {"agent-prep": ModelTier.CAPABLE}


# ---------------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------------


class TestReExports:
    """Test backward-compatibility re-exports."""

    def test_release_prep_steps_importable(self):
        """RELEASE_PREP_STEPS constant is importable."""
        assert isinstance(RELEASE_PREP_STEPS, dict)
        assert len(RELEASE_PREP_STEPS) > 0

    def test_format_release_prep_report_callable(self):
        """format_release_prep_report is callable."""
        assert callable(format_release_prep_report)

    def test_main_importable(self):
        """main function is importable."""
        from attune.workflows.release_prep import main

        assert callable(main)


# ---------------------------------------------------------------------------
# format_release_prep_report
# ---------------------------------------------------------------------------


class TestFormatReleasePrepReport:
    """Tests for format_release_prep_report."""

    def test_returns_string(self):
        """Report formatter returns a string."""
        result_data = {
            "approved": True,
            "recommendation": "Ship it",
            "blockers": [],
        }
        input_data = {
            "health": {"passed": True, "health_score": 100, "failed_checks": []},
            "security": {"vulnerabilities": []},
            "changelog": {"total_commits": 5, "entries": []},
        }
        report = format_release_prep_report(result_data, input_data)
        assert isinstance(report, str)

    def test_handles_missing_keys(self):
        """Report formatter handles empty dicts gracefully."""
        report = format_release_prep_report({}, {})
        assert isinstance(report, str)
