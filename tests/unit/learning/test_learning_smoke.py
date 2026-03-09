"""Smoke tests for learning.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.learning

        assert attune.learning is not None

    def test_evaluator_imports(self) -> None:
        """Test that evaluator classes import."""
        from attune.learning import SessionEvaluator, SessionQuality

        assert SessionEvaluator is not None
        assert SessionQuality is not None

    def test_extractor_imports(self) -> None:
        """Test that extractor classes import."""
        from attune.learning import ExtractedPattern, PatternCategory, PatternExtractor

        assert ExtractedPattern is not None
        assert PatternCategory is not None
        assert PatternExtractor is not None

    def test_storage_imports(self) -> None:
        """Test that storage classes import."""
        from attune.learning import LearnedSkill, LearnedSkillsStorage

        assert LearnedSkill is not None
        assert LearnedSkillsStorage is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_session_evaluator_defaults(self) -> None:
        """Test SessionEvaluator with defaults."""
        from attune.learning import SessionEvaluator

        evaluator = SessionEvaluator()
        assert evaluator is not None

    def test_pattern_extractor_defaults(self) -> None:
        """Test PatternExtractor with defaults."""
        from attune.learning import PatternExtractor

        extractor = PatternExtractor()
        assert extractor is not None

    def test_learned_skills_storage_defaults(self, tmp_path) -> None:
        """Test LearnedSkillsStorage with temp dir."""
        from attune.learning import LearnedSkillsStorage

        storage = LearnedSkillsStorage(storage_dir=str(tmp_path / "skills"))
        assert storage is not None
        assert storage.storage_dir == tmp_path / "skills"

    def test_extracted_pattern_creation(self) -> None:
        """Test ExtractedPattern dataclass creation."""
        from attune.learning import ExtractedPattern, PatternCategory

        pattern = ExtractedPattern(
            category=PatternCategory.ERROR_RESOLUTION,
            trigger="import error",
            context="Python module",
            resolution="install missing package",
            confidence=0.8,
            source_session="session-001",
        )
        assert pattern.category == PatternCategory.ERROR_RESOLUTION
        assert len(pattern.pattern_id) == 12

    def test_session_quality_enum(self) -> None:
        """Test SessionQuality enum values."""
        from attune.learning import SessionQuality

        assert SessionQuality.EXCELLENT.value == "excellent"
        assert SessionQuality.SKIP.value == "skip"
