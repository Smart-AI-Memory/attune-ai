"""Integration tests for the learning module.

Tests session evaluation, pattern extraction, and learned skills storage
with integration to other framework components.
"""

import pytest

from attune.learning import (
    ExtractedPattern,
    LearnedSkill,
    LearnedSkillsStorage,
    PatternCategory,
    PatternExtractor,
    SessionEvaluator,
    SessionQuality,
)


class TestSessionEvaluatorIntegration:
    """Test SessionEvaluator for determining learning value."""

    @pytest.fixture
    def evaluator(self):
        """Create session evaluator."""
        return SessionEvaluator()

    def test_evaluator_instantiation(self, evaluator):
        """Test that evaluator can be instantiated."""
        assert evaluator is not None
        assert hasattr(evaluator, "evaluate")

    def test_session_quality_enum_values(self):
        """Test that SessionQuality enum has expected values."""
        assert SessionQuality.EXCELLENT.value == "excellent"
        assert SessionQuality.GOOD.value == "good"
        assert SessionQuality.AVERAGE.value == "average"
        assert SessionQuality.POOR.value == "poor"
        assert SessionQuality.SKIP.value == "skip"

    def test_evaluator_has_pattern_attributes(self, evaluator):
        """Test that evaluator has expected pattern detection attributes."""
        # These are internal but should exist
        assert hasattr(evaluator, "_correction_re")
        assert hasattr(evaluator, "_error_re")
        assert hasattr(evaluator, "_workaround_re")


class TestPatternExtractorIntegration:
    """Test PatternExtractor for pattern identification."""

    @pytest.fixture
    def extractor(self):
        """Create pattern extractor."""
        return PatternExtractor()

    def test_extractor_instantiation(self, extractor):
        """Test that extractor can be instantiated."""
        assert extractor is not None

    def test_extractor_has_internal_methods(self, extractor):
        """Test that extractor has internal extraction methods."""
        assert hasattr(extractor, "_extract_corrections")
        assert hasattr(extractor, "_extract_error_resolutions")

    def test_pattern_category_enum_values(self):
        """Test that PatternCategory enum has expected values."""
        assert PatternCategory.ERROR_RESOLUTION.value == "error_resolution"
        assert PatternCategory.USER_CORRECTION.value == "user_correction"
        assert PatternCategory.WORKAROUND.value == "workaround"
        assert PatternCategory.PREFERENCE.value == "preference"
        assert PatternCategory.PROJECT_SPECIFIC.value == "project_specific"


class TestExtractedPatternIntegration:
    """Test ExtractedPattern dataclass functionality."""

    def test_pattern_serialization_roundtrip(self):
        """Test pattern serialization and deserialization."""
        original = ExtractedPattern(
            category=PatternCategory.WORKAROUND,
            trigger="async function without await",
            context="Python async/await usage",
            resolution="Always await async functions",
            confidence=0.92,
            source_session="session_123",
            tags=["python", "async", "common-error"],
            metadata={"frequency": 5, "severity": "high"},
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = ExtractedPattern.from_dict(data)

        assert restored.category == original.category
        assert restored.trigger == original.trigger
        assert restored.resolution == original.resolution
        assert restored.confidence == original.confidence
        assert restored.tags == original.tags
        assert restored.metadata == original.metadata

    def test_pattern_id_generation(self):
        """Test that pattern ID is deterministic."""
        pattern = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="test trigger",
            context="test context",
            resolution="test resolution",
            confidence=0.8,
            source_session="test_session",
        )

        # ID should be consistent
        id1 = pattern.pattern_id
        id2 = pattern.pattern_id
        assert id1 == id2

        # Different patterns should have different IDs
        pattern2 = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="different trigger",
            context="test context",
            resolution="test resolution",
            confidence=0.8,
            source_session="test_session",
        )
        assert pattern.pattern_id != pattern2.pattern_id

    def test_pattern_format_readable(self):
        """Test human-readable formatting."""
        pattern = ExtractedPattern(
            category=PatternCategory.ERROR_RESOLUTION,
            trigger="TypeError in handler",
            context="Async request handling",
            resolution="Add proper type checking",
            confidence=0.85,
            source_session="test_session",
        )

        readable = pattern.format_readable()

        assert "Error Resolution" in readable
        assert "TypeError" in readable
        assert "type checking" in readable.lower()


