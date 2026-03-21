"""Tests for the voice next-steps engine."""

from unittest.mock import MagicMock, patch

from attune.voice.next_steps import get_next_steps
from attune.workflows.data_classes import NextAction


def _mock_result(success: bool = True) -> MagicMock:
    """Create a minimal mock workflow result."""
    result = MagicMock()
    result.success = success
    result.final_output = {"formatted_report": "test"}
    result.error = None
    result.error_type = None
    result.transient = False
    return result


class TestGetNextSteps:
    """Test the main get_next_steps function."""

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="coverage is low",
                reasoning="test",
                priority="medium",
                confidence=0.8,
            ),
        ],
    )
    @patch("attune.voice.next_steps._get_spec_suggestions", return_value=[])
    def test_returns_voiced_strings(self, _spec, _raw):
        """Next steps are returned as natural-language strings."""
        result = _mock_result()
        steps = get_next_steps("code-review", result)
        assert len(steps) == 1
        assert "test-gen" in steps[0]
        assert "coverage is low" in steps[0]

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="a",
                reasoning="r",
            ),
            NextAction(
                workflow_name="security-audit",
                description="b",
                reasoning="r",
            ),
            NextAction(
                workflow_name="perf-audit",
                description="c",
                reasoning="r",
            ),
            NextAction(
                workflow_name="refactor-plan",
                description="d",
                reasoning="r",
            ),
        ],
    )
    @patch("attune.voice.next_steps._get_spec_suggestions", return_value=[])
    def test_respects_max_steps(self, _spec, _raw):
        """Limits output to max_steps."""
        steps = get_next_steps("code-review", _mock_result(), max_steps=2)
        assert len(steps) == 2

    @patch("attune.voice.next_steps._get_raw_suggestions", return_value=[])
    @patch("attune.voice.next_steps._get_spec_suggestions", return_value=[])
    def test_empty_when_no_suggestions(self, _spec, _raw):
        """Returns empty list when no suggestions available."""
        steps = get_next_steps("code-review", _mock_result())
        assert steps == []

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="from engine",
                reasoning="r",
            ),
        ],
    )
    @patch(
        "attune.voice.next_steps._get_spec_suggestions",
        return_value=[
            NextAction(
                workflow_name="security-audit",
                description="from spec",
                reasoning="r",
                priority="high",
                confidence=0.9,
            ),
        ],
    )
    def test_spec_suggestions_prepended(self, _spec, _raw):
        """Spec suggestions appear before engine suggestions."""
        steps = get_next_steps("code-review", _mock_result())
        assert len(steps) == 2
        assert "security-audit" in steps[0]
        assert "test-gen" in steps[1]

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="from engine",
                reasoning="r",
            ),
        ],
    )
    @patch(
        "attune.voice.next_steps._get_spec_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="from spec",
                reasoning="r",
            ),
        ],
    )
    def test_deduplicates_by_workflow_name(self, _spec, _raw):
        """Duplicate workflow names are deduplicated (spec wins)."""
        steps = get_next_steps("code-review", _mock_result())
        assert len(steps) == 1
        assert "from spec" in steps[0]


class TestGetNextStepsCompact:
    """Test compact mode (replaces get_next_steps_short)."""

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="gaps found",
                reasoning="r",
            ),
        ],
    )
    def test_compact_uses_short_phrasing(self, _raw):
        """Compact mode uses shorter phrasing."""
        result = _mock_result()
        steps = get_next_steps("code-review", result, compact=True)
        assert len(steps) == 1
        # Short phrasing uses "Try" not "I'd run"
        assert "Try" in steps[0]

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(workflow_name="a", description="x", reasoning="r"),
            NextAction(workflow_name="b", description="y", reasoning="r"),
            NextAction(workflow_name="c", description="z", reasoning="r"),
        ],
    )
    def test_compact_default_max_steps(self, _raw):
        """Compact with max_steps=2 limits output."""
        steps = get_next_steps(
            "code-review",
            _mock_result(),
            max_steps=2,
            compact=True,
        )
        assert len(steps) == 2

    @patch(
        "attune.voice.next_steps._get_raw_suggestions",
        return_value=[
            NextAction(
                workflow_name="test-gen",
                description="x",
                reasoning="r",
            ),
        ],
    )
    @patch(
        "attune.voice.next_steps._get_spec_suggestions",
        return_value=[
            NextAction(
                workflow_name="security-audit",
                description="from spec",
                reasoning="r",
            ),
        ],
    )
    def test_compact_skips_spec_suggestions(self, _spec, _raw):
        """Compact mode does not include spec suggestions."""
        steps = get_next_steps(
            "code-review",
            _mock_result(),
            compact=True,
        )
        assert len(steps) == 1
        assert "test-gen" in steps[0]
        # spec suggestion should NOT appear
        assert all("security-audit" not in s for s in steps)
