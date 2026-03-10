"""Smoke tests for attune.llm module."""


class TestLLMImports:
    """Verify the llm package exports are importable."""

    def test_import_package(self):
        """Test that the llm package imports cleanly."""
        from attune.llm import (
            CollaborationState,
            EmpathyLevel,
            PatternType,
        )

        assert EmpathyLevel is not None
        assert CollaborationState is not None
        assert PatternType is not None

    def test_empathy_level_enum(self):
        """Test EmpathyLevel enum values."""
        from attune.llm.levels import EmpathyLevel

        assert EmpathyLevel.REACTIVE == 1
        assert EmpathyLevel.GUIDED == 2
        assert EmpathyLevel.PROACTIVE == 3
        assert EmpathyLevel.ANTICIPATORY == 4
        assert EmpathyLevel.SYSTEMS == 5

    def test_empathy_level_description(self):
        """Test EmpathyLevel.get_description returns strings."""
        from attune.llm.levels import EmpathyLevel

        desc = EmpathyLevel.get_description(1)
        assert "Reactive" in desc
        assert EmpathyLevel.get_description(99) == "Unknown level"

    def test_pattern_type_enum(self):
        """Test PatternType enum values."""
        from attune.llm.state import PatternType

        assert PatternType.SEQUENTIAL.value == "sequential"
        assert PatternType.TEMPORAL.value == "temporal"
        assert PatternType.PREFERENCE.value == "preference"

    def test_user_pattern_should_act(self):
        """Test UserPattern.should_act logic."""
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="test",
            action="do something",
            confidence=0.9,
            occurrences=5,
            last_seen=datetime.now(),
        )
        # High confidence + high trust => should act
        assert pattern.should_act(trust_level=0.8) is True
        # High confidence + low trust => should not act
        assert pattern.should_act(trust_level=0.3) is False
