"""Tests for attune.core"""

import pytest

from attune.core import CollaborationState, EmpathyOS
from attune.memory.types import AccessTier


class TestCollaborationState:
    """Tests for CollaborationState class."""

    def test_initialization(self):
        """Test CollaborationState initialization."""
        state = CollaborationState()

        assert state is not None
        assert state.trust_level == 0.5  # Starts neutral
        assert isinstance(state.shared_context, dict)
        assert state.successful_interventions == 0
        assert state.failed_interventions == 0
        assert state.total_interactions == 0
        assert isinstance(state.trust_trajectory, list)

    def test_update_trust_success(self):
        """Test update_trust with successful outcome."""
        state = CollaborationState()
        initial_trust = state.trust_level

        state.update_trust("success")

        assert state.trust_level > initial_trust
        assert state.successful_interventions == 1
        assert state.failed_interventions == 0
        assert state.total_interactions == 1
        assert len(state.trust_trajectory) == 1

    def test_update_trust_failure(self):
        """Test update_trust with failed outcome."""
        state = CollaborationState()
        initial_trust = state.trust_level

        state.update_trust("failure")

        assert state.trust_level < initial_trust
        assert state.successful_interventions == 0
        assert state.failed_interventions == 1
        assert state.total_interactions == 1

    def test_update_trust_clamping_upper(self):
        """Test that trust level is clamped to maximum 1.0."""
        state = CollaborationState()

        # Force trust to very high value
        for _ in range(100):
            state.update_trust("success")

        assert state.trust_level <= 1.0

    def test_update_trust_clamping_lower(self):
        """Test that trust level is clamped to minimum 0.0."""
        state = CollaborationState()

        # Force trust to very low value
        for _ in range(100):
            state.update_trust("failure")

        assert state.trust_level >= 0.0

    def test_update_trust_trajectory_tracking(self):
        """Test that trust trajectory is tracked over time."""
        state = CollaborationState()

        state.update_trust("success")
        state.update_trust("success")
        state.update_trust("failure")

        assert len(state.trust_trajectory) == 3
        # Trust should go up, up, down
        assert state.trust_trajectory[1] > state.trust_trajectory[0]
        assert state.trust_trajectory[2] < state.trust_trajectory[1]


