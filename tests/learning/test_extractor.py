"""Tests for the pattern extractor."""

from datetime import datetime

from attune.learning.extractor import (
    ExtractedPattern,
    PatternCategory,
    PatternExtractor,
)
from attune.llm.state import CollaborationState


class TestExtractedPattern:
    """Tests for ExtractedPattern dataclass."""

    def test_create_pattern(self):
        """Test creating a pattern."""
        pattern = ExtractedPattern(
            category=PatternCategory.USER_CORRECTION,
            trigger="Misunderstood request",
            context="User clarified async vs callback",
            resolution="Use async/await syntax",
            confidence=0.8,
            source_session="session-001",
        )

        assert pattern.category == PatternCategory.USER_CORRECTION
        assert pattern.confidence == 0.8
        assert pattern.pattern_id  # Should be generated

    def test_pattern_id_generation(self):
        """Test that pattern ID is deterministic."""
        pattern1 = ExtractedPattern(
            category=PatternCategory.ERROR_RESOLUTION,
            trigger="TypeError",
            context="Null check missing",
            resolution="Add null check",
            confidence=0.7,
            source_session="s1",
        )

        pattern2 = ExtractedPattern(
            category=PatternCategory.ERROR_RESOLUTION,
            trigger="TypeError",
            context="Different context",
            resolution="Add null check",
            confidence=0.9,
            source_session="s2",
        )

        # Same category + trigger + resolution = same ID
        assert pattern1.pattern_id == pattern2.pattern_id

    def test_pattern_to_dict(self):
        """Test converting pattern to dict."""
        pattern = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="style",
            context="User prefers detailed",
            resolution="Be detailed",
            confidence=0.6,
            source_session="sess",
            tags=["preference", "style"],
        )

        data = pattern.to_dict()

        assert data["category"] == "preference"
        assert data["trigger"] == "style"
        assert "preference" in data["tags"]
        assert "pattern_id" in data

    def test_pattern_from_dict(self):
        """Test creating pattern from dict."""
        data = {
            "category": "workaround",
            "trigger": "library limitation",
            "context": "X doesn't support Y",
            "resolution": "Use Z instead",
            "confidence": 0.7,
            "source_session": "test",
            "extracted_at": datetime.now().isoformat(),
            "tags": ["workaround"],
        }

        pattern = ExtractedPattern.from_dict(data)

        assert pattern.category == PatternCategory.WORKAROUND
        assert pattern.trigger == "library limitation"
        assert pattern.confidence == 0.7

    def test_format_readable(self):
        """Test formatting pattern as readable text."""
        pattern = ExtractedPattern(
            category=PatternCategory.ERROR_RESOLUTION,
            trigger="NullPointerException",
            context="Accessing property of null",
            resolution="Add null check before access",
            confidence=0.85,
            source_session="test",
            tags=["error", "null"],
        )

        readable = pattern.format_readable()

        assert "Error Resolution" in readable
        assert "NullPointerException" in readable
        assert "85%" in readable
        assert "error" in readable