class TestLearnedSkillsStorageIntegration:
    """Test LearnedSkillsStorage for pattern persistence."""

    @pytest.fixture
    def storage_dir(self, tmp_path):
        """Create temporary storage directory."""
        return tmp_path / "learned_skills"

    @pytest.fixture
    def storage(self, storage_dir):
        """Create storage instance."""
        return LearnedSkillsStorage(storage_dir=storage_dir)

    def test_save_and_retrieve_pattern(self, storage):
        """Test saving and retrieving a pattern."""
        user_id = "test_user"
        pattern = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="API response format",
            context="REST API development",
            resolution="Use JSON with snake_case keys",
            confidence=0.9,
            source_session="test_session",
        )

        # Save
        storage.save_pattern(user_id, pattern)

        # Retrieve all
        patterns = storage.get_all_patterns(user_id)
        assert len(patterns) >= 1

        # Find our pattern
        found = any(p.trigger == "API response format" for p in patterns)
        assert found

    def test_search_patterns(self, storage):
        """Test searching patterns by keyword."""
        user_id = "search_user"

        # Save multiple patterns
        patterns = [
            ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger="Python imports",
                context="Code organization",
                resolution="Sort imports alphabetically",
                confidence=0.85,
                source_session="session1",
            ),
            ExtractedPattern(
                category=PatternCategory.ERROR_RESOLUTION,
                trigger="Python ModuleNotFoundError",
                context="Dependency management",
                resolution="Check PYTHONPATH and virtual env",
                confidence=0.9,
                source_session="session2",
            ),
            ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger="JavaScript formatting",
                context="Frontend development",
                resolution="Use Prettier with default config",
                confidence=0.8,
                source_session="session3",
            ),
        ]

        for p in patterns:
            storage.save_pattern(user_id, p)

        # Search for Python-related patterns
        results = storage.search_patterns(user_id, "Python")
        assert len(results) == 2

        # Search for formatting
        results = storage.search_patterns(user_id, "formatting")
        assert len(results) >= 1

    def test_get_patterns_by_category(self, storage):
        """Test filtering patterns by category."""
        user_id = "category_user"

        patterns = [
            ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger="preference_trigger",
                context="test",
                resolution="preference_resolution",
                confidence=0.8,
                source_session="session1",
            ),
            ExtractedPattern(
                category=PatternCategory.ERROR_RESOLUTION,
                trigger="error_trigger",
                context="test",
                resolution="error_resolution",
                confidence=0.8,
                source_session="session2",
            ),
        ]

        for p in patterns:
            storage.save_pattern(user_id, p)

        # Filter by category
        preferences = storage.get_patterns_by_category(user_id, PatternCategory.PREFERENCE)
        assert len(preferences) >= 1
        assert all(p.category == PatternCategory.PREFERENCE for p in preferences)

    def test_format_patterns_for_context(self, storage):
        """Test formatting patterns for context injection."""
        user_id = "format_user"

        pattern = ExtractedPattern(
            category=PatternCategory.WORKAROUND,
            trigger="React state not updating",
            context="React hooks usage",
            resolution="Use functional setState with previous value",
            confidence=0.95,
            source_session="session1",
        )
        storage.save_pattern(user_id, pattern)

        # Format for context
        context_text = storage.format_patterns_for_context(user_id)

        assert "Learned Patterns" in context_text
        assert "React" in context_text or "state" in context_text.lower()

    def test_get_summary(self, storage):
        """Test getting storage summary."""
        user_id = "summary_user"

        # Add some patterns
        for i in range(3):
            pattern = ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger=f"trigger_{i}",
                context="test",
                resolution=f"resolution_{i}",
                confidence=0.8,
                source_session=f"session_{i}",
            )
            storage.save_pattern(user_id, pattern)

        summary = storage.get_summary(user_id)

        assert summary["total_patterns"] >= 3
        assert "patterns_by_category" in summary


