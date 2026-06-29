"""Tests for get_usage_weights in attune.help.feedback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetUsageWeightsImportFailure:
    """Tests for get_usage_weights when telemetry is unavailable."""

    def test_returns_empty_on_import_error(self):
        """Returns empty dict when UsageTracker import fails."""
        from attune.help.feedback import get_usage_weights

        with (
            patch(
                "attune.help.feedback.UsageTracker",
                side_effect=ImportError("no telemetry"),
                create=True,
            ),
            patch.dict("sys.modules", {"attune.telemetry.usage_tracker": None}),
        ):
            # Force import failure by patching the lazy import
            with patch(
                "builtins.__import__",
                side_effect=ImportError("no telemetry"),
            ):
                result = get_usage_weights()

        assert result == {}

    def test_returns_empty_on_tracker_exception(self):
        """Returns empty dict when tracker.get_stats raises."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.side_effect = RuntimeError("boom")

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        with patch.dict(
            "sys.modules",
            {"attune.telemetry.usage_tracker": mock_module},
        ):
            result = get_usage_weights()

        assert result == {}


class TestGetUsageWeightsEmpty:
    """Tests when telemetry returns no data."""

    def test_empty_by_workflow(self):
        """Returns empty dict when by_workflow is empty."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"by_workflow": {}}

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        with patch.dict(
            "sys.modules",
            {"attune.telemetry.usage_tracker": mock_module},
        ):
            result = get_usage_weights()

        assert result == {}

    def test_zero_max_cost(self):
        """Returns empty dict when all costs are zero."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {
                "security-audit": {"total_cost": 0},
                "code-review": {"total_cost": 0},
            }
        }

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        with patch.dict(
            "sys.modules",
            {"attune.telemetry.usage_tracker": mock_module},
        ):
            result = get_usage_weights()

        assert result == {}


class TestGetUsageWeightsNormalization:
    """Tests for weight normalization logic."""

    def test_highest_cost_gets_weight_one(self, tmp_path):
        """Workflow with highest cost gets weight 1.0."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {
                "security-audit": {"total_cost": 10.0},
                "code-review": {"total_cost": 5.0},
            }
        }

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        # Mock cross_links to map workflows to template IDs
        cross_links = {
            "workflow_map": {
                "security-audit": ["war-ssrf", "tip-path-validation"],
                "code-review": ["tip-review-checklist"],
            },
            "tag_index": {},
        }

        with (
            patch.dict(
                "sys.modules",
                {"attune.telemetry.usage_tracker": mock_module},
            ),
            patch(
                "attune.help.feedback._load_cross_links",
                return_value=cross_links,
            ),
        ):
            result = get_usage_weights()

        # security-audit has highest cost -> weight 1.0
        assert result["war-ssrf"] == pytest.approx(1.0)
        assert result["tip-path-validation"] == pytest.approx(1.0)
        # code-review has half the cost -> weight 0.5
        assert result["tip-review-checklist"] == pytest.approx(0.5)

    def test_days_forwarded_to_tracker(self):
        """Custom days parameter is forwarded to tracker."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"by_workflow": {}}

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        with patch.dict(
            "sys.modules",
            {"attune.telemetry.usage_tracker": mock_module},
        ):
            get_usage_weights(days=7)

        mock_tracker.get_stats.assert_called_once_with(days=7)

    def test_scalar_workflow_values(self):
        """Handles by_workflow values that are scalars (not dicts)."""
        from attune.help.feedback import get_usage_weights

        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {
            "by_workflow": {
                "security-audit": 10.0,
                "code-review": 5.0,
            }
        }

        mock_module = MagicMock()
        mock_module.UsageTracker.get_instance.return_value = mock_tracker

        cross_links = {
            "workflow_map": {
                "security-audit": ["war-ssrf"],
            },
            "tag_index": {},
        }

        with (
            patch.dict(
                "sys.modules",
                {"attune.telemetry.usage_tracker": mock_module},
            ),
            patch(
                "attune.help.feedback._load_cross_links",
                return_value=cross_links,
            ),
        ):
            result = get_usage_weights()

        assert result["war-ssrf"] == pytest.approx(1.0)
