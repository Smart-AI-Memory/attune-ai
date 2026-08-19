"""Unit tests for attune.commands.context module.

Tests CommandContext dataclass, CommandExecutor, and
create_command_context factory.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from attune.commands.context import (
    CommandContext,
    CommandExecutor,
    create_command_context,
)
from attune.commands.models import CommandConfig, CommandMetadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_command(
    name: str = "test", body: str = "body", hooks: dict | None = None
) -> CommandConfig:
    """Build a minimal CommandConfig for testing."""
    metadata = CommandMetadata(name=name, hooks=hooks or {})
    return CommandConfig(
        name=name,
        description="test command",
        body=body,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# CommandContext
# ---------------------------------------------------------------------------


class TestCommandContextInit:
    """Tests for CommandContext initialisation."""

    def test_init_minimal_user_id_only(self):
        """CommandContext created with only user_id sets optional fields to None."""
        ctx = CommandContext(user_id="user1")

        assert ctx.user_id == "user1"
        assert ctx.hook_registry is None
        assert ctx.learning_storage is None
        assert ctx.collaboration_state is None
        assert ctx.project_root is None
        assert ctx.extra == {}

    def test_init_with_project_root(self, tmp_path):
        """CommandContext stores project_root as a Path."""
        ctx = CommandContext(user_id="user1", project_root=tmp_path)

        assert ctx.project_root == tmp_path

    def test_init_with_extra_dict(self):
        """CommandContext stores arbitrary extra keys."""
        ctx = CommandContext(user_id="u", extra={"key": "value"})

        assert ctx.extra["key"] == "value"


class TestCommandContextFireHook:
    """Tests for CommandContext.fire_hook()."""

    def test_fire_hook_no_registry_returns_empty_list(self):
        """fire_hook returns [] when hook_registry is None."""
        ctx = CommandContext(user_id="u")

        result = ctx.fire_hook("PreCommand")

        assert result == []

    def test_fire_hook_unknown_event_returns_empty_list(self):
        """fire_hook returns [] for an unrecognised event string.

        HookEvent is imported lazily inside fire_hook, so we patch it via
        the attune.hooks.config module path.
        """

        mock_registry = MagicMock()
        ctx = CommandContext(user_id="u", hook_registry=mock_registry)

        # Patch the module that fire_hook imports from
        with patch("attune.hooks.config.HookEvent") as mock_event_cls:
            mock_event_cls.side_effect = ValueError("unknown event")
            # Trigger the code-path by calling with an event string
            # The real HookEvent may raise ValueError for unknown values
            result = ctx.fire_hook("NotARealEvent_XYZ_DEFINITELY_DOES_NOT_EXIST")

        assert result == []

    def test_fire_hook_calls_registry_fire_sync(self):
        """fire_hook invokes hook_registry.fire_sync with correct arguments.

        We use a real HookEvent value so the import inside fire_hook succeeds.
        """
        from attune.hooks.config import HookEvent

        mock_registry = MagicMock()
        mock_registry.fire_sync.return_value = [{"result": "ok"}]
        ctx = CommandContext(user_id="alice", hook_registry=mock_registry)

        # Use the first real HookEvent value to avoid ValueError
        first_event = list(HookEvent)[0]
        result = ctx.fire_hook(first_event.value, {"extra": "ctx"})

        assert result == [{"result": "ok"}]
        mock_registry.fire_sync.assert_called_once()

    def test_fire_hook_injects_user_id_into_context(self):
        """fire_hook always adds user_id to the hook context."""
        from attune.hooks.config import HookEvent

        mock_registry = MagicMock()
        mock_registry.fire_sync.return_value = []
        ctx = CommandContext(user_id="bob", hook_registry=mock_registry)

        first_event = list(HookEvent)[0]
        ctx.fire_hook(first_event.value, {})

        _args, _kwargs = mock_registry.fire_sync.call_args
        passed_ctx = _args[1]
        assert passed_ctx["user_id"] == "bob"


class TestCommandContextPatterns:
    """Tests for get_patterns_for_context and related helpers."""

    def test_get_patterns_no_storage_returns_empty_string(self):
        """get_patterns_for_context returns '' when learning_storage is None."""
        ctx = CommandContext(user_id="u")

        result = ctx.get_patterns_for_context()

        assert result == ""

    def test_get_patterns_delegates_to_storage(self):
        """get_patterns_for_context calls storage.format_patterns_for_context."""
        mock_storage = MagicMock()
        mock_storage.format_patterns_for_context.return_value = "## Patterns\n- Fix bugs"
        ctx = CommandContext(user_id="u", learning_storage=mock_storage)

        result = ctx.get_patterns_for_context(max_patterns=3)

        assert result == "## Patterns\n- Fix bugs"
        mock_storage.format_patterns_for_context.assert_called_once_with("u", max_patterns=3)

    def test_get_learning_summary_no_storage_returns_empty_dict(self):
        """get_learning_summary returns {} when learning_storage is None."""
        ctx = CommandContext(user_id="u")

        result = ctx.get_learning_summary()

        assert result == {}

    def test_get_learning_summary_delegates_to_storage(self):
        """get_learning_summary calls storage.get_summary."""
        mock_storage = MagicMock()
        mock_storage.get_summary.return_value = {"patterns": 5}
        ctx = CommandContext(user_id="u", learning_storage=mock_storage)

        result = ctx.get_learning_summary()

        assert result == {"patterns": 5}
        mock_storage.get_summary.assert_called_once_with("u")

    def test_search_patterns_no_storage_returns_empty_list(self):
        """search_patterns returns [] when learning_storage is None."""
        ctx = CommandContext(user_id="u")

        result = ctx.search_patterns("query")

        assert result == []

    def test_search_patterns_delegates_to_storage(self):
        """search_patterns calls storage.search_patterns."""
        mock_p = MagicMock()
        mock_p.pattern_id = "p1"
        mock_storage = MagicMock()
        mock_storage.search_patterns.return_value = [mock_p]
        ctx = CommandContext(user_id="u", learning_storage=mock_storage)

        result = ctx.search_patterns("compact")

        assert result == [mock_p]
        mock_storage.search_patterns.assert_called_once_with("u", "compact")


# ---------------------------------------------------------------------------
# CommandExecutor
# ---------------------------------------------------------------------------


class TestCommandExecutorExecute:
    """Tests for CommandExecutor.execute()."""

    def test_execute_success_returns_command_result(self):
        """execute() returns CommandResult with success=True and correct body."""
        ctx = CommandContext(user_id="u")
        executor = CommandExecutor(ctx)
        cmd = _make_command(name="compact", body="Do the compact thing")

        result = executor.execute(cmd)

        assert result.success is True
        assert result.command_name == "compact"
        assert result.output == "Do the compact thing"
        assert result.duration_ms >= 0

    def test_execute_no_hooks_fires_nothing(self):
        """execute() does not call hook_registry when command has no hooks."""
        mock_registry = MagicMock()
        ctx = CommandContext(user_id="u", hook_registry=mock_registry)
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={})

        executor.execute(cmd)

        mock_registry.fire_sync.assert_not_called()

    def test_execute_with_pre_hook_fires_pre_hook(self):
        """execute() fires the pre hook when configured."""
        ctx = CommandContext(user_id="u")
        ctx.fire_hook = MagicMock(return_value=[])
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={"pre": "PreCommand"})

        executor.execute(cmd)

        ctx.fire_hook.assert_any_call("PreCommand", {"command": cmd.name, "args": {}})

    def test_execute_with_post_hook_fires_post_hook(self):
        """execute() fires the post hook after execution."""
        ctx = CommandContext(user_id="u")
        ctx.fire_hook = MagicMock(return_value=[])
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={"post": "PostCommand"})

        executor.execute(cmd)

        post_calls = [c for c in ctx.fire_hook.call_args_list if c[0][0] == "PostCommand"]
        assert len(post_calls) == 1

    def test_execute_records_hooks_fired(self):
        """execute() records hook names in result.hooks_fired."""
        ctx = CommandContext(user_id="u")
        ctx.fire_hook = MagicMock(return_value=[])
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={"pre": "PreCommand", "post": "PostCommand"})

        result = executor.execute(cmd)

        assert "pre:PreCommand" in result.hooks_fired
        assert "post:PostCommand" in result.hooks_fired

    def test_execute_with_patterns_records_applied(self):
        """execute() records first 3 pattern IDs in patterns_applied."""
        mock_p1 = MagicMock()
        mock_p1.pattern_id = "pat-1"
        mock_p2 = MagicMock()
        mock_p2.pattern_id = "pat-2"
        mock_storage = MagicMock()
        mock_storage.search_patterns.return_value = [mock_p1, mock_p2]
        ctx = CommandContext(user_id="u", learning_storage=mock_storage)
        executor = CommandExecutor(ctx)
        cmd = _make_command(name="compact")

        result = executor.execute(cmd)

        assert "pat-1" in result.patterns_applied
        assert "pat-2" in result.patterns_applied

    def test_execute_accepts_extra_args(self):
        """execute() passes args through to hook context without error."""
        ctx = CommandContext(user_id="u")
        executor = CommandExecutor(ctx)
        cmd = _make_command()

        result = executor.execute(cmd, args={"file": "main.py"})

        assert result.success is True


class TestCommandExecutorPrepareCommand:
    """Tests for CommandExecutor.prepare_command()."""

    def test_prepare_command_returns_expected_keys(self):
        """prepare_command() returns a dict with required keys."""
        ctx = CommandContext(user_id="alice")
        executor = CommandExecutor(ctx)
        cmd = _make_command(name="commit", body="Commit instructions")

        result = executor.prepare_command(cmd)

        assert result["command"] == "commit"
        assert result["description"] == "test command"
        assert result["body"] == "Commit instructions"
        assert result["user_id"] == "alice"
        assert "args" in result
        assert "patterns_context" in result
        assert "has_hooks" in result

    def test_prepare_command_has_hooks_false_when_no_hooks(self):
        """prepare_command() sets has_hooks=False when command has no hooks."""
        ctx = CommandContext(user_id="u")
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={})

        result = executor.prepare_command(cmd)

        assert result["has_hooks"] is False

    def test_prepare_command_has_hooks_true_when_hooks_present(self):
        """prepare_command() sets has_hooks=True when command has hooks."""
        ctx = CommandContext(user_id="u")
        executor = CommandExecutor(ctx)
        cmd = _make_command(hooks={"pre": "PreCommand"})

        result = executor.prepare_command(cmd)

        assert result["has_hooks"] is True

    def test_prepare_command_includes_patterns_context_when_storage(self):
        """prepare_command() includes patterns_context from learning storage."""
        mock_storage = MagicMock()
        mock_storage.format_patterns_for_context.return_value = "## P\n- pattern1"
        ctx = CommandContext(user_id="u", learning_storage=mock_storage)
        executor = CommandExecutor(ctx)
        cmd = _make_command()

        result = executor.prepare_command(cmd)

        assert "pattern1" in result["patterns_context"]

    def test_prepare_command_passes_args_through(self):
        """prepare_command() stores extra args in the result dict."""
        ctx = CommandContext(user_id="u")
        executor = CommandExecutor(ctx)
        cmd = _make_command()

        result = executor.prepare_command(cmd, args={"scope": "all"})

        assert result["args"] == {"scope": "all"}


# ---------------------------------------------------------------------------
# create_command_context
# ---------------------------------------------------------------------------


class TestCreateCommandContext:
    """Tests for the create_command_context factory function."""

    def test_minimal_creates_context_with_user_id(self):
        """create_command_context with only user_id returns a CommandContext.

        Imports are lazy inside the function, so we patch the modules
        themselves to simulate ImportError.
        """
        with patch.dict(
            "sys.modules",
            {
                "attune.hooks.registry": None,
                "attune.learning.storage": None,
            },
        ):
            ctx = create_command_context(
                "user1",
                enable_hooks=True,
                enable_learning=True,
            )

        assert isinstance(ctx, CommandContext)
        assert ctx.user_id == "user1"

    def test_create_with_project_root_sets_path(self, tmp_path):
        """create_command_context converts project_root string to Path."""
        ctx = create_command_context(
            "u",
            project_root=str(tmp_path),
            enable_hooks=False,
            enable_learning=False,
        )

        assert ctx.project_root == tmp_path

    def test_create_all_disabled_returns_context_with_no_components(self):
        """create_command_context with all disabled returns bare context."""
        ctx = create_command_context(
            "u",
            enable_hooks=False,
            enable_learning=False,
        )

        assert ctx.user_id == "u"
        assert ctx.hook_registry is None
        assert ctx.learning_storage is None

    def test_create_handles_import_error_gracefully(self):
        """create_command_context handles ImportError from optional modules.

        Simulating ImportError by removing the module from sys.modules so
        the lazy import inside the function fails cleanly.
        """
        with patch.dict("sys.modules", {"attune.hooks.registry": None}):
            ctx = create_command_context(
                "u",
                enable_hooks=True,
                enable_learning=False,
            )

        assert ctx.hook_registry is None
        assert isinstance(ctx, CommandContext)