class TestEmpathyOS:
    """Tests for EmpathyOS class."""

    def test_initialization_basic(self):
        """Test EmpathyOS initialization with basic params."""
        empathy = EmpathyOS(user_id="test_user")

        assert empathy is not None
        assert empathy.user_id == "test_user"
        assert empathy.target_level == 3  # Default
        assert empathy.confidence_threshold == 0.75
        assert isinstance(empathy.collaboration_state, CollaborationState)
        assert empathy.current_empathy_level == 1

    def test_initialization_with_custom_params(self):
        """Test EmpathyOS initialization with custom parameters."""
        empathy = EmpathyOS(
            user_id="custom_user",
            target_level=4,
            confidence_threshold=0.9,
            access_tier=AccessTier.STEWARD,
        )

        assert empathy.user_id == "custom_user"
        assert empathy.target_level == 4
        assert empathy.confidence_threshold == 0.9
        assert empathy.credentials.tier == AccessTier.STEWARD

    def test_memory_property_lazy_initialization(self):
        """Test that memory property is lazily initialized."""
        empathy = EmpathyOS(user_id="test_user")

        # Memory should not be initialized yet
        assert empathy._unified_memory is None

        # Access memory property
        memory = empathy.memory

        # Now it should be initialized
        assert memory is not None
        assert empathy._unified_memory is not None

        # Second access should return same instance
        memory2 = empathy.memory
        assert memory is memory2

    def test_persist_pattern(self, tmp_path):
        """Test persist_pattern convenience method."""
        import os

        os.environ["EMPATHY_STORAGE_DIR"] = str(tmp_path)

        empathy = EmpathyOS(user_id="test_user")

        result = empathy.persist_pattern(
            content="Test pattern content",
            pattern_type="algorithm",
        )

        assert result is not None
        assert "pattern_id" in result
        assert "classification" in result

    def test_recall_pattern(self, tmp_path):
        """Test recall_pattern convenience method."""
        import os

        os.environ["EMPATHY_STORAGE_DIR"] = str(tmp_path)

        empathy = EmpathyOS(user_id="test_user")

        # First persist a pattern
        persist_result = empathy.persist_pattern(
            content="Test recall content",
            pattern_type="protocol",
        )

        pattern_id = persist_result["pattern_id"]

        # Then recall it
        recalled = empathy.recall_pattern(pattern_id)

        # Verify pattern was recalled successfully
        assert recalled is not None
        assert isinstance(recalled, dict)
        assert recalled.get("content") == "Test recall content"

    def test_stash_and_retrieve(self, tmp_path):
        """Test stash and retrieve convenience methods."""
        import os

        os.environ["EMPATHY_STORAGE_DIR"] = str(tmp_path)

        empathy = EmpathyOS(user_id="test_user")

        # Stash some data
        result = empathy.stash("test_key", {"data": "test_value"}, ttl_seconds=3600)

        assert result is True

        # Retrieve it
        retrieved = empathy.retrieve("test_key")

        assert retrieved is not None
        assert retrieved["data"] == "test_value"

    def test_stash_nonexistent_key(self, tmp_path):
        """Test retrieving non-existent key returns None."""
        import os

        os.environ["EMPATHY_STORAGE_DIR"] = str(tmp_path)

        empathy = EmpathyOS(user_id="test_user")

        result = empathy.retrieve("nonexistent_key")

        assert result is None

    def test_has_shared_library_with_library(self):
        """Test has_shared_library returns True when library is configured."""
        from attune.pattern_library import PatternLibrary

        library = PatternLibrary()
        empathy = EmpathyOS(user_id="test_user", shared_library=library)

        assert empathy.has_shared_library() is True

    def test_has_shared_library_without_library(self):
        """Test has_shared_library returns False when no library configured."""
        empathy = EmpathyOS(user_id="test_user")

        assert empathy.has_shared_library() is False

    def test_contribute_pattern(self):
        """Test contributing a pattern to shared library."""
        from attune.pattern_library import Pattern, PatternLibrary

        library = PatternLibrary()
        empathy = EmpathyOS(user_id="test_agent", shared_library=library)

        pattern = Pattern(
            id="contrib_test",
            agent_id="test_agent",
            pattern_type="algorithm",
            name="Contributed Pattern",
            description="Test pattern contribution",
        )

        empathy.contribute_pattern(pattern)

        # Verify pattern was added to library
        assert "contrib_test" in library.patterns
        assert library.patterns["contrib_test"].name == "Contributed Pattern"

    def test_contribute_pattern_no_library_raises(self):
        """Test contributing pattern without shared library raises RuntimeError."""
        from attune.pattern_library import Pattern

        empathy = EmpathyOS(user_id="test_agent")  # No shared library

        pattern = Pattern(
            id="test",
            agent_id="test_agent",
            pattern_type="test",
            name="Test",
            description="Test",
        )

        with pytest.raises(RuntimeError, match="No shared library configured"):
            empathy.contribute_pattern(pattern)

    def test_query_patterns(self):
        """Test querying patterns from shared library."""
        from attune.pattern_library import Pattern, PatternLibrary

        library = PatternLibrary()
        empathy = EmpathyOS(user_id="test_agent", shared_library=library)

        # Add a pattern to the library
        pattern = Pattern(
            id="query_test",
            agent_id="other_agent",
            pattern_type="algorithm",
            name="Query Test",
            description="Test pattern for querying",
            confidence=0.9,
        )
        library.contribute_pattern("other_agent", pattern)

        # Query patterns
        context = {"task": "testing", "type": "algorithm"}
        matches = empathy.query_patterns(context, min_confidence=0.7)

        # Should be able to query successfully
        assert isinstance(matches, list)

    def test_query_patterns_no_library_raises(self):
        """Test querying patterns without shared library raises RuntimeError."""
        empathy = EmpathyOS(user_id="test_agent")  # No shared library

        with pytest.raises(RuntimeError, match="No shared library configured"):
            empathy.query_patterns({"task": "test"})

    def test_async_context_manager_enter(self):
        """Test async context manager __aenter__."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")

        async def test_enter():
            async with empathy as agent:
                assert agent is empathy
                assert agent.user_id == "test_user"

        asyncio.run(test_enter())

    def test_async_context_manager_exit(self):
        """Test async context manager __aexit__ cleanup."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")

        async def test_exit():
            async with empathy:
                pass  # Context should clean up on exit
            # No exceptions means cleanup succeeded

        asyncio.run(test_exit())

    def test_async_context_manager_exception_propagation(self):
        """Test that exceptions are propagated from async context manager."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")

        async def test_exception():
            with pytest.raises(ValueError, match="Test error"):
                async with empathy:
                    raise ValueError("Test error")

        asyncio.run(test_exception())

    def test_level_1_reactive_basic(self):
        """Test Level 1 reactive empathy with basic request."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")

        async def test_reactive():
            result = await empathy.level_1_reactive("Help me debug this code")

            assert result["level"] == 1
            assert result["type"] == "reactive"
            assert "result" in result
            assert "reasoning" in result
            assert empathy.current_empathy_level == 1

        asyncio.run(test_reactive())

    def test_level_1_reactive_empty_request_raises(self):
        """Test Level 1 with empty request raises ValidationError."""
        import asyncio

        from attune.exceptions import ValidationError

        empathy = EmpathyOS(user_id="test_user")

        async def test_empty():
            with pytest.raises(ValidationError, match="cannot be empty"):
                await empathy.level_1_reactive("")

        asyncio.run(test_empty())

    def test_level_1_reactive_invalid_type_raises(self):
        """Test Level 1 with non-string request raises ValidationError."""
        import asyncio

        from attune.exceptions import ValidationError

        empathy = EmpathyOS(user_id="test_user")

        async def test_invalid_type():
            with pytest.raises(ValidationError, match="must be a string"):
                await empathy.level_1_reactive(123)

        asyncio.run(test_invalid_type())

    def test_level_2_guided_basic(self):
        """Test Level 2 guided empathy with basic request."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")

        async def test_guided():
            result = await empathy.level_2_guided("I need help with my code")

            assert result["level"] == 2
            assert result["type"] == "guided"
            assert empathy.current_empathy_level == 2

        asyncio.run(test_guided())

    def test_level_2_guided_validation(self):
        """Test Level 2 input validation."""
        import asyncio

        from attune.exceptions import ValidationError

        empathy = EmpathyOS(user_id="test_user")

        async def test_validation():
            # Empty request
            with pytest.raises(ValidationError, match="cannot be empty"):
                await empathy.level_2_guided("")

            # Non-string request
            with pytest.raises(ValidationError, match="must be a string"):
                await empathy.level_2_guided(None)

        asyncio.run(test_validation())

    def test_collaboration_state_updates_on_interaction(self):
        """Test that collaboration state updates during interactions."""
        import asyncio

        empathy = EmpathyOS(user_id="test_user")
        initial_interactions = empathy.collaboration_state.total_interactions

        async def test_state_update():
            await empathy.level_1_reactive("Test request")

            # Verify interaction was recorded
            assert empathy.collaboration_state.total_interactions == initial_interactions + 1

        asyncio.run(test_state_update())
