"""Learned Skills Storage for Continuous Learning

Persists and retrieves learned patterns and skills.
Provides storage for patterns extracted from sessions.

Architectural patterns inspired by everything-claude-code by Affaan Mustafa.
See: https://github.com/affaan-m/everything-claude-code (MIT License)
See: ACKNOWLEDGMENTS.md for full attribution.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.learning.extractor import ExtractedPattern, PatternCategory
from attune.security.path_validation import _validate_file_path

logger = logging.getLogger(__name__)


@dataclass
class LearnedSkill:
    """A skill learned from pattern aggregation.

    Skills are higher-level learnings derived from
    multiple related patterns.
    """

    skill_id: str
    name: str
    description: str
    category: PatternCategory
    patterns: list[str]  # Pattern IDs
    confidence: float
    usage_count: int = 0
    last_used: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "patterns": self.patterns,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearnedSkill:
        """Create from dictionary."""
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data["description"],
            category=PatternCategory(data["category"]),
            patterns=data.get("patterns", []),
            confidence=data.get("confidence", 0.5),
            usage_count=data.get("usage_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now()
            ),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class LearnedSkillsStorage:
    """Manages storage of learned patterns and skills.

    Provides persistence and retrieval for patterns extracted
    from collaboration sessions, with support for querying
    and filtering.
    """

    def __init__(
        self,
        storage_dir: str | Path = ".attune/learned_skills",
        max_patterns_per_user: int = 100,
        max_skills_per_user: int = 50,
    ):
        """Initialize the storage.

        Args:
            storage_dir: Directory for storage files
            max_patterns_per_user: Maximum patterns to store per user
            max_skills_per_user: Maximum skills to store per user

        """
        self.storage_dir = Path(storage_dir)
        self._max_patterns = max_patterns_per_user
        self._max_skills = max_skills_per_user

    def _ensure_storage(self) -> None:
        """Ensure storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_dir(self, user_id: str) -> Path:
        """Get storage directory for a user."""
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.storage_dir / safe_id

    def _get_patterns_file(self, user_id: str) -> Path:
        """Get patterns file path for a user."""
        return self._get_user_dir(user_id) / "patterns.json"

    def _get_skills_file(self, user_id: str) -> Path:
        """Get skills file path for a user."""
        return self._get_user_dir(user_id) / "skills.json"

    # Pattern operations

    def save_pattern(
        self,
        user_id: str,
        pattern: ExtractedPattern,
    ) -> str:
        """Save a pattern for a user.

        Args:
            user_id: User identifier
            pattern: Pattern to save

        Returns:
            Pattern ID

        """
        self._ensure_storage()
        user_dir = self._get_user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        patterns = self._load_patterns(user_id)

        # Check for duplicate
        existing_ids = {p["pattern_id"] for p in patterns}
        if pattern.pattern_id in existing_ids:
            logger.debug(f"Pattern {pattern.pattern_id} already exists, updating")
            patterns = [p for p in patterns if p["pattern_id"] != pattern.pattern_id]

        patterns.append(pattern.to_dict())

        # Enforce limit (remove oldest)
        if len(patterns) > self._max_patterns:
            patterns = sorted(
                patterns,
                key=lambda p: p.get("extracted_at", ""),
                reverse=True,
            )[: self._max_patterns]

        self._save_patterns(user_id, patterns)
        logger.info(f"Saved pattern {pattern.pattern_id} for user {user_id}")

        return pattern.pattern_id

    def save_patterns(
        self,
        user_id: str,
        patterns: list[ExtractedPattern],
    ) -> list[str]:
        """Save multiple patterns.

        Args:
            user_id: User identifier
            patterns: Patterns to save

        Returns:
            List of saved pattern IDs

        """
        return [self.save_pattern(user_id, p) for p in patterns]

    def get_pattern(
        self,
        user_id: str,
        pattern_id: str,
    ) -> ExtractedPattern | None:
        """Get a specific pattern.

        Args:
            user_id: User identifier
            pattern_id: Pattern identifier

        Returns:
            Pattern or None if not found

        """
        patterns = self._load_patterns(user_id)

        for p in patterns:
            if p.get("pattern_id") == pattern_id:
                return ExtractedPattern.from_dict(p)

        return None

    def get_all_patterns(self, user_id: str) -> list[ExtractedPattern]:
        """Get all patterns for a user.

        Args:
            user_id: User identifier

        Returns:
            List of patterns

        """
        patterns = self._load_patterns(user_id)
        return [ExtractedPattern.from_dict(p) for p in patterns]

    def get_patterns_by_category(
        self,
        user_id: str,
        category: PatternCategory,
    ) -> list[ExtractedPattern]:
        """Get patterns by category.

        Args:
            user_id: User identifier
            category: Pattern category

        Returns:
            List of matching patterns

        """
        all_patterns = self.get_all_patterns(user_id)
        return [p for p in all_patterns if p.category == category]

    def get_patterns_by_tag(
        self,
        user_id: str,
        tag: str,
    ) -> list[ExtractedPattern]:
        """Get patterns by tag.

        Args:
            user_id: User identifier
            tag: Tag to filter by

        Returns:
            List of matching patterns

        """
        all_patterns = self.get_all_patterns(user_id)
        return [p for p in all_patterns if tag in p.tags]

    def search_patterns(
        self,
        user_id: str,
        query: str,
    ) -> list[ExtractedPattern]:
        """Search patterns by trigger or context.

        Args:
            user_id: User identifier
            query: Search query

        Returns:
            List of matching patterns

        """
        all_patterns = self.get_all_patterns(user_id)
        query_lower = query.lower()

        return [
            p
            for p in all_patterns
            if query_lower in p.trigger.lower()
            or query_lower in p.context.lower()
            or query_lower in p.resolution.lower()
        ]

    def delete_pattern(self, user_id: str, pattern_id: str) -> bool:
        """Delete a pattern.

        Args:
            user_id: User identifier
            pattern_id: Pattern to delete

        Returns:
            True if deleted

        """
        patterns = self._load_patterns(user_id)
        original_count = len(patterns)

        patterns = [p for p in patterns if p.get("pattern_id") != pattern_id]

        if len(patterns) < original_count:
            self._save_patterns(user_id, patterns)
            return True

        return False

    def _load_patterns(self, user_id: str) -> list[dict[str, Any]]:
        """Load patterns from storage."""
        patterns_file = self._get_patterns_file(user_id)

        if not patterns_file.exists():
            return []

        try:
            with open(patterns_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load patterns: {e}")
            return []

    def _save_patterns(
        self,
        user_id: str,
        patterns: list[dict[str, Any]],
    ) -> None:
        """Save patterns to storage."""
        patterns_file = self._get_patterns_file(user_id)

        validated_path = _validate_file_path(str(patterns_file))
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2, default=str)

    # Skill operations

    def save_skill(
        self,
        user_id: str,
        skill: LearnedSkill,
    ) -> str:
        """Save a learned skill.

        Args:
            user_id: User identifier
            skill: Skill to save

        Returns:
            Skill ID

        """
        self._ensure_storage()
        user_dir = self._get_user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        skills = self._load_skills(user_id)

        # Check for duplicate
        existing_ids = {s["skill_id"] for s in skills}
        if skill.skill_id in existing_ids:
            skills = [s for s in skills if s["skill_id"] != skill.skill_id]

        skills.append(skill.to_dict())

        # Enforce limit
        if len(skills) > self._max_skills:
            skills = sorted(
                skills,
                key=lambda s: s.get("created_at", ""),
                reverse=True,
            )[: self._max_skills]

        self._save_skills(user_id, skills)
        return skill.skill_id

    def get_skill(
        self,
        user_id: str,
        skill_id: str,
    ) -> LearnedSkill | None:
        """Get a specific skill.

        Args:
            user_id: User identifier
            skill_id: Skill identifier

        Returns:
            Skill or None

        """
        skills = self._load_skills(user_id)

        for s in skills:
            if s.get("skill_id") == skill_id:
                return LearnedSkill.from_dict(s)

        return None

    def get_all_skills(self, user_id: str) -> list[LearnedSkill]:
        """Get all skills for a user.

        Args:
            user_id: User identifier

        Returns:
            List of skills

        """
        skills = self._load_skills(user_id)
        return [LearnedSkill.from_dict(s) for s in skills]

    def record_skill_usage(
        self,
        user_id: str,
        skill_id: str,
    ) -> None:
        """Record that a skill was used.

        Args:
            user_id: User identifier
            skill_id: Skill that was used

        """
        skills = self._load_skills(user_id)

        for s in skills:
            if s.get("skill_id") == skill_id:
                s["usage_count"] = s.get("usage_count", 0) + 1
                s["last_used"] = datetime.now().isoformat()
                break

        self._save_skills(user_id, skills)

    def delete_skill(self, user_id: str, skill_id: str) -> bool:
        """Delete a skill.

        Args:
            user_id: User identifier
            skill_id: Skill to delete

        Returns:
            True if deleted

        """
        skills = self._load_skills(user_id)
        original_count = len(skills)

        skills = [s for s in skills if s.get("skill_id") != skill_id]

        if len(skills) < original_count:
            self._save_skills(user_id, skills)
            return True

        return False

    def _load_skills(self, user_id: str) -> list[dict[str, Any]]:
        """Load skills from storage."""
        skills_file = self._get_skills_file(user_id)

        if not skills_file.exists():
            return []

        try:
            with open(skills_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load skills: {e}")
            return []

    def _save_skills(
        self,
        user_id: str,
        skills: list[dict[str, Any]],
    ) -> None:
        """Save skills to storage."""
        skills_file = self._get_skills_file(user_id)

        validated_path = _validate_file_path(str(skills_file))
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(skills, f, indent=2, default=str)

    # Summary operations

    def get_summary(self, user_id: str) -> dict[str, Any]:
        """Get learning summary for a user.

        Args:
            user_id: User identifier

        Returns:
            Summary dictionary

        """
        patterns = self.get_all_patterns(user_id)
        skills = self.get_all_skills(user_id)

        # Count by category
        category_counts: dict[str, int] = {}
        for pattern in patterns:
            cat = pattern.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "user_id": user_id,
            "total_patterns": len(patterns),
            "total_skills": len(skills),
            "patterns_by_category": category_counts,
            "avg_confidence": (
                sum(p.confidence for p in patterns) / len(patterns) if patterns else 0.0
            ),
            "most_used_skill": (max(skills, key=lambda s: s.usage_count).name if skills else None),
        }

    def clear_user_data(self, user_id: str) -> int:
        """Clear all data for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of items cleared

        """
        user_dir = self._get_user_dir(user_id)
        count = 0

        if user_dir.exists():
            for file in user_dir.glob("*.json"):
                try:
                    # Count items before deleting
                    with open(file, encoding="utf-8") as f:
                        data = json.load(f)
                        count += len(data) if isinstance(data, list) else 1
                    file.unlink()
                except (OSError, json.JSONDecodeError):
                    continue

            try:
                user_dir.rmdir()
            except OSError:
                pass

        return count

    def format_patterns_for_context(
        self,
        user_id: str,
        max_patterns: int = 5,
        categories: list[PatternCategory] | None = None,
    ) -> str:
        """Format patterns for injection into context.

        Args:
            user_id: User identifier
            max_patterns: Maximum patterns to include
            categories: Optional category filter

        Returns:
            Formatted markdown string

        """
        patterns = self.get_all_patterns(user_id)

        if categories:
            patterns = [p for p in patterns if p.category in categories]

        # Sort by confidence
        patterns = sorted(patterns, key=lambda p: p.confidence, reverse=True)
        patterns = patterns[:max_patterns]

        if not patterns:
            return ""

        lines = ["## Learned Patterns", ""]

        for pattern in patterns:
            lines.append(pattern.format_readable())
            lines.append("")

        return "\n".join(lines)
