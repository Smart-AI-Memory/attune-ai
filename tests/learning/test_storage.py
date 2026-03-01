"""Tests for the learned skills storage."""

import tempfile
from datetime import datetime

import pytest

from attune.learning.extractor import ExtractedPattern, PatternCategory
from attune.learning.storage import LearnedSkill, LearnedSkillsStorage


class TestLearnedSkill:
    """Tests for LearnedSkill dataclass."""

    def test_create_skill(self):
        """Test creating a learned skill."""
        skill = LearnedSkill(
            skill_id="skill-001",
            name="Error Handling",
            description="Best practices for error handling",
            category=PatternCategory.ERROR_RESOLUTION,
            patterns=["pattern-1", "pattern-2"],
            confidence=0.85,
        )

        assert skill.skill_id == "skill-001"
        assert skill.usage_count == 0
        assert skill.last_used is None

    def test_skill_to_dict(self):
        """Test converting skill to dict."""
        skill = LearnedSkill(
            skill_id="skill-002",
            name="Testing Patterns",
            description="Unit testing best practices",
            category=PatternCategory.CODE_PATTERN,
            patterns=["p1"],
            confidence=0.7,
            tags=["testing"],
        )

        data = skill.to_dict()

        assert data["skill_id"] == "skill-002"
        assert data["category"] == "code_pattern"
        assert "testing" in data["tags"]

    def test_skill_from_dict(self):
        """Test creating skill from dict."""
        data = {
            "skill_id": "skill-003",
            "name": "Debug Skill",
            "description": "Debugging techniques",
            "category": "debugging_technique",
            "patterns": ["p1", "p2"],
            "confidence": 0.8,
            "usage_count": 5,
            "created_at": datetime.now().isoformat(),
        }

        skill = LearnedSkill.from_dict(data)

        assert skill.skill_id == "skill-003"
        assert skill.usage_count == 5


