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


def _make_pattern(
    trigger: str = "TypeError",
    resolution: str = "Add null check",
    category: PatternCategory = PatternCategory.ERROR_RESOLUTION,
    confidence: float = 0.8,
) -> ExtractedPattern:
    """Build a minimal ExtractedPattern for storage tests."""
    return ExtractedPattern(
        category=category,
        trigger=trigger,
        context="ctx",
        resolution=resolution,
        confidence=confidence,
        source_session="test-session",
    )


def _make_skill(
    skill_id: str = "skill-001",
    name: str = "Skill",
    created_at: datetime | None = None,
) -> LearnedSkill:
    """Build a minimal LearnedSkill for storage tests."""
    kwargs = {}
    if created_at is not None:
        kwargs["created_at"] = created_at
    return LearnedSkill(
        skill_id=skill_id,
        name=name,
        description="desc",
        category=PatternCategory.CODE_PATTERN,
        patterns=[],
        confidence=0.7,
        **kwargs,
    )


class TestPatternEdgeCases:
    """Edge-case behavior for pattern operations."""

    def test_save_duplicate_pattern_updates_in_place(self, tmp_path):
        """Re-saving a pattern with the same ID replaces it, not appends."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)

        first = _make_pattern(confidence=0.5)
        second = _make_pattern(confidence=0.9)  # same trigger/resolution => same ID
        assert first.pattern_id == second.pattern_id

        storage.save_pattern("user1", first)
        storage.save_pattern("user1", second)

        patterns = storage.get_all_patterns("user1")
        assert len(patterns) == 1
        assert patterns[0].confidence == 0.9

    def test_delete_pattern_missing_returns_false(self, tmp_path):
        """Deleting a nonexistent pattern returns False and keeps the rest."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_pattern("user1", _make_pattern())

        assert storage.delete_pattern("user1", "no-such-id") is False
        assert len(storage.get_all_patterns("user1")) == 1

    def test_corrupt_patterns_file_returns_empty(self, tmp_path):
        """A corrupt patterns.json is tolerated and reads as no patterns."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_pattern("user1", _make_pattern())

        patterns_file = tmp_path / "user1" / "patterns.json"
        patterns_file.write_text("{not valid json", encoding="utf-8")

        assert storage.get_all_patterns("user1") == []


class TestSkillEdgeCases:
    """Edge-case behavior for skill operations."""

    def test_save_duplicate_skill_updates_in_place(self, tmp_path):
        """Re-saving a skill with the same ID replaces it, not appends."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)

        storage.save_skill("user1", _make_skill(name="Old Name"))
        storage.save_skill("user1", _make_skill(name="New Name"))

        skills = storage.get_all_skills("user1")
        assert len(skills) == 1
        assert skills[0].name == "New Name"

    def test_max_skills_limit_keeps_newest(self, tmp_path):
        """Saving beyond max_skills_per_user drops the oldest skills."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path, max_skills_per_user=2)

        storage.save_skill("user1", _make_skill("s-old", created_at=datetime(2026, 1, 1)))
        storage.save_skill("user1", _make_skill("s-mid", created_at=datetime(2026, 2, 1)))
        storage.save_skill("user1", _make_skill("s-new", created_at=datetime(2026, 3, 1)))

        skills = storage.get_all_skills("user1")
        assert len(skills) == 2
        assert {s.skill_id for s in skills} == {"s-mid", "s-new"}

    def test_get_skill_missing_returns_none(self, tmp_path):
        """Looking up an unknown skill ID returns None."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_skill("user1", _make_skill("s-exists"))

        assert storage.get_skill("user1", "s-missing") is None

    def test_delete_skill_existing_returns_true(self, tmp_path):
        """Deleting an existing skill removes it and returns True."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_skill("user1", _make_skill("s-1"))

        assert storage.delete_skill("user1", "s-1") is True
        assert storage.get_all_skills("user1") == []

    def test_delete_skill_missing_returns_false(self, tmp_path):
        """Deleting a nonexistent skill returns False, leaving others intact."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_skill("user1", _make_skill("s-1"))

        assert storage.delete_skill("user1", "s-missing") is False
        assert len(storage.get_all_skills("user1")) == 1

    def test_corrupt_skills_file_returns_empty(self, tmp_path):
        """A corrupt skills.json is tolerated and reads as no skills."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_skill("user1", _make_skill("s-1"))

        skills_file = tmp_path / "user1" / "skills.json"
        skills_file.write_text("[truncated", encoding="utf-8")

        assert storage.get_all_skills("user1") == []


class TestClearUserDataEdgeCases:
    """Edge-case behavior for clear_user_data."""

    def test_clear_skips_corrupt_file_and_keeps_dir(self, tmp_path):
        """A corrupt JSON file is skipped (not deleted) and the dir survives."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_pattern("user1", _make_pattern())

        user_dir = tmp_path / "user1"
        corrupt = user_dir / "extra.json"
        corrupt.write_text("{broken", encoding="utf-8")

        count = storage.clear_user_data("user1")

        assert count == 1  # only the valid pattern was counted
        assert not (user_dir / "patterns.json").exists()
        assert corrupt.exists()  # skipped, not deleted
        assert user_dir.exists()  # rmdir failed on non-empty dir, tolerated

    def test_clear_missing_user_returns_zero(self, tmp_path):
        """Clearing a user with no data returns 0."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)

        assert storage.clear_user_data("ghost") == 0


class TestFormatPatternsEdgeCases:
    """Edge-case behavior for format_patterns_for_context."""

    def test_category_filter_limits_output(self, tmp_path):
        """Only patterns in the requested categories are formatted."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)
        storage.save_pattern("user1", _make_pattern(trigger="TypeError"))
        storage.save_pattern(
            "user1",
            _make_pattern(
                trigger="prefers tables",
                resolution="use markdown tables",
                category=PatternCategory.PREFERENCE,
            ),
        )

        context = storage.format_patterns_for_context(
            "user1",
            categories=[PatternCategory.PREFERENCE],
        )

        assert "prefers tables" in context
        assert "TypeError" not in context

    def test_no_matching_patterns_returns_empty_string(self, tmp_path):
        """No patterns (or none after filtering) yields an empty string."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path)

        assert storage.format_patterns_for_context("nobody") == ""

        storage.save_pattern("user1", _make_pattern())
        filtered = storage.format_patterns_for_context(
            "user1",
            categories=[PatternCategory.WORKAROUND],
        )
        assert filtered == ""
