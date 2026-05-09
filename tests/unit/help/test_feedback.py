"""Tests for attune.help.feedback module — coverage for previously-missed branches.

Targets:
- _load_feedback corrupted JSON handler (lines 46-48)
- record_template_feedback unknown rating (line 91->94)
- get_template_confidence empty entry → 1.0 (line 128)
- search_by_tag with sort_by_usage + weights (lines 212-214)
- list_tags with sort_by_usage + weights (lines 241-248)
- get_workflow_help skips populate==None (line 299->297)
- get_precursor_warnings no candidates → [] (line 350)
- get_precursor_warnings populate==None branch (line 362->360)

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.help.feedback import (
    _load_feedback,
    get_precursor_warnings,
    get_template_confidence,
    get_workflow_help,
    list_tags,
    record_template_feedback,
    search_by_tag,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_cross_links(gen_dir: Path, data: dict) -> None:
    """Write cross_links.json with given data and clear the cache."""
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "cross_links.json").write_text(json.dumps(data), encoding="utf-8")
    # Clear cross_links cache so test changes are picked up
    from attune.help import templates as _t

    with _t._CROSS_LINKS_LOCK:
        _t._CROSS_LINKS_CACHE.clear()


# ---------------------------------------------------------------------------
# _load_feedback / record_template_feedback / get_template_confidence
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadFeedbackErrorHandling:
    """Cover lines 46-48: corrupted feedback.json yields {}."""

    def test_corrupted_json_returns_empty(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        (gen / "feedback.json").write_text("{not valid")
        result = _load_feedback(gen)
        assert result == {}

    def test_missing_file_returns_empty(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        assert _load_feedback(gen) == {}


@pytest.mark.unit
class TestRecordFeedbackUnknownRating:
    """Cover line 91->94: rating that's neither 'good' nor 'bad'."""

    def test_unknown_rating_does_not_increment(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        confidence = record_template_feedback(
            "tpl-1",
            rating="meh",
            generated_dir=gen,
        )
        # New entry created with both 0; confidence falls back to 1.0
        assert confidence == 1.0

        feedback_data = json.loads((gen / "feedback.json").read_text())
        assert feedback_data["tpl-1"] == {"good": 0, "bad": 0}

    def test_good_rating_increments(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        c1 = record_template_feedback("tpl-1", rating="good", generated_dir=gen)
        assert c1 == 1.0  # 1/1
        c2 = record_template_feedback("tpl-1", rating="bad", generated_dir=gen)
        assert c2 == 0.5  # 1/2


@pytest.mark.unit
class TestGetTemplateConfidenceEmptyEntry:
    """Cover line 128: entry exists but good+bad == 0."""

    def test_empty_entry_returns_one(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        (gen / "feedback.json").write_text(
            json.dumps({"tpl-x": {"good": 0, "bad": 0}}),
        )
        assert get_template_confidence("tpl-x", generated_dir=gen) == 1.0

    def test_nonexistent_entry_returns_one(self, tmp_path: Path):
        gen = tmp_path / "generated"
        gen.mkdir()
        assert get_template_confidence("absent", generated_dir=gen) == 1.0


# ---------------------------------------------------------------------------
# search_by_tag with sort_by_usage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchByTagSortByUsage:
    """Cover lines 212-214: sort_by_usage=True with non-empty weights."""

    def test_sorted_by_usage_descending(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"tag_index": {"py": ["err-low", "err-high", "err-mid"]}},
        )

        with patch(
            "attune.help.feedback.get_usage_weights",
            return_value={"err-high": 1.0, "err-mid": 0.5, "err-low": 0.1},
        ):
            results = search_by_tag("py", generated_dir=gen, sort_by_usage=True)

        assert results == ["err-high", "err-mid", "err-low"]

    def test_sort_by_usage_no_weights_returns_unsorted(self, tmp_path: Path):
        """When weights is empty dict, original order is preserved."""
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"tag_index": {"py": ["err-a", "err-b"]}},
        )

        with patch("attune.help.feedback.get_usage_weights", return_value={}):
            results = search_by_tag("py", generated_dir=gen, sort_by_usage=True)

        assert results == ["err-a", "err-b"]

    def test_no_results_short_circuits(self, tmp_path: Path):
        """Empty results don't trigger weight lookup."""
        gen = tmp_path / "generated"
        _setup_cross_links(gen, {"tag_index": {"py": []}})

        with patch("attune.help.feedback.get_usage_weights") as mock_weights:
            results = search_by_tag("py", generated_dir=gen, sort_by_usage=True)

        assert results == []
        mock_weights.assert_not_called()