class TestLearnedSkillsStorage:
    """Tests for LearnedSkillsStorage class."""

    def test_save_and_get_pattern(self):
        """Test saving and retrieving a pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            pattern = ExtractedPattern(
                category=PatternCategory.ERROR_RESOLUTION,
                trigger="TypeError",
                context="Null reference",
                resolution="Add null check",
                confidence=0.8,
                source_session="test",
            )

            pattern_id = storage.save_pattern("user1", pattern)
            retrieved = storage.get_pattern("user1", pattern_id)

            assert retrieved is not None
            assert retrieved.trigger == "TypeError"
            assert retrieved.confidence == 0.8

    def test_save_multiple_patterns(self):
        """Test saving multiple patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            patterns = [
                ExtractedPattern(
                    category=PatternCategory.PREFERENCE,
                    trigger=f"trigger-{i}",
                    context=f"context-{i}",
                    resolution=f"resolution-{i}",
                    confidence=0.5 + (i * 0.1),
                    source_session="test",
                )
                for i in range(3)
            ]

            ids = storage.save_patterns("user1", patterns)
            all_patterns = storage.get_all_patterns("user1")

            assert len(ids) == 3
            assert len(all_patterns) == 3

    def test_get_patterns_by_category(self):
        """Test filtering patterns by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            # Save patterns of different categories
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.ERROR_RESOLUTION,
                    trigger="error",
                    context="ctx",
                    resolution="res",
                    confidence=0.8,
                    source_session="t",
                ),
            )
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.PREFERENCE,
                    trigger="pref",
                    context="ctx",
                    resolution="res",
                    confidence=0.6,
                    source_session="t",
                ),
            )

            error_patterns = storage.get_patterns_by_category(
                "user1",
                PatternCategory.ERROR_RESOLUTION,
            )
            pref_patterns = storage.get_patterns_by_category("user1", PatternCategory.PREFERENCE)

            assert len(error_patterns) == 1
            assert len(pref_patterns) == 1

    def test_get_patterns_by_tag(self):
        """Test filtering patterns by tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.WORKAROUND,
                    trigger="api",
                    context="ctx",
                    resolution="res",
                    confidence=0.7,
                    source_session="t",
                    tags=["api", "workaround"],
                ),
            )
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.CODE_PATTERN,
                    trigger="code",
                    context="ctx",
                    resolution="res",
                    confidence=0.6,
                    source_session="t",
                    tags=["code"],
                ),
            )

            api_patterns = storage.get_patterns_by_tag("user1", "api")
            assert len(api_patterns) == 1
            assert api_patterns[0].trigger == "api"

    def test_search_patterns(self):
        """Test searching patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.ERROR_RESOLUTION,
                    trigger="async timeout error",
                    context="Network request",
                    resolution="Add timeout handling",
                    confidence=0.8,
                    source_session="t",
                ),
            )
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.PREFERENCE,
                    trigger="style",
                    context="Code style",
                    resolution="Use TypeScript",
                    confidence=0.6,
                    source_session="t",
                ),
            )

            results = storage.search_patterns("user1", "timeout")
            assert len(results) == 1
            assert "timeout" in results[0].trigger.lower()

    def test_delete_pattern(self):
        """Test deleting a pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            pattern = ExtractedPattern(
                category=PatternCategory.PREFERENCE,
                trigger="delete-test",
                context="ctx",
                resolution="res",
                confidence=0.5,
                source_session="t",
            )

            pattern_id = storage.save_pattern("user1", pattern)
            assert storage.get_pattern("user1", pattern_id) is not None

            deleted = storage.delete_pattern("user1", pattern_id)
            assert deleted is True
            assert storage.get_pattern("user1", pattern_id) is None

    def test_max_patterns_limit(self):
        """Test that max patterns limit is enforced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(
                storage_dir=tmpdir,
                max_patterns_per_user=3,
            )

            # Save 5 patterns
            for i in range(5):
                storage.save_pattern(
                    "user1",
                    ExtractedPattern(
                        category=PatternCategory.PREFERENCE,
                        trigger=f"trigger-{i}",
                        context=f"ctx-{i}",
                        resolution=f"res-{i}",
                        confidence=0.5,
                        source_session="t",
                    ),
                )

            all_patterns = storage.get_all_patterns("user1")
            assert len(all_patterns) == 3

    def test_save_and_get_skill(self):
        """Test saving and retrieving a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            skill = LearnedSkill(
                skill_id="skill-001",
                name="Test Skill",
                description="A test skill",
                category=PatternCategory.CODE_PATTERN,
                patterns=["p1", "p2"],
                confidence=0.75,
            )

            storage.save_skill("user1", skill)
            retrieved = storage.get_skill("user1", "skill-001")

            assert retrieved is not None
            assert retrieved.name == "Test Skill"
            assert retrieved.confidence == 0.75

    def test_record_skill_usage(self):
        """Test recording skill usage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            skill = LearnedSkill(
                skill_id="skill-usage",
                name="Usage Skill",
                description="Test",
                category=PatternCategory.PREFERENCE,
                patterns=[],
                confidence=0.5,
            )

            storage.save_skill("user1", skill)

            # Use the skill multiple times
            storage.record_skill_usage("user1", "skill-usage")
            storage.record_skill_usage("user1", "skill-usage")

            retrieved = storage.get_skill("user1", "skill-usage")
            assert retrieved.usage_count == 2
            assert retrieved.last_used is not None

    def test_get_summary(self):
        """Test getting learning summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            # Add some patterns
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.ERROR_RESOLUTION,
                    trigger="error",
                    context="ctx",
                    resolution="res",
                    confidence=0.8,
                    source_session="t",
                ),
            )
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.PREFERENCE,
                    trigger="pref",
                    context="ctx",
                    resolution="res",
                    confidence=0.6,
                    source_session="t",
                ),
            )

            summary = storage.get_summary("user1")

            assert summary["total_patterns"] == 2
            assert summary["patterns_by_category"]["error_resolution"] == 1
            assert summary["patterns_by_category"]["preference"] == 1
            assert summary["avg_confidence"] == pytest.approx(0.7, rel=0.01)

    def test_clear_user_data(self):
        """Test clearing all user data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            # Add patterns and skills
            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.PREFERENCE,
                    trigger="t",
                    context="c",
                    resolution="r",
                    confidence=0.5,
                    source_session="s",
                ),
            )
            storage.save_skill(
                "user1",
                LearnedSkill(
                    skill_id="s1",
                    name="S",
                    description="D",
                    category=PatternCategory.CODE_PATTERN,
                    patterns=[],
                    confidence=0.5,
                ),
            )

            cleared = storage.clear_user_data("user1")
            assert cleared >= 2

            assert len(storage.get_all_patterns("user1")) == 0
            assert len(storage.get_all_skills("user1")) == 0

    def test_format_patterns_for_context(self):
        """Test formatting patterns for context injection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LearnedSkillsStorage(storage_dir=tmpdir)

            storage.save_pattern(
                "user1",
                ExtractedPattern(
                    category=PatternCategory.ERROR_RESOLUTION,
                    trigger="TypeError",
                    context="Null reference",
                    resolution="Add null check",
                    confidence=0.9,
                    source_session="t",
                ),
            )

            context = storage.format_patterns_for_context("user1", max_patterns=5)

            assert "## Learned Patterns" in context
            assert "TypeError" in context
            assert "Error Resolution" in context
