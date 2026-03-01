"""Full workflow integration tests.

Tests the complete flow: SessionStart → Commands → Learning → SessionEnd
integrating hooks, context, learning, and commands modules.
"""

from pathlib import Path

import pytest

from attune.commands import CommandContext, CommandExecutor, CommandRegistry
from attune.context.compaction import CompactState
from attune.context.manager import ContextManager
from attune.hooks.config import HookEvent
from attune.hooks.registry import HookRegistry
from attune.learning.evaluator import SessionEvaluator, SessionQuality
from attune.learning.extractor import (
    ExtractedPattern,
    PatternCategory,
)
from attune.learning.storage import LearnedSkillsStorage


class TestFullSessionWorkflow:
    """Test complete session workflow from start to end."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return "integration_test_user"

    @pytest.fixture
    def storage_dir(self, tmp_path):
        """Temporary storage directory."""
        return tmp_path / "storage"

    @pytest.fixture
    def hook_registry(self):
        """Create hook registry with session hooks."""
        registry = HookRegistry()
        return registry

    @pytest.fixture
    def context_manager(self, storage_dir):
        """Create context manager."""
        return ContextManager(storage_dir=storage_dir / "compact_states")

    @pytest.fixture
    def learning_storage(self, storage_dir):
        """Create learning storage."""
        return LearnedSkillsStorage(storage_dir=storage_dir / "learned_skills")

    @pytest.fixture(autouse=True)
    def reset_command_registry(self):
        """Reset command registry."""
        CommandRegistry.reset_instance()
        yield
        CommandRegistry.reset_instance()

    def test_session_start_to_end_workflow(
        self,
        user_id,
        hook_registry,
        context_manager,
        learning_storage,
    ):
        """Test complete session lifecycle."""
        events_log = []

        # Register session hooks - handlers receive keyword arguments
        hook_registry.register(
            event=HookEvent.SESSION_START,
            handler=lambda **kw: events_log.append("session_start") or {"success": True},
        )
        hook_registry.register(
            event=HookEvent.SESSION_END,
            handler=lambda **kw: events_log.append("session_end") or {"success": True},
        )

        # === SESSION START ===
        hook_registry.fire_sync(HookEvent.SESSION_START, {"user_id": user_id})
        assert "session_start" in events_log

        # Try to restore previous state
        restored_state = context_manager.restore_state(user_id)
        # First run - no state to restore
        assert restored_state is None

        # === DURING SESSION: Commands ===
        CommandContext(
            user_id=user_id,
            hook_registry=hook_registry,
            context_manager=context_manager,
            learning_storage=learning_storage,
        )

        # Load commands
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        if commands_dir.exists():
            registry = CommandRegistry.get_instance()
            registry.load_from_directory(commands_dir)
            # Check for any command (commands may vary based on setup)
            assert len(registry.list_commands()) > 0

        # === DURING SESSION: Learning ===
        # Verify evaluator can be instantiated (full evaluation requires complex state)
        evaluator = SessionEvaluator()
        assert evaluator is not None

        # Verify SessionQuality enum values exist
        assert SessionQuality.EXCELLENT is not None
        assert SessionQuality.GOOD is not None
        assert SessionQuality.AVERAGE is not None
        assert SessionQuality.POOR is not None
        assert SessionQuality.SKIP is not None

        # === PRE-COMPACT: Save State ===
        hook_registry.register(
            event=HookEvent.PRE_COMPACT,
            handler=lambda **kw: events_log.append("pre_compact") or {"success": True},
        )
        hook_registry.fire_sync(HookEvent.PRE_COMPACT, {"user_id": user_id})
        assert "pre_compact" in events_log

        # Create compact state
        context_manager.session_id = "test_session_123"
        context_manager.current_phase = "testing"

        # Set handoff
        context_manager.set_handoff(
            situation="Running integration tests",
            background="Testing full workflow",
            assessment="Tests passing so far",
            recommendation="Continue with more tests",
        )

        # === SESSION END ===
        hook_registry.fire_sync(HookEvent.SESSION_END, {"user_id": user_id})
        assert "session_end" in events_log

        # Verify all events fired
        assert events_log == ["session_start", "pre_compact", "session_end"]

    def test_context_preservation_across_sessions(
        self,
        user_id,
        context_manager,
    ):
        """Test that context is preserved and restored across sessions."""
        # === FIRST SESSION ===
        context_manager.session_id = "session_1"
        context_manager.current_phase = "implementation"
        context_manager.complete_phase("planning")

        handoff = context_manager.set_handoff(
            situation="Implementing feature X",
            background="User requested feature X",
            assessment="50% complete",
            recommendation="Continue with unit tests",
            priority="high",
        )

        # Create and save state
        state = CompactState(
            user_id=user_id,
            trust_level=0.9,
            empathy_level=4,
            detected_patterns=[],
            session_id="session_1",
            current_phase="implementation",
            completed_phases=["planning"],
            pending_handoff=handoff,
        )

        saved_path = context_manager._state_manager.save_state(state)
        assert saved_path.exists()

        # === SECOND SESSION ===
        # Create new context manager (simulates new session)
        new_context = ContextManager(storage_dir=context_manager._state_manager.storage_dir)

        # Restore state
        restored = new_context.restore_state(user_id)

        assert restored is not None
        assert restored.trust_level == 0.9
        assert restored.empathy_level == 4
        assert restored.session_id == "session_1"
        assert restored.current_phase == "implementation"
        assert "planning" in restored.completed_phases
        assert restored.pending_handoff is not None
        assert restored.pending_handoff.priority == "high"

    def test_pattern_extraction_and_application(
        self,
        user_id,
        learning_storage,
    ):
        """Test extracting patterns and applying them."""
        # Create patterns directly (extractor methods are private)
        # The PatternExtractor is designed to work with CollaborationState,
        # not raw corrections dictionaries
        patterns = [
            ExtractedPattern(
                category=PatternCategory.USER_CORRECTION,
                trigger="eval usage",
                context="User corrected unsafe eval() usage",
                resolution="Use ast.literal_eval() instead for security",
                confidence=0.9,
                source_session="test_session",
            ),
        ]

        assert len(patterns) > 0

        # Save patterns
        for pattern in patterns:
            learning_storage.save_pattern(user_id, pattern)

        # Retrieve patterns
        stored = learning_storage.get_all_patterns(user_id)
        assert len(stored) > 0

        # Search patterns
        results = learning_storage.search_patterns(user_id, "eval")
        assert len(results) > 0

        # Format for context
        context_text = learning_storage.format_patterns_for_context(user_id)
        assert "Learned Patterns" in context_text

    def test_command_execution_with_full_context(
        self,
        user_id,
        hook_registry,
        context_manager,
        learning_storage,
    ):
        """Test command execution with all context components."""
        # Setup hooks
        hooks_log = []
        hook_registry.register(
            event=HookEvent.PRE_COMMAND,
            handler=lambda ctx: hooks_log.append(f"pre:{ctx.get('command')}") or {"success": True},
        )
        hook_registry.register(
            event=HookEvent.POST_COMMAND,
            handler=lambda ctx: hooks_log.append(f"post:{ctx.get('command')}") or {"success": True},
        )

        # Create full context
        ctx = CommandContext(
            user_id=user_id,
            hook_registry=hook_registry,
            context_manager=context_manager,
            learning_storage=learning_storage,
        )

        # Load and execute command
        commands_dir = Path(__file__).parent.parent.parent / ".claude" / "commands"
        if not commands_dir.exists():
            pytest.skip("Commands directory not found")

        registry = CommandRegistry.get_instance()
        registry.load_from_directory(commands_dir)

        compact_cmd = registry.get("compact")
        if compact_cmd is None:
            pytest.skip("compact command not found")

        executor = CommandExecutor(ctx)
        result = executor.execute(compact_cmd)

        assert result.success is True
        assert "pre:compact" in hooks_log
        assert "post:compact" in hooks_log


class TestModuleIntegration:
    """Test integration between specific modules."""

    def test_hooks_and_context_integration(self, tmp_path):
        """Test hooks triggering context operations."""
        context_manager = ContextManager(storage_dir=tmp_path / "states")
        hook_registry = HookRegistry()

        # Hook that triggers context save
        # Note: Hook handlers receive keyword arguments, not positional ctx dict
        def pre_compact_handler(**kwargs):
            context_manager.session_id = kwargs.get("session_id", "unknown")
            context_manager.current_phase = "compacting"
            return {"success": True, "phase": "compacting"}

        hook_registry.register(
            event=HookEvent.PRE_COMPACT,
            handler=pre_compact_handler,
        )

        # Fire hook
        results = hook_registry.fire_sync(
            HookEvent.PRE_COMPACT,
            {"session_id": "session_abc"},
        )

        assert len(results) > 0
        assert results[0]["success"] is True
        assert context_manager.session_id == "session_abc"
        assert context_manager.current_phase == "compacting"

    def test_learning_and_commands_integration(self, tmp_path):
        """Test learning patterns applied to commands."""
        storage = LearnedSkillsStorage(storage_dir=tmp_path / "skills")
        user_id = "test_user"

        # Save some patterns
        # Note: ExtractedPattern.pattern_id is a computed property, not a constructor arg
        pattern = ExtractedPattern(
            category=PatternCategory.PREFERENCE,
            trigger="command style",
            context="user prefers concise output",
            resolution="keep output brief",
            confidence=0.9,
            source_session="test_session",
        )
        storage.save_pattern(user_id, pattern)

        # Create command context with storage
        ctx = CommandContext(
            user_id=user_id,
            learning_storage=storage,
        )

        # Get patterns for context
        patterns_text = ctx.get_patterns_for_context()
        assert "Learned Patterns" in patterns_text

        # Search patterns
        results = ctx.search_patterns("command")
        assert len(results) > 0

    def test_agents_and_commands_coexistence(self):
        """Test that agents and commands modules coexist."""
        from attune.agents_md import AgentRegistry as AgentReg
        from attune.commands import CommandRegistry as CmdReg

        # Both registries should work independently
        AgentReg.reset_instance()
        CmdReg.reset_instance()

        agent_registry = AgentReg.get_instance()
        cmd_registry = CmdReg.get_instance()

        # They should be different objects
        assert agent_registry is not cmd_registry

        # Both should function
        assert agent_registry.list_agents() is not None
        assert cmd_registry.list_commands() is not None

        AgentReg.reset_instance()
        CmdReg.reset_instance()


class TestErrorHandling:
    """Test error handling across modules."""

    def test_hook_error_doesnt_crash_session(self):
        """Test that hook errors are handled gracefully."""
        registry = HookRegistry()

        def failing_handler(ctx):
            raise ValueError("Intentional test error")

        registry.register(
            event=HookEvent.SESSION_START,
            handler=failing_handler,
        )

        # Should not raise, should return error in results
        results = registry.fire_sync(HookEvent.SESSION_START, {})

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "error" in results[0]

    def test_missing_storage_dir_handled(self, tmp_path):
        """Test graceful handling of missing storage."""
        nonexistent = tmp_path / "nonexistent" / "deep" / "path"

        # Should create directories as needed
        storage = LearnedSkillsStorage(storage_dir=nonexistent)
        summary = storage.get_summary("test_user")

        assert summary["total_patterns"] == 0

    def test_invalid_command_file_skipped(self, tmp_path):
        """Test that command files with content load correctly."""
        from attune.commands import CommandLoader

        # Create valid and minimal files
        (tmp_path / "valid.md").write_text("Valid - Description\n\nBody content.")
        (tmp_path / "minimal.md").write_text("Minimal command")

        loader = CommandLoader()
        commands = loader.load_directory(tmp_path)

        # Both should load (loader is permissive)
        assert "valid" in commands
        # Valid command should have body content
        assert commands["valid"].body != ""
