"""Integration tests for the context module.

Tests context management, state compaction, and restoration
with integration to hooks and other framework components.
"""

import pytest

from attune.context import (
    CompactionStateManager,
    CompactState,
    ContextManager,
    SBARHandoff,
)
from attune.context.compaction import PatternSummary


class TestCompactStateIntegration:
    """Test CompactState serialization and restoration."""

    def test_full_state_roundtrip(self):
        """Test complete state serialization and deserialization."""
        original = CompactState(
            user_id="test_user_123",
            trust_level=0.85,
            empathy_level=4,
            detected_patterns=[
                PatternSummary(
                    pattern_type="preference",
                    trigger="code style",
                    action="use concise comments",
                    confidence=0.9,
                    occurrences=5,
                ),
                PatternSummary(
                    pattern_type="workaround",
                    trigger="async error",
                    action="add await keyword",
                    confidence=0.95,
                    occurrences=3,
                ),
            ],
            session_id="session_abc123",
            current_phase="implementation",
            completed_phases=["planning", "design"],
            pending_handoff=SBARHandoff(
                situation="Implementing user authentication",
                background="User requested OAuth support",
                assessment="Core flow complete, need error handling",
                recommendation="Add error handling and tests",
                priority="high",
            ),
            interaction_count=42,
            successful_actions=38,
            failed_actions=4,
            preferences={"response_style": "concise", "code_format": "black"},
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = CompactState.from_dict(data)

        # Verify all fields
        assert restored.user_id == original.user_id
        assert restored.trust_level == original.trust_level
        assert restored.empathy_level == original.empathy_level
        assert len(restored.detected_patterns) == 2
        assert restored.detected_patterns[0].trigger == "code style"
        assert restored.session_id == original.session_id
        assert restored.current_phase == original.current_phase
        assert restored.completed_phases == original.completed_phases
        assert restored.pending_handoff is not None
        assert restored.pending_handoff.situation == "Implementing user authentication"
        assert restored.pending_handoff.priority == "high"
        assert restored.interaction_count == 42
        assert restored.preferences["response_style"] == "concise"

    def test_minimal_state_roundtrip(self):
        """Test minimal state with only required fields."""
        original = CompactState(
            user_id="minimal_user",
            trust_level=0.5,
            empathy_level=1,
        )

        data = original.to_dict()
        restored = CompactState.from_dict(data)

        assert restored.user_id == "minimal_user"
        assert restored.trust_level == 0.5
        assert restored.empathy_level == 1
        assert restored.detected_patterns == []
        assert restored.pending_handoff is None

    def test_format_restoration_prompt(self):
        """Test generating restoration prompt from state."""
        state = CompactState(
            user_id="prompt_user",
            trust_level=0.9,
            empathy_level=4,
            detected_patterns=[
                PatternSummary(
                    pattern_type="preference",
                    trigger="testing",
                    action="use pytest",
                    confidence=0.95,
                    occurrences=10,
                ),
            ],
            session_id="prompt_session",
            current_phase="testing",
            pending_handoff=SBARHandoff(
                situation="Running test suite",
                background="Adding unit tests",
                assessment="80% coverage",
                recommendation="Add edge case tests",
            ),
        )

        prompt = state.format_restoration_prompt()

        assert "prompt_user" in prompt
        assert "0.90" in prompt  # trust level
        assert "Known Patterns" in prompt
        assert "testing" in prompt
        assert "pytest" in prompt
        assert "Pending Handoff" in prompt
        assert "Running test suite" in prompt


class TestSBARHandoffIntegration:
    """Test SBAR handoff functionality."""

    def test_sbar_format_summary(self):
        """Test SBAR summary formatting."""
        handoff = SBARHandoff(
            situation="Debugging memory leak",
            background="User reported high memory usage after 2 hours",
            assessment="Found circular references in cache",
            recommendation="Implement weak references for cache",
            priority="high",
        )

        summary = handoff.format_summary()

        assert "**Priority**: HIGH" in summary
        assert "**Situation**: Debugging memory leak" in summary
        assert "**Background**: User reported" in summary
        assert "**Assessment**: Found circular" in summary
        assert "**Recommendation**: Implement weak" in summary

    def test_sbar_metadata_preserved(self):
        """Test that SBAR metadata is preserved through serialization."""
        handoff = SBARHandoff(
            situation="Test situation",
            background="Test background",
            assessment="Test assessment",
            recommendation="Test recommendation",
            metadata={
                "files_modified": ["a.py", "b.py"],
                "test_coverage": 85.5,
                "related_issues": ["#123", "#456"],
            },
        )

        data = handoff.to_dict()
        restored = SBARHandoff.from_dict(data)

        assert restored.metadata["files_modified"] == ["a.py", "b.py"]
        assert restored.metadata["test_coverage"] == 85.5


class TestCompactionStateManagerIntegration:
    """Test CompactionStateManager persistence."""

    @pytest.fixture
    def storage_dir(self, tmp_path):
        """Create temporary storage directory."""
        return tmp_path / "compact_states"

    @pytest.fixture
    def manager(self, storage_dir):
        """Create state manager."""
        return CompactionStateManager(storage_dir=storage_dir)

    def test_save_and_load_state(self, manager):
        """Test saving and loading state."""
        state = CompactState(
            user_id="persistence_user",
            trust_level=0.75,
            empathy_level=3,
            current_phase="coding",
        )

        # Save
        path = manager.save_state(state)
        assert path.exists()
        assert "persistence_user" in str(path)

        # Load using load_latest_state
        loaded = manager.load_latest_state("persistence_user")
        assert loaded is not None
        assert loaded.user_id == "persistence_user"
        assert loaded.trust_level == 0.75
        assert loaded.current_phase == "coding"

    def test_load_latest_state(self, manager):
        """Test getting latest state for user."""
        user_id = "latest_test_user"

        # Save multiple states
        for i in range(3):
            state = CompactState(
                user_id=user_id,
                trust_level=0.5 + (i * 0.1),
                empathy_level=i + 1,
            )
            manager.save_state(state)

        # Get latest using load_latest_state
        latest = manager.load_latest_state(user_id)
        assert latest is not None
        assert latest.empathy_level == 3  # Last saved
        assert latest.trust_level == pytest.approx(0.7, abs=0.01)

    def test_get_all_states(self, manager):
        """Test listing all states for a user."""
        user_id = "list_test_user"

        # Save states
        for i in range(3):
            state = CompactState(
                user_id=user_id,
                trust_level=0.5,
                empathy_level=i + 1,
            )
            manager.save_state(state)

        # List
        states = manager.get_all_states(user_id)
        assert len(states) == 3

    def test_max_states_cleanup(self, storage_dir):
        """Test that old states are cleaned up when max is exceeded."""
        manager = CompactionStateManager(storage_dir=storage_dir, max_states_per_user=3)
        user_id = "cleanup_user"

        # Save more than max
        for i in range(5):
            state = CompactState(
                user_id=user_id,
                trust_level=0.5,
                empathy_level=i + 1,
            )
            manager.save_state(state)

        # Should only have max states
        states = manager.get_all_states(user_id)
        assert len(states) <= 3

    def test_nonexistent_user_returns_none(self, manager):
        """Test that nonexistent user returns None."""
        latest = manager.load_latest_state("nonexistent_user")
        assert latest is None


class TestContextManagerIntegration:
    """Test ContextManager orchestration."""

    @pytest.fixture
    def context_manager(self, tmp_path):
        """Create context manager with temp storage."""
        return ContextManager(storage_dir=tmp_path / "context")

    def test_session_lifecycle(self, context_manager):
        """Test full session lifecycle."""
        context_manager.session_id = "lifecycle_test"
        context_manager.current_phase = "planning"

        # Complete phases
        context_manager.complete_phase("planning")
        assert "planning" in context_manager._completed_phases

        context_manager.current_phase = "implementation"
        context_manager.complete_phase("implementation")
        assert "implementation" in context_manager._completed_phases

    def test_handoff_creation_and_retrieval(self, context_manager):
        """Test creating and retrieving handoff."""
        handoff = context_manager.set_handoff(
            situation="Testing handoff",
            background="Integration test",
            assessment="Working correctly",
            recommendation="Continue testing",
            priority="high",
        )

        assert handoff.situation == "Testing handoff"
        assert handoff.priority == "high"

        # Get handoff - access via private attribute
        retrieved = context_manager._pending_handoff
        assert retrieved is not None
        assert retrieved.situation == "Testing handoff"

    def test_clear_handoff(self, context_manager):
        """Test clearing pending handoff."""
        context_manager.set_handoff(
            situation="To be cleared",
            background="Test",
            assessment="Test",
            recommendation="Test",
        )

        context_manager.clear_handoff()
        assert context_manager._pending_handoff is None

    def test_state_restoration_roundtrip(self, context_manager):
        """Test saving and restoring state through ContextManager."""
        user_id = "roundtrip_user"

        # Set up state
        context_manager.session_id = "roundtrip_session"
        context_manager.current_phase = "testing"
        context_manager.complete_phase("planning")
        context_manager.set_handoff(
            situation="Testing roundtrip",
            background="Full cycle test",
            assessment="State should persist",
            recommendation="Verify restoration",
        )

        # Create state and save
        state = CompactState(
            user_id=user_id,
            trust_level=0.8,
            empathy_level=4,
            session_id=context_manager.session_id,
            current_phase=context_manager.current_phase,
            completed_phases=list(context_manager._completed_phases),
            pending_handoff=context_manager._pending_handoff,
        )

        context_manager._state_manager.save_state(state)

        # Create new manager and restore
        new_manager = ContextManager(storage_dir=context_manager._state_manager.storage_dir)

        restored = new_manager.restore_state(user_id)

        assert restored is not None
        assert restored.trust_level == 0.8
        assert restored.session_id == "roundtrip_session"
        assert "planning" in restored.completed_phases
        assert restored.pending_handoff is not None


class TestContextWithHooksIntegration:
    """Test context management with hook system."""

    def test_pre_compact_hook_saves_state(self, tmp_path):
        """Test that pre-compact hook triggers state save."""
        from attune.hooks.config import HookEvent
        from attune.hooks.registry import HookRegistry

        context_manager = ContextManager(storage_dir=tmp_path / "states")
        hook_registry = HookRegistry()
        states_saved = []

        def pre_compact_handler(
            user_id="unknown",
            trust_level=0.5,
            empathy_level=1,
            session_id="",
            **kwargs,
        ):
            # Save state on pre-compact
            state = CompactState(
                user_id=user_id,
                trust_level=trust_level,
                empathy_level=empathy_level,
                session_id=session_id,
            )
            path = context_manager._state_manager.save_state(state)
            states_saved.append(path)
            return {"success": True, "state_path": str(path)}

        hook_registry.register(
            event=HookEvent.PRE_COMPACT,
            handler=pre_compact_handler,
        )

        # Fire pre-compact
        hook_registry.fire_sync(
            HookEvent.PRE_COMPACT,
            {
                "user_id": "hook_user",
                "trust_level": 0.9,
                "empathy_level": 4,
                "session_id": "hook_session",
            },
        )

        assert len(states_saved) == 1
        assert states_saved[0].exists()

    def test_session_end_triggers_evaluation(self, tmp_path):
        """Test that session end can trigger learning evaluation."""
        from attune.hooks.config import HookEvent
        from attune.hooks.registry import HookRegistry

        hook_registry = HookRegistry()
        evaluation_results = []

        def session_end_handler(user_id=None, interaction_count=0, **kwargs):
            # Simulate evaluation
            result = {
                "user_id": user_id,
                "interactions": interaction_count,
                "evaluated": True,
            }
            evaluation_results.append(result)
            return {"success": True, "evaluation": result}

        hook_registry.register(
            event=HookEvent.SESSION_END,
            handler=session_end_handler,
        )

        # Fire session end
        hook_registry.fire_sync(
            HookEvent.SESSION_END,
            {"user_id": "eval_user", "interaction_count": 25},
        )

        assert len(evaluation_results) == 1
        assert evaluation_results[0]["evaluated"] is True


class TestPatternSummaryIntegration:
    """Test PatternSummary in context flow."""

    def test_patterns_in_compact_state(self):
        """Test patterns embedded in compact state."""
        patterns = [
            PatternSummary(
                pattern_type="preference",
                trigger="imports",
                action="sort alphabetically",
                confidence=0.88,
                occurrences=12,
            ),
            PatternSummary(
                pattern_type="workaround",
                trigger="circular import",
                action="use TYPE_CHECKING",
                confidence=0.95,
                occurrences=3,
            ),
        ]

        state = CompactState(
            user_id="pattern_user",
            trust_level=0.8,
            empathy_level=3,
            detected_patterns=patterns,
        )

        # Serialize and restore
        data = state.to_dict()
        restored = CompactState.from_dict(data)

        assert len(restored.detected_patterns) == 2
        assert restored.detected_patterns[0].confidence == 0.88
        assert restored.detected_patterns[1].occurrences == 3

    def test_patterns_in_restoration_prompt(self):
        """Test patterns appear in restoration prompt."""
        patterns = [
            PatternSummary(
                pattern_type="preference",
                trigger="error handling",
                action="always log exceptions",
                confidence=0.92,
                occurrences=8,
            ),
        ]

        state = CompactState(
            user_id="prompt_pattern_user",
            trust_level=0.7,
            empathy_level=3,
            detected_patterns=patterns,
        )

        prompt = state.format_restoration_prompt()

        assert "Known Patterns" in prompt
        assert "error handling" in prompt
        assert "always log exceptions" in prompt
        assert "92%" in prompt  # confidence formatted as percentage


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_state_restoration(self, tmp_path):
        """Test restoring state for user with no saved states."""
        manager = ContextManager(storage_dir=tmp_path / "empty")
        state = manager.restore_state("nonexistent_user")
        assert state is None

    def test_corrupted_state_file_handled(self, tmp_path):
        """Test handling of corrupted state files."""
        storage_dir = tmp_path / "corrupt"
        storage_dir.mkdir(parents=True)

        # Create corrupted file
        user_dir = storage_dir / "corrupt_user"
        user_dir.mkdir()
        (user_dir / "compact_20250123.json").write_text("{ invalid json }")

        manager = CompactionStateManager(storage_dir=storage_dir)
        # Should handle gracefully
        manager.load_latest_state("corrupt_user")
        # Either returns None or raises appropriate error
        # depending on implementation

    def test_large_pattern_list_truncated_in_prompt(self):
        """Test that large pattern lists are truncated in prompts."""
        patterns = [
            PatternSummary(
                pattern_type="preference",
                trigger=f"trigger_{i}",
                action=f"action_{i}",
                confidence=0.8,
                occurrences=i,
            )
            for i in range(20)
        ]

        state = CompactState(
            user_id="many_patterns_user",
            trust_level=0.7,
            empathy_level=3,
            detected_patterns=patterns,
        )

        prompt = state.format_restoration_prompt()

        # Should truncate to reasonable number (5 by default)
        pattern_count = prompt.count("→")
        assert pattern_count <= 5