# ---------------------------------------------------------------------------
# list_tags with sort_by_usage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListTagsSortByUsage:
    """Cover lines 241-248: list_tags sort_by_usage with non-empty weights."""

    def test_tags_sorted_by_aggregate_weight(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {
                "tag_index": {
                    "low": ["a"],
                    "high": ["b", "c"],
                    "mid": ["d"],
                },
            },
        )

        with patch(
            "attune.help.feedback.get_usage_weights",
            return_value={"a": 0.1, "b": 0.9, "c": 0.9, "d": 0.5},
        ):
            tags = list_tags(generated_dir=gen, sort_by_usage=True)

        # Aggregate weights: high=1.8, mid=0.5, low=0.1 → sorted descending
        assert list(tags.keys()) == ["high", "mid", "low"]
        assert tags == {"high": 2, "mid": 1, "low": 1}

    def test_sort_by_usage_no_weights_falls_back_to_count_sort(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"tag_index": {"x": ["a"], "y": ["b", "c"]}},
        )

        with patch("attune.help.feedback.get_usage_weights", return_value={}):
            tags = list_tags(generated_dir=gen, sort_by_usage=True)

        # Falls through to count-based sort
        assert tags["y"] == 2
        assert tags["x"] == 1


# ---------------------------------------------------------------------------
# get_workflow_help — populate returns None branch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetWorkflowHelpPopulateNone:
    """Cover line 299->297: populate returning None is skipped."""

    def test_populate_none_results_skipped(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"workflow_map": {"my-flow": ["tpl-real", "tpl-missing", "tpl-also-real"]}},
        )

        # Populate returns None for "tpl-missing", real PopulatedTemplate otherwise
        from attune.help.templates import PopulatedTemplate

        def fake_populate(tid, audience=None, generated_dir=None):
            if tid == "tpl-missing":
                return None
            return PopulatedTemplate(
                template_id=tid,
                type="tip",
                subtype="practice",
                name=tid,
                title=f"Title {tid}",
                body="body",
                sections={},
                tags=[],
                related=[],
                confidence="High",
                source="test",
            )

        with patch("attune.help.feedback.populate", side_effect=fake_populate):
            results = get_workflow_help(
                "my-flow",
                generated_dir=gen,
                max_results=10,
            )

        # Only the 2 non-None results returned
        assert len(results) == 2
        assert {r.template_id for r in results} == {"tpl-real", "tpl-also-real"}

    def test_no_workflow_match_returns_empty(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(gen, {"workflow_map": {}})

        results = get_workflow_help("nope", generated_dir=gen)
        assert results == []


# ---------------------------------------------------------------------------
# get_precursor_warnings — no candidates / populate None branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrecursorWarnings:
    """Cover lines 350 (no candidates) and 362->360 (populate None)."""

    def test_no_warning_or_error_candidates_returns_empty(self, tmp_path: Path):
        """If matching tags exist but no template IDs start with war-/err-, → []."""
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"tag_index": {"python": ["tip-something", "ref-other"]}},
        )

        results = get_precursor_warnings("foo.py", generated_dir=gen)
        assert results == []

    def test_unknown_extension_returns_empty(self, tmp_path: Path):
        gen = tmp_path / "generated"
        _setup_cross_links(gen, {"tag_index": {}})
        assert get_precursor_warnings("foo.unknown", generated_dir=gen) == []

    def test_populate_none_skipped(self, tmp_path: Path):
        """If populate returns None for a candidate, it's silently skipped."""
        gen = tmp_path / "generated"
        _setup_cross_links(
            gen,
            {"tag_index": {"python": ["err-real", "err-missing"]}},
        )

        from attune.help.templates import PopulatedTemplate

        def fake_populate(tid, audience=None, generated_dir=None):
            if tid == "err-missing":
                return None
            return PopulatedTemplate(
                template_id=tid,
                type="error",
                subtype="import",
                name=tid,
                title="t",
                body="b",
                sections={},
                tags=[],
                related=[],
                confidence="High",
                source="test",
            )

        with patch("attune.help.feedback.populate", side_effect=fake_populate):
            results = get_precursor_warnings("foo.py", generated_dir=gen)

        assert len(results) == 1
        assert results[0].template_id == "err-real"