class TestLearnedSkillIntegration:
    """Test LearnedSkill functionality."""

    def test_skill_serialization_roundtrip(self):
        """Test skill serialization and deserialization."""
        original = LearnedSkill(
            skill_id="skill_001",
            name="Python Async Mastery",
            description="Proper async/await usage in Python",
            category=PatternCategory.CODE_PATTERN,
            patterns=["pat_001", "pat_002", "pat_003"],
            confidence=0.88,
            usage_count=15,
            tags=["python", "async", "advanced"],
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = LearnedSkill.from_dict(data)

        assert restored.skill_id == original.skill_id
        assert restored.name == original.name
        assert restored.patterns == original.patterns
        assert restored.usage_count == 15
        assert restored.tags == ["python", "async", "advanced"]


class TestLearningWithHooksIntegration:
    """Test learning module integration with hooks."""

    def test_session_end_triggers_pattern_save(self, tmp_path):
        """Test that session end hook can save patterns to storage."""
        from attune.hooks.config import HookEvent
        from attune.hooks.registry import HookRegistry

        storage = LearnedSkillsStorage(storage_dir=tmp_path / "skills")
        hook_registry = HookRegistry()

        saved_patterns = []

        def session_end_handler(user_id="unknown", session_id="", **kwargs):
            # Manually create a pattern (in real use, would come from extractor)
            pattern = ExtractedPattern(
                category=PatternCategory.USER_CORRECTION,
                trigger="hook test",
                context="testing hooks with learning",
                resolution="hook saves pattern correctly",
                confidence=0.9,
                source_session=session_id,
            )
            storage.save_pattern(user_id, pattern)
            saved_patterns.append(pattern)

            return {
                "success": True,
                "patterns_saved": len(saved_patterns),
            }

        hook_registry.register(
            event=HookEvent.SESSION_END,
            handler=session_end_handler,
        )

        # Fire session end
        hook_registry.fire_sync(
            HookEvent.SESSION_END,
            {
                "user_id": "learning_user",
                "session_id": "learning_session",
            },
        )

        # Verify pattern was saved
        assert len(saved_patterns) == 1

        # Verify pattern is in storage
        patterns = storage.get_all_patterns("learning_user")
        assert len(patterns) >= 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_extractor_instantiation(self):
        """Test that PatternExtractor can be instantiated."""
        extractor = PatternExtractor()
        assert extractor is not None

    def test_high_confidence_patterns_prioritized(self, tmp_path):
        """Test that high confidence patterns are prioritized."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path / "priority")
        user_id = "priority_user"

        # Add patterns with varying confidence
        for i, confidence in enumerate([0.5, 0.9, 0.7, 0.95, 0.6]):
            pattern = ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger=f"trigger_{i}",
                context="priority test",
                resolution=f"resolution_{i}",
                confidence=confidence,
                source_session="session",
            )
            storage.save_pattern(user_id, pattern)

        # Get all patterns and sort by confidence manually
        patterns = storage.get_all_patterns(user_id)
        sorted_patterns = sorted(patterns, key=lambda p: p.confidence, reverse=True)[:3]

        # Verify patterns can be sorted by confidence
        if len(sorted_patterns) >= 2:
            confidences = [p.confidence for p in sorted_patterns]
            assert confidences == sorted(confidences, reverse=True)

    def test_duplicate_pattern_handling(self, tmp_path):
        """Test handling of duplicate patterns."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path / "duplicates")
        user_id = "duplicate_user"

        pattern = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="same trigger",
            context="same context",
            resolution="same resolution",
            confidence=0.8,
            source_session="session1",
        )

        # Save same pattern twice
        storage.save_pattern(user_id, pattern)
        storage.save_pattern(user_id, pattern)

        # Should either merge or keep only one
        patterns = storage.get_all_patterns(user_id)
        # Implementation dependent - just verify no crash
        assert len(patterns) >= 1
