"""Smoke tests for attune.learning module."""


class TestLearningImports:
    """Verify the learning package exports are importable."""

    def test_import_package(self):
        """Test that the learning package imports cleanly."""
        from attune.learning import (
            LearnedSkillsStorage,
            PatternExtractor,
            SessionEvaluator,
        )

        assert SessionEvaluator is not None
        assert PatternExtractor is not None
        assert LearnedSkillsStorage is not None

    def test_session_quality_enum(self):
        """Test SessionQuality enum values."""
        from attune.learning.evaluator import SessionQuality

        assert SessionQuality.EXCELLENT.value == "excellent"
        assert SessionQuality.SKIP.value == "skip"

    def test_pattern_category_enum(self):
        """Test PatternCategory enum values."""
        from attune.learning.extractor import PatternCategory

        assert PatternCategory.ERROR_RESOLUTION.value == "error_resolution"
        assert PatternCategory.PREFERENCE.value == "preference"

    def test_session_evaluator_instantiation(self):
        """Test SessionEvaluator can be created."""
        from attune.learning.evaluator import SessionEvaluator

        evaluator = SessionEvaluator(
            min_interactions=5,
            min_score_for_extraction=0.3,
        )
        assert evaluator is not None

    def test_learned_skills_storage_instantiation(self, tmp_path):
        """Test LearnedSkillsStorage can be created."""
        from attune.learning.storage import LearnedSkillsStorage

        storage = LearnedSkillsStorage(storage_dir=str(tmp_path / "skills"))
        assert storage is not None
        assert storage.storage_dir == tmp_path / "skills"
