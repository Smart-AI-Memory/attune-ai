"""Tests for pattern registry.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import pytest

from patterns.core import BasePattern, PatternCategory
from patterns.registry import PatternRegistry, get_pattern_registry


class TestPatternRegistry:
    """Test PatternRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry for each test."""
        return PatternRegistry()

    @pytest.fixture
    def sample_pattern(self):
        """Create sample pattern for testing."""
        return BasePattern(
            id="test_pattern",
            name="Test Pattern",
            category=PatternCategory.STRUCTURAL,
            description="A test pattern for unit tests",
            frequency=5,
            reusability_score=0.8,
            examples=["wizard1", "wizard2"],
        )

    def test_registry_starts_empty(self, registry):
        """New registry should start with no patterns."""
        assert len(registry.list_all()) == 0
        assert registry.get("nonexistent") is None

    def test_register_pattern(self, registry, sample_pattern):
        """Should register a pattern successfully."""
        registry.register(sample_pattern)

        assert len(registry.list_all()) == 1
        assert registry.get("test_pattern") == sample_pattern

    def test_register_duplicate_id_raises_error(self, registry, sample_pattern):
        """Registering pattern with duplicate ID should raise ValueError."""
        registry.register(sample_pattern)

        duplicate = BasePattern(
            id="test_pattern",  # Same ID
            name="Different Pattern",
            category=PatternCategory.INPUT,
            description="Different pattern",
            frequency=3,
            reusability_score=0.7,
        )

        with pytest.raises(ValueError) as exc:
            registry.register(duplicate)

        assert "already registered" in str(exc.value)

    def test_get_existing_pattern(self, registry, sample_pattern):
        """get() should return registered pattern."""
        registry.register(sample_pattern)
        result = registry.get("test_pattern")

        assert result == sample_pattern

    def test_get_nonexistent_pattern(self, registry):
        """get() should return None for nonexistent pattern."""
        result = registry.get("nonexistent")
        assert result is None

    def test_list_all_patterns(self, registry):
        """list_all() should return all registered patterns."""
        pattern1 = BasePattern(
            id="pattern1",
            name="Pattern 1",
            category=PatternCategory.STRUCTURAL,
            description="First pattern",
            frequency=5,
            reusability_score=0.8,
        )
        pattern2 = BasePattern(
            id="pattern2",
            name="Pattern 2",
            category=PatternCategory.INPUT,
            description="Second pattern",
            frequency=3,
            reusability_score=0.7,
        )

        registry.register(pattern1)
        registry.register(pattern2)

        all_patterns = registry.list_all()
        assert len(all_patterns) == 2
        assert pattern1 in all_patterns
        assert pattern2 in all_patterns

    def test_list_by_category(self, registry):
        """list_by_category() should return patterns in specified category."""
        structural = BasePattern(
            id="structural1",
            name="Structural",
            category=PatternCategory.STRUCTURAL,
            description="Structural pattern",
            frequency=5,
            reusability_score=0.8,
        )
        input_pattern = BasePattern(
            id="input1",
            name="Input",
            category=PatternCategory.INPUT,
            description="Input pattern",
            frequency=3,
            reusability_score=0.7,
        )

        registry.register(structural)
        registry.register(input_pattern)

        structural_patterns = registry.list_by_category(PatternCategory.STRUCTURAL)
        assert len(structural_patterns) == 1
        assert structural in structural_patterns
        assert input_pattern not in structural_patterns

        input_patterns = registry.list_by_category(PatternCategory.INPUT)
        assert len(input_patterns) == 1
        assert input_pattern in input_patterns
        assert structural not in input_patterns

    def test_search_by_name_case_insensitive(self, registry):
        """search() should find patterns by name (case-insensitive by default)."""
        pattern = BasePattern(
            id="test",
            name="Linear Flow Pattern",
            category=PatternCategory.STRUCTURAL,
            description="A pattern",
            frequency=5,
            reusability_score=0.8,
        )
        registry.register(pattern)

        # Case insensitive
        results = registry.search("linear")
        assert len(results) == 1
        assert pattern in results

        results = registry.search("LINEAR")
        assert len(results) == 1
        assert pattern in results

    def test_search_by_description(self, registry):
        """search() should find patterns by description."""
        pattern = BasePattern(
            id="test",
            name="Test",
            category=PatternCategory.STRUCTURAL,
            description="Multi-step wizard with approval",
            frequency=5,
            reusability_score=0.8,
        )
        registry.register(pattern)

        results = registry.search("approval")
        assert len(results) == 1
        assert pattern in results

    def test_search_case_sensitive(self, registry):
        """search() should support case-sensitive search."""
        pattern = BasePattern(
            id="test",
            name="Linear Flow",
            category=PatternCategory.STRUCTURAL,
            description="Pattern",
            frequency=5,
            reusability_score=0.8,
        )
        registry.register(pattern)

        # Case sensitive search should not match
        results = registry.search("linear", case_sensitive=True)
        assert len(results) == 0

        # Exact case should match
        results = registry.search("Linear", case_sensitive=True)
        assert len(results) == 1

    def test_search_no_results(self, registry, sample_pattern):
        """search() should return empty list when no matches."""
        registry.register(sample_pattern)

        results = registry.search("nonexistent")
        assert results == []

    def test_recommend_for_healthcare_wizard(self, registry):
        """Should recommend appropriate patterns for healthcare wizard."""
        # Register some patterns
        registry.register(
            BasePattern(
                id="linear_flow",
                name="Linear Flow",
                category=PatternCategory.STRUCTURAL,
                description="Step-by-step wizard",
                frequency=16,
                reusability_score=0.9,
            ),
        )
        registry.register(
            BasePattern(
                id="approval",
                name="Approval",
                category=PatternCategory.VALIDATION,
                description="User approval",
                frequency=16,
                reusability_score=0.95,
            ),
        )
        registry.register(
            BasePattern(
                id="code_analysis_input",
                name="Code Analysis",
                category=PatternCategory.INPUT,
                description="Code analysis",
                frequency=16,
                reusability_score=0.9,
            ),
        )

        recommendations = registry.recommend_for_wizard(wizard_type="domain", domain="healthcare")

        # Should recommend healthcare-specific patterns
        pattern_ids = {p.id for p in recommendations if p is not None}
        assert "linear_flow" in pattern_ids
        assert "approval" in pattern_ids
        # Should NOT recommend coach-specific patterns
        assert "code_analysis_input" not in pattern_ids

    def test_recommend_for_coach_wizard(self, registry):
        """Should recommend appropriate patterns for coach wizard."""
        registry.register(
            BasePattern(
                id="code_analysis_input",
                name="Code Analysis",
                category=PatternCategory.INPUT,
                description="Code analysis",
                frequency=16,
                reusability_score=0.9,
            ),
        )
        registry.register(
            BasePattern(
                id="risk_assessment",
                name="Risk Assessment",
                category=PatternCategory.BEHAVIOR,
                description="Risk analysis",
                frequency=16,
                reusability_score=0.8,
            ),
        )

        recommendations = registry.recommend_for_wizard(wizard_type="coach")

        pattern_ids = {p.id for p in recommendations if p is not None}
        assert "code_analysis_input" in pattern_ids
        assert "risk_assessment" in pattern_ids

    def test_recommend_for_ai_wizard(self, registry):
        """Should recommend appropriate patterns for AI wizard."""
        registry.register(
            BasePattern(
                id="phased_processing",
                name="Phased Processing",
                category=PatternCategory.STRUCTURAL,
                description="Multi-phase pipeline",
                frequency=12,
                reusability_score=0.85,
            ),
        )
        registry.register(
            BasePattern(
                id="context_based_input",
                name="Context Input",
                category=PatternCategory.INPUT,
                description="Flexible context",
                frequency=12,
                reusability_score=0.8,
            ),
        )

        recommendations = registry.recommend_for_wizard(wizard_type="ai")

        pattern_ids = {p.id for p in recommendations if p is not None}
        assert "phased_processing" in pattern_ids
        assert "context_based_input" in pattern_ids

    def test_recommendations_no_duplicates(self, registry):
        """Recommendations should not contain duplicates."""
        registry.register(
            BasePattern(
                id="empathy_level",
                name="Empathy Level",
                category=PatternCategory.EMPATHY,
                description="Empathy config",
                frequency=16,
                reusability_score=1.0,
            ),
        )

        # Empathy level is recommended for all types
        recommendations = registry.recommend_for_wizard(wizard_type="domain", domain="healthcare")

        pattern_ids = [p.id for p in recommendations if p is not None]
        # Should appear only once
        assert pattern_ids.count("empathy_level") == 1

    def test_get_statistics(self, registry):
        """get_statistics() should return registry statistics."""
        registry.register(
            BasePattern(
                id="pattern1",
                name="Pattern 1",
                category=PatternCategory.STRUCTURAL,
                description="Pattern",
                frequency=10,
                reusability_score=0.9,
            ),
        )
        registry.register(
            BasePattern(
                id="pattern2",
                name="Pattern 2",
                category=PatternCategory.INPUT,
                description="Pattern",
                frequency=5,
                reusability_score=0.7,
            ),
        )

        stats = registry.get_statistics()

        assert stats["total_patterns"] == 2
        assert stats["by_category"]["structural"] == 1
        assert stats["by_category"]["input"] == 1
        assert stats["average_reusability"] == 0.8  # (0.9 + 0.7) / 2

        # Top patterns should be sorted by frequency
        assert len(stats["top_patterns"]) == 2
        assert stats["top_patterns"][0]["id"] == "pattern1"  # Higher frequency
        assert stats["top_patterns"][0]["frequency"] == 10


class TestGlobalRegistry:
    """Test global registry functions."""

    def test_get_pattern_registry_singleton(self):
        """get_pattern_registry() should return same instance."""
        registry1 = get_pattern_registry()
        registry2 = get_pattern_registry()

        assert registry1 is registry2

    def test_global_registry_loads_patterns(self):
        """Global registry should have patterns loaded."""
        registry = get_pattern_registry()

        # Should have all 15 patterns loaded
        all_patterns = registry.list_all()
        assert len(all_patterns) >= 15

        # Check some key patterns exist
        assert registry.get("linear_flow") is not None
        assert registry.get("phased_processing") is not None
        assert registry.get("approval") is not None
        assert registry.get("risk_assessment") is not None
        assert registry.get("empathy_level") is not None

    def test_global_registry_pattern_details(self):
        """Global registry patterns should have correct details."""
        registry = get_pattern_registry()

        linear_flow = registry.get("linear_flow")
        assert linear_flow.name == "Linear Flow"
        assert linear_flow.category == PatternCategory.STRUCTURAL
        assert linear_flow.frequency == 16
        assert linear_flow.reusability_score == 0.9

        approval = registry.get("approval")
        assert approval.name == "User Approval"
        assert approval.category == PatternCategory.VALIDATION
        assert approval.frequency == 16
        assert approval.reusability_score == 0.95
