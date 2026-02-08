"""Tests for the ContextManager class."""

import tempfile
import time
from datetime import datetime

from attune_llm.context.compaction import CompactState
from attune_llm.context.manager import ContextManager
from attune_llm.state import CollaborationState, PatternType, UserPattern


class TestContextManager:
    """Tests for ContextManager class."""

    def test_init_default(self):
        """Test default initialization."""
        manager = ContextManager()

        assert manager._token_threshold == 50
        assert manager._auto_save is True
        assert manager.session_id == ""
        assert manager.current_phase == ""

    def test_init_custom(self):
        """Test custom initialization."""
        manager = ContextManager(
            storage_dir="/tmp/test",
            token_threshold=75,
            auto_save=False,
        )

        assert manager._token_threshold == 75
        assert manager._auto_save is False

    def test_session_id_property(self):
        """Test session ID property."""
        manager = ContextManager()

        manager.session_id = "test-session-123"
        assert manager.session_id == "test-session-123"

    def test_current_phase_property(self):
        """Test current phase property."""
        manager = ContextManager()

        manager.current_phase = "implementation"
        assert manager.current_phase == "implementation"

    def test_complete_phase(self):
        """Test completing phases."""
        manager = ContextManager()

        manager.complete_phase("planning")
        manager.complete_phase("design")
        manager.complete_phase("planning")  # Duplicate, should not add

        assert "planning" in manager._completed_phases
        assert "design" in manager._completed_phases
        assert len(manager._completed_phases) == 2

    def test_set_handoff(self):
        """Test setting SBAR handoff."""
        manager = ContextManager()

        handoff = manager.set_handoff(
            situation="Working on feature",
            background="User requested new button",
            assessment="50% complete",
            recommendation="Continue implementation",
            priority="high",
            extra_field="extra_value",
        )

        assert handoff.situation == "Working on feature"
        assert handoff.priority == "high"
        assert handoff.metadata["extra_field"] == "extra_value"
        assert manager._pending_handoff is handoff

    def test_clear_handoff(self):
        """Test clearing handoff."""
        manager = ContextManager()

        manager.set_handoff(
            situation="Test",
            background="Test",
            assessment="Test",
            recommendation="Test",
        )
        assert manager._pending_handoff is not None

        manager.clear_handoff()
        assert manager._pending_handoff is None

    def test_should_suggest_compaction_by_tokens(self):
        """Test compaction suggestion based on token usage."""
        manager = ContextManager(token_threshold=50)

        assert manager.should_suggest_compaction(40) is False
        assert manager.should_suggest_compaction(50) is True
        assert manager.should_suggest_compaction(75) is True

    def test_should_suggest_compaction_by_messages(self):
        """Test compaction suggestion based on message count."""
        manager = ContextManager(token_threshold=80)

        # Token usage below threshold but high message count
        assert manager.should_suggest_compaction(40, message_count=30) is False
        assert manager.should_suggest_compaction(40, message_count=50) is True
        assert manager.should_suggest_compaction(40, message_count=100) is True

    def test_get_compaction_message(self):
        """Test generating compaction message."""
        manager = ContextManager()

        message = manager.get_compaction_message(75.5)

        assert "76%" in message  # 75.5 rounds to 76
        assert "/compact" in message
        assert "preserved" in message

    def test_extract_compact_state(self):
        """Test extracting compact state from collaboration state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            manager.session_id = "extract-session"
            manager.current_phase = "testing"
            manager._completed_phases = ["planning"]

            # Create collaboration state
            collab_state = CollaborationState(user_id="test_user")
            collab_state.trust_level = 0.8
            collab_state.current_level = 4
            collab_state.successful_actions = 10
            collab_state.failed_actions = 2
            collab_state.preferences = {"verbosity": "high", "style": "formal"}

            # Add a pattern
            pattern = UserPattern(
                pattern_type=PatternType.PREFERENCE,
                trigger="code review",
                action="detailed feedback",
                confidence=0.85,
                occurrences=15,
                last_seen=datetime.now(),
            )
            collab_state.add_pattern(pattern)

            # Add some interactions
            collab_state.add_interaction("user", "Hello", 2)
            collab_state.add_interaction("assistant", "Hi there!", 2)

            # Extract
            compact = manager.extract_compact_state(collab_state)

            assert compact.user_id == "test_user"
            assert compact.trust_level == 0.8
            assert compact.empathy_level == 4
            assert compact.session_id == "extract-session"
            assert compact.current_phase == "testing"
            assert "planning" in compact.completed_phases
            assert compact.interaction_count == 2
            assert compact.successful_actions == 10
            assert compact.failed_actions == 2
            assert len(compact.detected_patterns) == 1
            assert compact.detected_patterns[0].trigger == "code review"

    def test_save_and_restore_state(self):
        """Test full save and restore cycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            manager.session_id = "save-restore-session"
            manager.current_phase = "implementation"
            manager._completed_phases = ["planning", "design"]

            manager.set_handoff(
                situation="Working on tests",
                background="Feature nearly complete",
                assessment="Good progress",
                recommendation="Add edge case tests",
            )

            # Create collaboration state
            collab_state = CollaborationState(user_id="save_user")
            collab_state.trust_level = 0.75
            collab_state.current_level = 3

            # Save
            saved_path = manager.save_for_compaction(collab_state)
            assert saved_path.exists()

            # Create new manager to simulate restart
            new_manager = ContextManager(storage_dir=tmpdir)

            # Restore
            restored = new_manager.restore_state("save_user")

            assert restored is not None
            assert restored.user_id == "save_user"
            assert restored.trust_level == 0.75
            assert restored.empathy_level == 3
            assert restored.session_id == "save-restore-session"
            assert new_manager.session_id == "save-restore-session"
            assert new_manager.current_phase == "implementation"
            assert "planning" in new_manager._completed_phases
            assert new_manager._pending_handoff is not None
            assert new_manager._pending_handoff.situation == "Working on tests"

    def test_restore_by_session(self):
        """Test restoring by session ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)

            # Save multiple sessions with delay to ensure distinct filenames
            # (some platforms have low-resolution timestamps that can collide)
            manager.session_id = "session-alpha"
            collab1 = CollaborationState(user_id="session_user")
            collab1.trust_level = 0.6
            collab1.current_level = 2
            manager.save_for_compaction(collab1)

            time.sleep(0.05)  # Ensure distinct timestamp on all platforms

            manager.session_id = "session-beta"
            collab2 = CollaborationState(user_id="session_user")
            collab2.trust_level = 0.8
            collab2.current_level = 4
            manager.save_for_compaction(collab2)

            # Restore specific session
            new_manager = ContextManager(storage_dir=tmpdir)
            restored = new_manager.restore_by_session("session-alpha")

            assert restored is not None
            assert restored.session_id == "session-alpha"
            assert restored.trust_level == 0.6

    def test_generate_restoration_prompt(self):
        """Test generating restoration prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            manager.session_id = "prompt-session"

            collab_state = CollaborationState(user_id="prompt_user")
            collab_state.trust_level = 0.85
            collab_state.current_level = 4
            manager.save_for_compaction(collab_state)

            # New manager
            new_manager = ContextManager(storage_dir=tmpdir)
            prompt = new_manager.generate_restoration_prompt("prompt_user")

            assert prompt is not None
            assert "## Session Restoration" in prompt
            assert "prompt_user" in prompt
            assert "0.85" in prompt

    def test_generate_restoration_prompt_no_state(self):
        """Test restoration prompt when no state exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            prompt = manager.generate_restoration_prompt("nonexistent_user")

            assert prompt is None

    def test_apply_state_to_collaboration(self):
        """Test applying compact state to collaboration state."""
        manager = ContextManager()

        compact = CompactState(
            user_id="apply_user",
            trust_level=0.9,
            empathy_level=5,
            successful_actions=50,
            failed_actions=5,
            preferences={"style": "concise"},
        )

        collab = CollaborationState(user_id="apply_user")
        collab.trust_level = 0.5  # Will be overwritten
        collab.current_level = 1  # Will be overwritten

        manager.apply_state_to_collaboration(compact, collab)

        assert collab.trust_level == 0.9
        assert collab.current_level == 5
        assert collab.successful_actions == 50
        assert collab.failed_actions == 5
        assert collab.preferences["style"] == "concise"

    def test_get_state_summary(self):
        """Test getting state summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            manager.session_id = "summary-session"

            collab = CollaborationState(user_id="summary_user")
            collab.trust_level = 0.7
            collab.current_level = 3

            pattern = UserPattern(
                pattern_type=PatternType.PREFERENCE,
                trigger="test",
                action="test",
                confidence=0.8,
                occurrences=5,
                last_seen=datetime.now(),
            )
            collab.add_pattern(pattern)

            manager.save_for_compaction(collab)

            summary = manager.get_state_summary("summary_user")

            assert summary is not None
            assert summary["user_id"] == "summary_user"
            assert summary["states_count"] == 1
            assert summary["latest_trust_level"] == 0.7
            assert summary["latest_empathy_level"] == 3
            assert summary["patterns_count"] == 1

    def test_get_state_summary_no_states(self):
        """Test getting summary when no states exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)
            summary = manager.get_state_summary("nonexistent")

            assert summary is None

    def test_clear_states(self):
        """Test clearing states."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ContextManager(storage_dir=tmpdir)

            # Save some states with delays to ensure distinct filenames
            # (some platforms have low-resolution timestamps that can collide)
            for _i in range(3):
                collab = CollaborationState(user_id="clear_user")
                manager.save_for_compaction(collab)
                time.sleep(0.05)  # Ensure distinct timestamp on all platforms

            # Clear
            cleared = manager.clear_states("clear_user")
            assert cleared == 3

            # Verify cleared
            summary = manager.get_state_summary("clear_user")
            assert summary is None

    def test_extract_key_preferences(self):
        """Test preference extraction logic."""
        manager = ContextManager()

        preferences = {
            "response_style": "detailed",
            "code_style": "pythonic",
            "verbosity": "high",
            "random_pref": "value",
            "complex_nested": {"a": {"b": "c"}},  # Should be skipped
            "simple_list": ["a", "b"],  # Should be included
            "long_list": list(range(100)),  # Should be skipped (too long)
        }

        extracted = manager._extract_key_preferences(preferences, max_items=5)

        assert "response_style" in extracted
        assert "code_style" in extracted
        assert "verbosity" in extracted
        assert "simple_list" in extracted
        assert "complex_nested" not in extracted
        assert "long_list" not in extracted
        assert len(extracted) <= 5
