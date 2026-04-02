"""Tests for _suggestions_from_help() in attune.workflows.suggestions.

Verifies that help system templates are correctly converted
into NextAction suggestions with the expected field values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

from attune.workflows.data_classes import NextAction


@dataclass
class _FakeTemplate:
    """Minimal stand-in for PopulatedTemplate with a .title attribute."""

    template_id: str = "ref-001"
    title: str = "Fake Title"
    body: str = ""
    type: str = "reference"
    subtype: str = ""
    name: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    related: list[dict[str, str]] = field(default_factory=list)
    confidence: str = "high"
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def _import_suggestions_from_help():
    """Import the function under test.

    Returns:
        The _suggestions_from_help callable.
    """
    from attune.workflows.suggestions import _suggestions_from_help

    return _suggestions_from_help


class TestSuggestionsFromHelpEmpty:
    """Tests for the empty-result path."""

    @patch("attune.help.engine.get_workflow_help", return_value=[])
    def test_returns_empty_list_when_no_templates(self, mock_help):
        """Return empty list when get_workflow_help yields nothing."""
        func = _import_suggestions_from_help()
        result = func("security-audit")

        assert result == []
        mock_help.assert_called_once_with("security-audit", max_results=2)

    @patch("attune.help.engine.get_workflow_help", return_value=None)
    def test_returns_empty_list_when_none(self, mock_help):
        """Return empty list when get_workflow_help returns None."""
        func = _import_suggestions_from_help()
        result = func("code-review")

        assert result == []


class TestSuggestionsFromHelpSingle:
    """Tests with a single help template result."""

    @patch("attune.help.engine.get_workflow_help")
    def test_returns_one_next_action(self, mock_help):
        """Return exactly one NextAction for one template."""
        mock_help.return_value = [_FakeTemplate(title="Security Overview")]
        func = _import_suggestions_from_help()

        result = func("security-audit")

        assert len(result) == 1
        assert isinstance(result[0], NextAction)

    @patch("attune.help.engine.get_workflow_help")
    def test_workflow_name_prefixed_with_learn(self, mock_help):
        """NextAction.workflow_name is 'learn-' + original workflow name."""
        mock_help.return_value = [_FakeTemplate(title="Guide")]
        func = _import_suggestions_from_help()

        result = func("code-review")

        assert result[0].workflow_name == "learn-code-review"

    @patch("attune.help.engine.get_workflow_help")
    def test_description_contains_template_title(self, mock_help):
        """NextAction.description includes the template's title."""
        mock_help.return_value = [_FakeTemplate(title="Path Traversal Guide")]
        func = _import_suggestions_from_help()

        result = func("security-audit")

        assert "Path Traversal Guide" in result[0].description
        assert result[0].description == "Learn more: Path Traversal Guide"

    @patch("attune.help.engine.get_workflow_help")
    def test_priority_is_low(self, mock_help):
        """Help suggestions always have low priority."""
        mock_help.return_value = [_FakeTemplate(title="Title")]
        func = _import_suggestions_from_help()

        result = func("bug-predict")

        assert result[0].priority == "low"

    @patch("attune.help.engine.get_workflow_help")
    def test_confidence_is_half(self, mock_help):
        """Help suggestions have 0.5 confidence."""
        mock_help.return_value = [_FakeTemplate(title="Title")]
        func = _import_suggestions_from_help()

        result = func("deep-review")

        assert result[0].confidence == 0.5

    @patch("attune.help.engine.get_workflow_help")
    def test_reasoning_mentions_workflow_name(self, mock_help):
        """Reasoning text references the completed workflow."""
        mock_help.return_value = [_FakeTemplate(title="Title")]
        func = _import_suggestions_from_help()

        result = func("test-gen")

        assert "test-gen" in result[0].reasoning

    @patch("attune.help.engine.get_workflow_help")
    def test_reasoning_contains_learn_hint(self, mock_help):
        """Reasoning text tells user about /learn command."""
        mock_help.return_value = [_FakeTemplate(title="Title")]
        func = _import_suggestions_from_help()

        result = func("test-gen")

        assert "/learn" in result[0].reasoning


class TestSuggestionsFromHelpMultiple:
    """Tests with multiple help template results."""

    @patch("attune.help.engine.get_workflow_help")
    def test_returns_matching_count(self, mock_help):
        """Return one NextAction per template."""
        mock_help.return_value = [
            _FakeTemplate(title="Overview"),
            _FakeTemplate(title="Advanced"),
        ]
        func = _import_suggestions_from_help()

        result = func("security-audit")

        assert len(result) == 2

    @patch("attune.help.engine.get_workflow_help")
    def test_each_action_has_correct_workflow_name(self, mock_help):
        """All NextActions share the same learn- prefixed workflow name."""
        mock_help.return_value = [
            _FakeTemplate(title="A"),
            _FakeTemplate(title="B"),
        ]
        func = _import_suggestions_from_help()

        result = func("refactor")

        for action in result:
            assert action.workflow_name == "learn-refactor"

    @patch("attune.help.engine.get_workflow_help")
    def test_each_action_has_distinct_description(self, mock_help):
        """Each NextAction description reflects its own template title."""
        mock_help.return_value = [
            _FakeTemplate(title="First Topic"),
            _FakeTemplate(title="Second Topic"),
        ]
        func = _import_suggestions_from_help()

        result = func("code-review")

        descriptions = [a.description for a in result]
        assert "Learn more: First Topic" in descriptions
        assert "Learn more: Second Topic" in descriptions
