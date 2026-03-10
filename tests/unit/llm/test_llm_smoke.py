"""Smoke tests for llm.

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
        import attune.llm

        assert attune.llm is not None

    def test_empathy_level_imports(self) -> None:
        """Test that EmpathyLevel imports."""
        from attune.llm import EmpathyLevel

        assert EmpathyLevel is not None

    def test_state_classes_import(self) -> None:
        """Test that state classes import."""
        from attune.llm import CollaborationState, PatternType, UserPattern

        assert CollaborationState is not None
        assert PatternType is not None
        assert UserPattern is not None

    def test_provider_classes_import(self) -> None:
        """Test that provider base classes import."""
        from attune.llm import BaseLLMProvider, LLMResponse

        assert BaseLLMProvider is not None
        assert LLMResponse is not None


@pytest.mark.unit
class TestEnums:
    """Verify enums have expected values."""

    def test_empathy_level_values(self) -> None:
        """Test EmpathyLevel enum values."""
        from attune.llm import EmpathyLevel

        assert EmpathyLevel.REACTIVE == 1
        assert EmpathyLevel.ANTICIPATORY == 4

    def test_empathy_level_description(self) -> None:
        """Test EmpathyLevel.get_description works."""
        from attune.llm import EmpathyLevel

        desc = EmpathyLevel.get_description(1)
        assert "Reactive" in desc

    def test_pattern_type_values(self) -> None:
        """Test PatternType enum values."""
        from attune.llm import PatternType

        assert PatternType.SEQUENTIAL.value == "sequential"
        assert PatternType.PREFERENCE.value == "preference"


@pytest.mark.unit
class TestInstantiation:
    """Verify dataclasses can be instantiated."""

    def test_llm_response_creation(self) -> None:
        """Test LLMResponse dataclass creation."""
        from attune.llm import LLMResponse

        response = LLMResponse(
            content="Hello",
            model="test-model",
            tokens_used=10,
            finish_reason="end_turn",
            metadata={},
        )
        assert response.content == "Hello"
        assert response.tokens_used == 10

    def test_collaboration_state_creation(self) -> None:
        """Test CollaborationState dataclass creation."""
        from attune.llm import CollaborationState

        state = CollaborationState(user_id="test-user")
        assert state.user_id == "test-user"

    def test_user_pattern_should_act(self) -> None:
        """Test UserPattern.should_act method."""
        from datetime import datetime

        from attune.llm import PatternType, UserPattern

        pattern = UserPattern(
            pattern_type=PatternType.PREFERENCE,
            trigger="test",
            action="do something",
            confidence=0.9,
            occurrences=5,
            last_seen=datetime.now(),
        )
        assert pattern.should_act(trust_level=0.8) is True
        assert pattern.should_act(trust_level=0.3) is False
