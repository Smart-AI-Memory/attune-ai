"""Behavioral tests for evaluate_session.py SessionEnd hook script.

Covers the three public entry points plus the ``__main__`` banner:

- ``run_evaluate_session`` — guard for missing state, user_id derivation,
  the no-extraction branch, the extraction-with-patterns branch (storage +
  capped summaries), the extraction-with-no-patterns branch, min_score
  pass-through, and the catch-all error path.
- ``get_learning_summary`` — missing user_id, happy path, error path.
- ``apply_learned_patterns`` — missing user_id, formatting, category-filter
  parsing, and the catch-all empty-string error path.
- The ``__main__`` informational banner.

The hook imports its collaborators lazily from ``attune.learning``; tests
patch those names there and feed real ``EvaluationResult`` /
``ExtractedPattern`` dataclasses so the hook's branching logic runs against
genuine data structures rather than opaque mocks.
"""

from __future__ import annotations

import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from attune.hooks.scripts import evaluate_session as hook
from attune.learning.evaluator import (
    EvaluationResult,
    SessionMetrics,
    SessionQuality,
)
from attune.learning.extractor import ExtractedPattern, PatternCategory

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "evaluate_session.py"
)


# --------------------------------------------------------------------------- #
# Builders for real result objects
# --------------------------------------------------------------------------- #


def make_evaluation(
    *,
    quality: SessionQuality = SessionQuality.GOOD,
    score: float = 0.75,
    topics: list[str] | None = None,
    recommended: bool = False,
    reasoning: str = "looks learnable",
) -> EvaluationResult:
    return EvaluationResult(
        quality=quality,
        score=score,
        metrics=SessionMetrics(interaction_count=5),
        learnable_topics=topics if topics is not None else ["debugging"],
        recommended_extraction=recommended,
        reasoning=reasoning,
    )


def make_pattern(trigger: str = "error appeared", confidence: float = 0.8) -> ExtractedPattern:
    return ExtractedPattern(
        category=PatternCategory.ERROR_RESOLUTION,
        trigger=trigger,
        context="while running tests",
        resolution="pinned the dependency",
        confidence=confidence,
        source_session="sess-1",
    )


class FakeEvaluator:
    """Stand-in for SessionEvaluator that returns a preset evaluation."""

    last_kwargs: dict = {}

    def __init__(self, **kwargs):
        FakeEvaluator.last_kwargs = kwargs
        self._result = FakeEvaluator.result

    def evaluate(self, state):
        FakeEvaluator.evaluated_state = state
        return self._result


class FakeExtractor:
    """Stand-in for PatternExtractor returning preset patterns."""

    def __init__(self, **kwargs):
        pass

    def extract_patterns(self, state, session_id):
        FakeExtractor.session_id = session_id
        return FakeExtractor.patterns


class FakeStorage:
    """Stand-in for LearnedSkillsStorage capturing calls."""

    def __init__(self, storage_dir=None):
        FakeStorage.storage_dir = storage_dir

    def save_patterns(self, user_id, patterns):
        FakeStorage.saved = (user_id, patterns)
        return [p.pattern_id for p in patterns]

    def get_summary(self, user_id):
        FakeStorage.summary_user = user_id
        return {"user_id": user_id, "total": 3}

    def format_patterns_for_context(self, user_id, max_patterns=5, categories=None):
        FakeStorage.format_args = (user_id, max_patterns, categories)
        return f"# Patterns for {user_id}"


@pytest.fixture
def patched_learning():
    """Patch the three lazily-imported collaborators on attune.learning."""
    FakeEvaluator.result = make_evaluation()
    FakeExtractor.patterns = []
    with (
        patch("attune.learning.SessionEvaluator", FakeEvaluator),
        patch("attune.learning.PatternExtractor", FakeExtractor),
        patch("attune.learning.LearnedSkillsStorage", FakeStorage),
    ):
        yield


# --------------------------------------------------------------------------- #
# run_evaluate_session
# --------------------------------------------------------------------------- #


def test_missing_collaboration_state_returns_error():
    result = hook.run_evaluate_session({})

    assert result == {
        "evaluated": False,
        "error": "No collaboration state provided",
    }


def test_derives_user_id_from_state_when_not_in_context(patched_learning):
    FakeEvaluator.result = make_evaluation(recommended=True)
    FakeExtractor.patterns = [make_pattern()]
    state = SimpleNamespace(user_id="from-state")

    result = hook.run_evaluate_session({"collaboration_state": state})

    assert result["evaluated"] is True
    # storage.save_patterns was called with the user_id derived from state
    assert FakeStorage.saved[0] == "from-state"


def test_evaluated_without_extraction_passes_through_fields(patched_learning):
    FakeEvaluator.result = make_evaluation(
        quality=SessionQuality.AVERAGE,
        score=0.3,
        topics=["a", "b"],
        recommended=False,
        reasoning="meh",
    )
    state = SimpleNamespace(user_id="u1")

    result = hook.run_evaluate_session({"collaboration_state": state, "user_id": "u1"})

    assert result["evaluated"] is True
    assert result["quality"] == "average"
    assert result["score"] == 0.3
    assert result["learnable_topics"] == ["a", "b"]
    assert result["reasoning"] == "meh"
    assert result["patterns_extracted"] == 0
    assert result["patterns_stored"] == 0
    assert "pattern_summaries" not in result


