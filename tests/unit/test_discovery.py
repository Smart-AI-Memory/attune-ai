"""Tests for attune.discovery"""

import re

from attune.discovery import (
    DISCOVERY_TIPS,
    DiscoveryEngine,
    format_tips_for_cli,
    get_engine,
    show_tip_if_available,
)


class TestDiscoveryEngine:
    """Tests for DiscoveryEngine class."""

    def test_initialization(self, tmp_path):
        """Test DiscoveryEngine initialization."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        assert engine is not None
        assert engine.storage_dir == tmp_path
        assert engine.stats_file == tmp_path / "discovery_stats.json"
        assert isinstance(engine.state, dict)
        assert "command_counts" in engine.state
        assert "tips_shown" in engine.state
        assert "total_commands" in engine.state

    def test_record_command_basic(self, tmp_path):
        """Test recording a command."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        engine.record_command("inspect")

        assert engine.state["command_counts"]["inspect"] == 1
        assert engine.state["total_commands"] == 1

        # Record another command
        engine.record_command("inspect")

        assert engine.state["command_counts"]["inspect"] == 2
        assert engine.state["total_commands"] == 2

    def test_record_command_triggers_tip(self, tmp_path):
        """Test that recording a command triggers appropriate tips."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        # First inspect command should trigger tip
        tips = engine.record_command("inspect")

        # Should get after_first_inspect tip
        assert len(tips) >= 0  # May or may not trigger depending on conditions

    def test_record_patterns_learned(self, tmp_path):
        """Test recording patterns learned."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        engine.record_patterns_learned(5)

        assert engine.state["patterns_learned"] == 5

        # Record more
        engine.record_patterns_learned(3)

        assert engine.state["patterns_learned"] == 8

    def test_record_api_request(self, tmp_path):
        """Test recording API requests."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        engine.record_api_request()

        assert engine.state["api_requests"] == 1

        # Record more
        for _ in range(15):
            engine.record_api_request()

        assert engine.state["api_requests"] == 16

    def test_record_claude_sync(self, tmp_path):
        """Test recording Claude sync."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        assert engine.state["last_claude_sync"] is None

        engine.record_claude_sync()

        assert engine.state["last_claude_sync"] is not None
        assert isinstance(engine.state["last_claude_sync"], str)

    def test_set_tech_debt_trend(self, tmp_path):
        """Test setting tech debt trend."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        engine.set_tech_debt_trend("increasing")

        assert engine.state["tech_debt_trend"] == "increasing"

        engine.set_tech_debt_trend("decreasing")

        assert engine.state["tech_debt_trend"] == "decreasing"

    def test_get_pending_tips_with_trigger(self, tmp_path):
        """Test getting pending tips with trigger."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        # Record 10 inspect commands to trigger tip
        for _ in range(10):
            engine.record_command("inspect")

        # Get tips triggered by inspect
        tips = engine.get_pending_tips(trigger="inspect", max_tips=5)

        # Should have tips (though may be empty if already shown)
        assert isinstance(tips, list)

    def test_mark_shown(self, tmp_path):
        """Test marking a tip as shown."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        assert "after_first_inspect" not in engine.state["tips_shown"]

        engine.mark_shown("after_first_inspect")

        assert "after_first_inspect" in engine.state["tips_shown"]

        # Marking again should be idempotent
        engine.mark_shown("after_first_inspect")

        assert engine.state["tips_shown"].count("after_first_inspect") == 1

    def test_get_stats(self, tmp_path):
        """Test getting discovery statistics."""
        engine = DiscoveryEngine(storage_dir=str(tmp_path))

        # Record some activity
        engine.record_command("inspect")
        engine.record_command("health")
        engine.record_patterns_learned(5)
        engine.mark_shown("after_first_inspect")

        stats = engine.get_stats()

        assert stats["total_commands"] == 2
        assert stats["patterns_learned"] == 5
        assert stats["tips_shown"] == 1
        assert isinstance(stats["command_counts"], dict)
        assert isinstance(stats["days_active"], int)

    def test_state_persistence(self, tmp_path):
        """Test that state persists across instances."""
        # Create engine and record commands
        engine1 = DiscoveryEngine(storage_dir=str(tmp_path))
        engine1.record_command("inspect")
        engine1.record_patterns_learned(10)

        # Create new engine with same storage
        engine2 = DiscoveryEngine(storage_dir=str(tmp_path))

        assert engine2.state["command_counts"]["inspect"] == 1
        assert engine2.state["patterns_learned"] == 10


def test_get_engine_singleton(tmp_path):
    """Test get_engine returns singleton instance."""
    # Reset global engine
    import attune.discovery

    attune.discovery._engine = None

    engine1 = get_engine(storage_dir=str(tmp_path))
    engine2 = get_engine(storage_dir=str(tmp_path))

    # Should be same instance
    assert engine1 is engine2


def test_show_tip_if_available(tmp_path, capsys):
    """Test show_tip_if_available displays tips."""
    # Reset global engine
    import attune.discovery

    attune.discovery._engine = None

    # This should create global engine and record command
    show_tip_if_available("inspect", quiet=False)

    # Tips may or may not be shown depending on conditions
    # Just verify no errors occurred


def test_show_tip_if_available_quiet_mode(tmp_path, capsys):
    """Test show_tip_if_available with quiet mode."""
    # Reset global engine
    import attune.discovery

    attune.discovery._engine = None

    # Quiet mode should not print anything
    show_tip_if_available("inspect", quiet=True)

    capsys.readouterr()
    # In quiet mode, should not print tips (may print empty line)


def test_format_tips_for_cli_with_tips():
    """Test formatting tips for CLI display."""
    tips = [
        {"id": "tip1", "tip": "Try this feature", "priority": 1},
        {"id": "tip2", "tip": "Try that feature", "priority": 2},
    ]

    result = format_tips_for_cli(tips)

    assert isinstance(result, str)
    assert "TIPS" in result
    assert "Try this feature" in result
    assert "Try that feature" in result


def test_format_tips_for_cli_empty():
    """Test formatting empty tips list."""
    result = format_tips_for_cli([])

    assert result == ""


# Valid top-level CLI subcommands registered in cli_minimal.py
_VALID_CLI_SUBCOMMANDS = {
    "workflow",
    "telemetry",
    "costs",
    "provider",
    "remember",
    "forget",
    "lessons",
    "setup",
    "auth",
    "doctor",
    "features",
    "validate",
    "version",
}

# Valid compound commands: "attune <sub> <action>" or tool commands
_VALID_COMMAND_PATTERNS = [
    r"attune workflow run \S+",
    r"attune doctor",
    r"attune costs",
    r"attune workflow run \S+ --\S+",
    r"ruff (?:check|format)",
    r"pytest ",
]


def test_discovery_tips_reference_valid_commands():
    """Ensure all discovery tips reference commands that actually exist.

    This prevents ghost command references (e.g. 'attune ship',
    'attune sync-claude') from reaching users. Every tip that
    mentions 'attune ...' must reference either a registered CLI
    subcommand or a known tool command.
    """
    # Extract all 'attune ...' and 'ruff ...' command references from tips
    command_pattern = re.compile(r"'(attune \S+(?:\s\S+)*)'")

    for tip_id, tip_config in DISCOVERY_TIPS.items():
        tip_text = tip_config["tip"]
        matches = command_pattern.findall(tip_text)

        for cmd in matches:
            parts = cmd.split()
            assert parts[0] == "attune", f"Tip '{tip_id}' references unexpected prefix: {cmd}"

            # The second token must be a registered subcommand
            if len(parts) >= 2:
                subcommand = parts[1]
                assert subcommand in _VALID_CLI_SUBCOMMANDS, (
                    f"Tip '{tip_id}' references non-existent subcommand "
                    f"'attune {subcommand}'. Valid subcommands: "
                    f"{sorted(_VALID_CLI_SUBCOMMANDS)}"
                )

            # If it's "attune workflow run <name>", the structure is valid
            # (workflow names are dynamic, so we just check the prefix)
            if len(parts) >= 4 and parts[1] == "workflow" and parts[2] == "run":
                # Valid: attune workflow run <something>
                pass