class TestPatternExtractor:
    """Tests for PatternExtractor class."""

    def test_init_default(self):
        """Test default initialization."""
        extractor = PatternExtractor()

        assert extractor._min_confidence == 0.3
        assert extractor._max_patterns == 10

    def test_extract_corrections(self):
        """Test extracting user correction patterns."""
        extractor = PatternExtractor()
        state = CollaborationState(user_id="test")

        state.add_interaction("user", "How do I use callbacks?", 2)
        state.add_interaction("assistant", "Callbacks work like this...", 2)
        state.add_interaction("user", "Actually, I meant async/await", 2)
        state.add_interaction("assistant", "For async/await, you do...", 3)

        patterns = extractor.extract_patterns(state, "test-session")

        correction_patterns = [p for p in patterns if p.category == PatternCategory.USER_CORRECTION]
        assert len(correction_patterns) >= 1

    def test_extract_error_resolutions(self):
        """Test extracting error resolution patterns."""
        extractor = PatternExtractor()
        state = CollaborationState(user_id="test")

        state.add_interaction("user", "Error: Cannot read property 'name' of null", 2)
        state.add_interaction("assistant", "Add a null check before accessing...", 3)
        state.add_interaction("user", "That works! Thanks!", 2)

        patterns = extractor.extract_patterns(state, "test-session")

        error_patterns = [p for p in patterns if p.category == PatternCategory.ERROR_RESOLUTION]
        assert len(error_patterns) >= 1

    def test_extract_workarounds(self):
        """Test extracting workaround patterns."""
        extractor = PatternExtractor()
        state = CollaborationState(user_id="test")

        state.add_interaction("user", "This API doesn't support pagination", 2)
        state.add_interaction(
            "assistant",
            "A workaround is to fetch all data and paginate client-side",
            3,
        )

        patterns = extractor.extract_patterns(state, "test-session")

        workaround_patterns = [p for p in patterns if p.category == PatternCategory.WORKAROUND]
        assert len(workaround_patterns) >= 1

    def test_extract_preferences(self):
        """Test extracting preference patterns."""
        extractor = PatternExtractor()
        state = CollaborationState(user_id="test")

        state.add_interaction("user", "I prefer TypeScript over JavaScript", 2)
        state.add_interaction("user", "I always use functional components", 2)

        patterns = extractor.extract_patterns(state, "test-session")

        pref_patterns = [p for p in patterns if p.category == PatternCategory.PREFERENCE]
        assert len(pref_patterns) >= 2

    def test_extract_project_patterns(self):
        """Test extracting project-specific patterns."""
        extractor = PatternExtractor()
        state = CollaborationState(user_id="test")

        state.add_interaction(
            "user",
            "In this project, we always use snake_case for variables",
            2,
        )
        state.add_interaction(
            "assistant",
            "I'll use snake_case for all variables in this codebase",
            3,
        )

        patterns = extractor.extract_patterns(state, "test-session")

        project_patterns = [p for p in patterns if p.category == PatternCategory.PROJECT_SPECIFIC]
        assert len(project_patterns) >= 1

    def test_max_patterns_limit(self):
        """Test that max patterns limit is enforced."""
        extractor = PatternExtractor(max_patterns_per_session=3)
        state = CollaborationState(user_id="test")

        # Add many correction-triggering interactions
        for i in range(10):
            state.add_interaction("user", f"Question {i}", 2)
            state.add_interaction("assistant", f"Answer {i}", 2)
            state.add_interaction("user", f"Actually, I meant {i}", 2)
            state.add_interaction("assistant", f"Corrected answer {i}", 3)

        patterns = extractor.extract_patterns(state, "test-session")

        assert len(patterns) <= 3

    def test_min_confidence_filter(self):
        """Test that low confidence patterns are filtered."""
        extractor = PatternExtractor(min_confidence=0.8)
        state = CollaborationState(user_id="test")

        # Add a weak preference signal
        state.add_interaction("user", "I like this", 2)

        patterns = extractor.extract_patterns(state, "test-session")

        # Low confidence preferences should be filtered
        for pattern in patterns:
            assert pattern.confidence >= 0.8

    def test_categorize_pattern(self):
        """Test pattern categorization."""
        extractor = PatternExtractor()

        assert (
            extractor.categorize_pattern(
                "TypeError",
                "Fix the error by adding null check",
            )
            == PatternCategory.ERROR_RESOLUTION
        )

        assert (
            extractor.categorize_pattern(
                "Actually",
                "User clarification about requirements",
            )
            == PatternCategory.USER_CORRECTION
        )

        assert (
            extractor.categorize_pattern(
                "style",
                "I prefer detailed responses",
            )
            == PatternCategory.PREFERENCE
        )

    def test_summarize_truncation(self):
        """Test that long text is truncated."""
        extractor = PatternExtractor()

        long_text = "x" * 200
        summary = extractor._summarize(long_text, 50)

        assert len(summary) <= 53  # 50 + "..."

    def test_summarize_preserves_sentences(self):
        """Test that summarization tries to preserve sentence boundaries."""
        extractor = PatternExtractor()

        text = "First sentence. Second sentence. Third sentence is very long."
        summary = extractor._summarize(text, 40)

        # Should cut at sentence boundary
        assert summary.endswith(".") or summary.endswith("...")