def test_extraction_with_patterns_stores_and_summarizes(patched_learning):
    FakeEvaluator.result = make_evaluation(recommended=True)
    FakeExtractor.patterns = [
        make_pattern(trigger="t1"),
        make_pattern(trigger="t2"),
    ]
    state = SimpleNamespace(user_id="u1")

    result = hook.run_evaluate_session(
        {"collaboration_state": state, "user_id": "u1", "session_id": "sess-X"}
    )

    assert result["patterns_extracted"] == 2
    assert result["patterns_stored"] == 2
    assert len(result["pattern_summaries"]) == 2
    first = result["pattern_summaries"][0]
    assert set(first) == {"id", "category", "trigger", "confidence"}
    assert first["category"] == "error_resolution"
    assert FakeExtractor.session_id == "sess-X"


def test_pattern_summaries_capped_at_five(patched_learning):
    FakeEvaluator.result = make_evaluation(recommended=True)
    FakeExtractor.patterns = [make_pattern(trigger=f"t{i}") for i in range(7)]
    state = SimpleNamespace(user_id="u1")

    result = hook.run_evaluate_session({"collaboration_state": state, "user_id": "u1"})

    assert result["patterns_extracted"] == 7
    assert result["patterns_stored"] == 7
    assert len(result["pattern_summaries"]) == 5  # capped


def test_recommended_extraction_but_no_patterns_skips_storage(patched_learning):
    FakeEvaluator.result = make_evaluation(recommended=True)
    FakeExtractor.patterns = []  # extractor finds nothing
    FakeStorage.saved = None
    state = SimpleNamespace(user_id="u1")

    result = hook.run_evaluate_session({"collaboration_state": state, "user_id": "u1"})

    assert result["patterns_extracted"] == 0
    assert result["patterns_stored"] == 0
    assert "pattern_summaries" not in result
    assert FakeStorage.saved is None  # save_patterns never called


def test_min_score_forwarded_to_evaluator(patched_learning):
    FakeEvaluator.result = make_evaluation()
    state = SimpleNamespace(user_id="u1")

    hook.run_evaluate_session({"collaboration_state": state, "user_id": "u1", "min_score": 0.9})

    assert FakeEvaluator.last_kwargs == {"min_score_for_extraction": 0.9}


def test_storage_dir_forwarded(patched_learning):
    FakeEvaluator.result = make_evaluation(recommended=True)
    FakeExtractor.patterns = [make_pattern()]
    state = SimpleNamespace(user_id="u1")

    hook.run_evaluate_session(
        {
            "collaboration_state": state,
            "user_id": "u1",
            "storage_dir": "/tmp/custom_skills",
        }
    )

    assert FakeStorage.storage_dir == "/tmp/custom_skills"


def test_exception_during_evaluation_returns_error(patched_learning):
    def boom(self, state):
        raise RuntimeError("evaluator exploded")

    state = SimpleNamespace(user_id="u1")
    with patch.object(FakeEvaluator, "evaluate", boom):
        result = hook.run_evaluate_session({"collaboration_state": state, "user_id": "u1"})

    assert result["evaluated"] is False
    assert "evaluator exploded" in result["error"]


# --------------------------------------------------------------------------- #
# get_learning_summary
# --------------------------------------------------------------------------- #


def test_get_learning_summary_missing_user_id():
    assert hook.get_learning_summary({}) == {"error": "No user_id provided"}


def test_get_learning_summary_returns_storage_summary(patched_learning):
    result = hook.get_learning_summary({"user_id": "u7", "storage_dir": "/tmp/skills"})

    assert result == {"user_id": "u7", "total": 3}
    assert FakeStorage.storage_dir == "/tmp/skills"
    assert FakeStorage.summary_user == "u7"


def test_get_learning_summary_handles_exception():
    def boom(self, user_id):
        raise OSError("disk gone")

    with (
        patch("attune.learning.LearnedSkillsStorage", FakeStorage),
        patch.object(FakeStorage, "get_summary", boom),
    ):
        result = hook.get_learning_summary({"user_id": "u1"})

    assert "disk gone" in result["error"]


# --------------------------------------------------------------------------- #
# apply_learned_patterns
# --------------------------------------------------------------------------- #


def test_apply_learned_patterns_missing_user_id_returns_empty():
    assert hook.apply_learned_patterns({}) == ""


def test_apply_learned_patterns_formats_without_filter(patched_learning):
    out = hook.apply_learned_patterns({"user_id": "u1", "max_patterns": 3})

    assert out == "# Patterns for u1"
    user_id, max_patterns, categories = FakeStorage.format_args
    assert (user_id, max_patterns) == ("u1", 3)
    assert categories is None


def test_apply_learned_patterns_parses_category_filter(patched_learning):
    hook.apply_learned_patterns({"user_id": "u1", "categories": ["preference", "workaround"]})

    _, _, categories = FakeStorage.format_args
    assert categories == [PatternCategory.PREFERENCE, PatternCategory.WORKAROUND]


def test_apply_learned_patterns_bad_category_returns_empty(patched_learning):
    # An unknown category string makes PatternCategory(...) raise ValueError,
    # which the catch-all converts into the empty-string fallback.
    out = hook.apply_learned_patterns({"user_id": "u1", "categories": ["not-a-real-category"]})

    assert out == ""


# --------------------------------------------------------------------------- #
# __main__ banner
# --------------------------------------------------------------------------- #


def test_main_banner_prints_usage(capsys):
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

    out = capsys.readouterr().out
    assert "Evaluate Session Hook Script" in out
    assert "collaboration_state" in out
    assert "min_score" in out
