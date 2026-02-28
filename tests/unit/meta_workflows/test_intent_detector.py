"""Tests for intent_detector module.

Covers IntentMatch, IntentDetector, and helper functions.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.meta_workflows.intent_detector import (
    INTENT_PATTERNS,
    IntentDetector,
    IntentMatch,
    auto_detect_template,
    detect_and_suggest,
)


@pytest.mark.unit
class TestIntentMatch:
    """Tests for IntentMatch dataclass."""

    def test_basic_creation(self):
        """Test creating a basic IntentMatch."""
        match = IntentMatch(
            template_id="release-prep",
            template_name="Release Preparation",
            confidence=0.8,
        )

        assert match.template_id == "release-prep"
        assert match.template_name == "Release Preparation"
        assert match.confidence == 0.8
        assert match.matched_keywords == []
        assert match.description == ""

    def test_full_creation(self):
        """Test creating IntentMatch with all fields."""
        match = IntentMatch(
            template_id="test-coverage-boost",
            template_name="Test Coverage Boost",
            confidence=0.95,
            matched_keywords=["test", "coverage", "improve"],
            description="Improve test coverage across your codebase",
        )

        assert match.confidence == 0.95
        assert len(match.matched_keywords) == 3
        assert "coverage" in match.matched_keywords


@pytest.mark.unit
class TestIntentPatterns:
    """Tests for INTENT_PATTERNS constant."""

    def test_release_prep_patterns(self):
        """Test release-prep patterns exist."""
        assert "release-prep" in INTENT_PATTERNS
        patterns = INTENT_PATTERNS["release-prep"]

        assert "keywords" in patterns
        assert "phrases" in patterns
        assert "release" in patterns["keywords"]

    def test_test_coverage_patterns(self):
        """Test test-coverage-boost patterns exist."""
        assert "test-coverage-boost" in INTENT_PATTERNS
        patterns = INTENT_PATTERNS["test-coverage-boost"]

        assert "coverage" in patterns["keywords"]
        assert "generate tests" in patterns["keywords"]

    def test_test_maintenance_patterns(self):
        """Test test-maintenance patterns exist."""
        assert "test-maintenance" in INTENT_PATTERNS
        patterns = INTENT_PATTERNS["test-maintenance"]

        assert "flaky tests" in patterns["keywords"]

    def test_manage_docs_patterns(self):
        """Test manage-docs patterns exist."""
        assert "manage-docs" in INTENT_PATTERNS
        patterns = INTENT_PATTERNS["manage-docs"]

        assert "documentation" in patterns["keywords"]


@pytest.mark.unit
class TestIntentDetectorInit:
    """Tests for IntentDetector initialization."""

    def test_init(self):
        """Test IntentDetector initialization."""
        detector = IntentDetector()

        assert detector.patterns == INTENT_PATTERNS
        assert len(detector.templates) > 0


@pytest.mark.unit
class TestIntentDetectorDetect:
    """Tests for IntentDetector.detect method."""

    def test_detect_release_intent(self):
        """Test detecting release-related intent."""
        detector = IntentDetector()

        matches = detector.detect("I need to prepare for a release")

        assert len(matches) > 0
        assert matches[0].template_id == "release-prep"
        assert matches[0].confidence > 0.3

    def test_detect_test_coverage_intent(self):
        """Test detecting test coverage intent."""
        detector = IntentDetector()

        matches = detector.detect("I want to improve my test coverage")

        assert len(matches) > 0
        top_match = matches[0]
        assert top_match.template_id == "test-coverage-boost"

    def test_detect_documentation_intent(self):
        """Test detecting documentation intent."""
        detector = IntentDetector()

        matches = detector.detect("I need to update the documentation")

        assert len(matches) > 0
        # Should match manage-docs
        template_ids = [m.template_id for m in matches]
        assert "manage-docs" in template_ids

    def test_detect_with_threshold(self):
        """Test that threshold filters low-confidence matches."""
        detector = IntentDetector()

        # High threshold should return fewer matches
        high_threshold_matches = detector.detect("test", threshold=0.8)
        low_threshold_matches = detector.detect("test", threshold=0.1)

        assert len(high_threshold_matches) <= len(low_threshold_matches)

    def test_detect_empty_input(self):
        """Test detecting with empty input."""
        detector = IntentDetector()

        matches = detector.detect("")

        assert matches == []

    def test_detect_none_input(self):
        """Test detecting with None input."""
        detector = IntentDetector()

        matches = detector.detect(None)

        assert matches == []

    def test_detect_sorted_by_confidence(self):
        """Test that matches are sorted by confidence."""
        detector = IntentDetector()

        matches = detector.detect("release ready deploy tests coverage")

        if len(matches) > 1:
            for i in range(len(matches) - 1):
                assert matches[i].confidence >= matches[i + 1].confidence

    def test_detect_case_insensitive(self):
        """Test that detection is case insensitive."""
        detector = IntentDetector()

        lower_matches = detector.detect("release preparation")
        upper_matches = detector.detect("RELEASE PREPARATION")
        mixed_matches = detector.detect("Release Preparation")

        assert len(lower_matches) == len(upper_matches) == len(mixed_matches)

    def test_detect_includes_matched_keywords(self):
        """Test that matches include matched keywords."""
        detector = IntentDetector()

        matches = detector.detect("I need to release and deploy")

        assert len(matches) > 0
        assert len(matches[0].matched_keywords) > 0


@pytest.mark.unit
class TestIntentDetectorCalculateScore:
    """Tests for _calculate_match_score method."""

    def test_keyword_matching(self):
        """Test keyword matching scoring."""
        detector = IntentDetector()
        pattern_config = {
            "keywords": ["test", "coverage"],
            "phrases": [],
            "weight": 1.0,
        }

        score, keywords = detector._calculate_match_score("improve test coverage", pattern_config)

        assert score > 0
        assert "test" in keywords
        assert "coverage" in keywords

    def test_phrase_matching(self):
        """Test phrase matching scores higher."""
        detector = IntentDetector()
        pattern_config = {
            "keywords": ["release"],
            "phrases": [r"prepare for (a )?release"],
            "weight": 1.0,
        }

        score, keywords = detector._calculate_match_score("prepare for a release", pattern_config)

        assert score > 0.3  # Phrase matching adds 0.3

    def test_weight_multiplier(self):
        """Test weight affects final score."""
        detector = IntentDetector()

        config_normal = {"keywords": ["test"], "phrases": [], "weight": 1.0}
        config_weighted = {"keywords": ["test"], "phrases": [], "weight": 2.0}

        score_normal, _ = detector._calculate_match_score("test", config_normal)
        score_weighted, _ = detector._calculate_match_score("test", config_weighted)

        # Weighted should be higher (but capped at 1.0)
        assert score_weighted >= score_normal

    def test_no_match(self):
        """Test score is 0 with no matches."""
        detector = IntentDetector()
        pattern_config = {
            "keywords": ["xyz123"],
            "phrases": [],
            "weight": 1.0,
        }

        score, keywords = detector._calculate_match_score("nothing matches here", pattern_config)

        assert score == 0
        assert keywords == []


@pytest.mark.unit
class TestIntentDetectorSuggestionText:
    """Tests for get_suggestion_text method."""

    def test_suggestion_text_with_matches(self):
        """Test suggestion text generation."""
        detector = IntentDetector()
        matches = [
            IntentMatch(
                template_id="release-prep",
                template_name="Release Preparation",
                confidence=0.8,
                description="Prepare for release",
            ),
        ]

        text = detector.get_suggestion_text(matches)

        assert "Release Preparation" in text
        assert "80%" in text
        assert "release-prep" in text

    def test_suggestion_text_empty_matches(self):
        """Test suggestion text with no matches."""
        detector = IntentDetector()

        text = detector.get_suggestion_text([])

        assert text == ""

    def test_suggestion_text_limits_to_3(self):
        """Test that suggestion text shows at most 3 matches."""
        detector = IntentDetector()
        matches = [IntentMatch(f"template-{i}", f"Template {i}", 0.9 - i * 0.1) for i in range(5)]

        text = detector.get_suggestion_text(matches)

        # Should only show top 3
        assert "Template 0" in text
        assert "Template 1" in text
        assert "Template 2" in text
        assert "Template 4" not in text


@pytest.mark.unit
class TestIntentDetectorShouldSuggest:
    """Tests for should_suggest method."""

    def test_should_suggest_true(self):
        """Test should_suggest returns True for good match."""
        detector = IntentDetector()

        result = detector.should_suggest("prepare for release", min_confidence=0.3)

        assert result is True

    def test_should_suggest_false_low_confidence(self):
        """Test should_suggest returns False for low confidence."""
        detector = IntentDetector()

        result = detector.should_suggest("hello world", min_confidence=0.9)

        assert result is False


@pytest.mark.unit
class TestIntentDetectorGetBestMatch:
    """Tests for get_best_match method."""

    def test_get_best_match_found(self):
        """Test get_best_match returns best match."""
        detector = IntentDetector()

        match = detector.get_best_match("prepare for a release")

        assert match is not None
        assert match.template_id == "release-prep"

    def test_get_best_match_none(self):
        """Test get_best_match returns None when no good match."""
        detector = IntentDetector()

        match = detector.get_best_match("xyz random gibberish 123")

        assert match is None


@pytest.mark.unit
class TestDetectAndSuggest:
    """Tests for detect_and_suggest function."""

    def test_detect_and_suggest_with_match(self):
        """Test detect_and_suggest with matching input."""
        result = detect_and_suggest("I need to improve test coverage")

        assert result != ""
        assert "test" in result.lower() or "coverage" in result.lower()

    def test_detect_and_suggest_no_match(self):
        """Test detect_and_suggest with no match."""
        result = detect_and_suggest("xyz random gibberish")

        # May return empty or some result depending on threshold
        assert isinstance(result, str)


@pytest.mark.unit
class TestAutoDetectTemplate:
    """Tests for auto_detect_template function."""

    def test_auto_detect_high_confidence(self):
        """Test auto_detect returns template for high confidence match."""
        result = auto_detect_template("prepare for a release and deploy to production")

        assert result == "release-prep"

    def test_auto_detect_low_confidence(self):
        """Test auto_detect returns None for low confidence."""
        result = auto_detect_template("hello")

        assert result is None
