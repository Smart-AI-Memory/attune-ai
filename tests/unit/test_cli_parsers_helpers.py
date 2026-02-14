"""Tests for CLI parsers, helpers, and metrics collector.

Covers:
- src/attune/cli/utils/helpers.py
- src/attune/cli/parsers/batch.py
- src/attune/cli/parsers/workflow.py
- src/attune/cli/parsers/cache.py
- src/attune/cli/parsers/provider.py
- src/attune/cli/parsers/metrics.py
- src/attune/metrics/collector.py

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# helpers.py tests
# ---------------------------------------------------------------------------


class TestFileExists:
    """Tests for _file_exists."""

    def test_existing_file_returns_true(self, tmp_path):
        """Test returns True for a file that exists."""
        f = tmp_path / "exists.txt"
        f.write_text("content")
        from attune.cli.utils.helpers import _file_exists

        assert _file_exists(str(f)) is True

    def test_nonexistent_file_returns_false(self, tmp_path):
        """Test returns False for a file that does not exist."""
        from attune.cli.utils.helpers import _file_exists

        assert _file_exists(str(tmp_path / "nope.txt")) is False

    def test_directory_returns_true(self, tmp_path):
        """Test returns True for a directory (Path.exists covers dirs)."""
        from attune.cli.utils.helpers import _file_exists

        assert _file_exists(str(tmp_path)) is True


class TestShowAchievements:
    """Tests for _show_achievements."""

    def _make_engine(self, stats: dict) -> MagicMock:
        engine = MagicMock()
        engine.get_stats.return_value = stats
        return engine

    def test_no_achievements_prints_nothing(self, capsys):
        """Test that zero commands produces no output."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({"total_commands": 0, "command_counts": {}}))
        assert capsys.readouterr().out == ""

    def test_first_steps_achievement(self, capsys):
        """Test 1 command unlocks First Steps."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({"total_commands": 1, "command_counts": {}}))
        out = capsys.readouterr().out
        assert "First Steps" in out
        assert "ACHIEVEMENTS UNLOCKED" in out

    def test_all_command_thresholds(self, capsys):
        """Test 100+ commands unlocks all command-count achievements."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({"total_commands": 100, "command_counts": {}}))
        out = capsys.readouterr().out
        for label in ("First Steps", "Getting Started", "Power User", "Expert"):
            assert label in out

    def test_learn_achievement(self, capsys):
        """Test learn command triggers Pattern Learner."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({"total_commands": 1, "command_counts": {"learn": 1}}))
        assert "Pattern Learner" in capsys.readouterr().out

    def test_sync_claude_achievement(self, capsys):
        """Test sync-claude command triggers Claude Whisperer."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {"sync-claude": 1}})
        )
        assert "Claude Whisperer" in capsys.readouterr().out

    def test_morning_achievement(self, capsys):
        """Test morning >= 5 triggers Early Bird."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {"morning": 5}})
        )
        assert "Early Bird" in capsys.readouterr().out

    def test_ship_achievement(self, capsys):
        """Test ship >= 10 triggers Quality Shipper."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({"total_commands": 1, "command_counts": {"ship": 10}}))
        assert "Quality Shipper" in capsys.readouterr().out

    def test_code_doctor_achievement(self, capsys):
        """Test health + fix-all triggers Code Doctor."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {"health": 1, "fix-all": 1}})
        )
        assert "Code Doctor" in capsys.readouterr().out

    def test_code_doctor_missing_fix_all(self, capsys):
        """Test health alone does NOT trigger Code Doctor."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {"health": 1}})
        )
        assert "Code Doctor" not in capsys.readouterr().out

    def test_patterns_learned_achievement(self, capsys):
        """Test patterns_learned >= 10 triggers Pattern Master."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {}, "patterns_learned": 10})
        )
        assert "Pattern Master" in capsys.readouterr().out

    def test_week_warrior_achievement(self, capsys):
        """Test days_active >= 7 triggers Week Warrior."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {}, "days_active": 7})
        )
        assert "Week Warrior" in capsys.readouterr().out

    def test_monthly_maven_achievement(self, capsys):
        """Test days_active >= 30 triggers Monthly Maven and Week Warrior."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(
            self._make_engine({"total_commands": 1, "command_counts": {}, "days_active": 30})
        )
        out = capsys.readouterr().out
        assert "Monthly Maven" in out
        assert "Week Warrior" in out

    def test_empty_stats_dict(self, capsys):
        """Test with completely empty stats dict."""
        from attune.cli.utils.helpers import _show_achievements

        _show_achievements(self._make_engine({}))
        assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Helper to create subparsers object
# ---------------------------------------------------------------------------


def _make_subparsers() -> argparse._SubParsersAction:
    """Create a fresh argparse subparsers object for testing."""
    parser = argparse.ArgumentParser()
    return parser.add_subparsers()


# ---------------------------------------------------------------------------
# batch.py parser tests
# ---------------------------------------------------------------------------


class TestBatchParser:
    """Tests for batch parser registration."""

    @patch("attune.cli.parsers.batch.cmd_batch_submit", create=True)
    @patch("attune.cli.parsers.batch.cmd_batch_status", create=True)
    @patch("attune.cli.parsers.batch.cmd_batch_results", create=True)
    @patch("attune.cli.parsers.batch.cmd_batch_wait", create=True)
    def test_register_creates_batch_parser(self, _w, _r, _s, _sub):
        """Test that register_parsers creates a 'batch' parser."""
        with patch.dict(
            "sys.modules",
            {"attune.cli.commands.batch": MagicMock()},
        ):
            from attune.cli.parsers.batch import register_parsers

            subparsers = _make_subparsers()
            register_parsers(subparsers)

            # Verify batch parser was added by checking choices
            assert "batch" in subparsers._name_parser_map

    def test_batch_subcommands_exist(self):
        """Test that submit, status, results, wait subcommands are registered."""
        mock_batch_module = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.batch": mock_batch_module}):
            # Need to reimport to pick up the mock
            import importlib

            import attune.cli.parsers.batch as batch_mod

            importlib.reload(batch_mod)

            subparsers = _make_subparsers()
            batch_mod.register_parsers(subparsers)

            # Parse a submit command to verify it works
            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            batch_mod.register_parsers(sp)

            args = parent.parse_args(["batch", "submit", "input.json"])
            assert args.input_file == "input.json"

    def test_batch_status_json_flag(self):
        """Test that status subcommand accepts --json flag."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.batch": mock_mod}):
            import importlib

            import attune.cli.parsers.batch as batch_mod

            importlib.reload(batch_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            batch_mod.register_parsers(sp)

            args = parent.parse_args(["batch", "status", "msgbatch_123", "--json"])
            assert args.batch_id == "msgbatch_123"
            assert args.json is True

    def test_batch_wait_defaults(self):
        """Test wait subcommand default values."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.batch": mock_mod}):
            import importlib

            import attune.cli.parsers.batch as batch_mod

            importlib.reload(batch_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            batch_mod.register_parsers(sp)

            args = parent.parse_args(["batch", "wait", "msgbatch_1", "out.json"])
            assert args.poll_interval == 300
            assert args.timeout == 86400


# ---------------------------------------------------------------------------
# cache.py parser tests
# ---------------------------------------------------------------------------


class TestCacheParser:
    """Tests for cache parser registration."""

    def test_register_creates_cache_parser(self):
        """Test that register_parsers creates a 'cache' parser."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.cache": mock_mod}):
            import importlib

            import attune.cli.parsers.cache as cache_mod

            importlib.reload(cache_mod)

            subparsers = _make_subparsers()
            cache_mod.register_parsers(subparsers)
            assert "cache" in subparsers._name_parser_map

    def test_cache_stats_defaults(self):
        """Test stats subcommand default values."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.cache": mock_mod}):
            import importlib

            import attune.cli.parsers.cache as cache_mod

            importlib.reload(cache_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            cache_mod.register_parsers(sp)

            args = parent.parse_args(["cache", "stats"])
            assert args.days == 7
            assert args.format == "table"
            assert args.verbose is False

    def test_cache_stats_custom_args(self):
        """Test stats subcommand with custom arguments."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.cache": mock_mod}):
            import importlib

            import attune.cli.parsers.cache as cache_mod

            importlib.reload(cache_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            cache_mod.register_parsers(sp)

            args = parent.parse_args(["cache", "stats", "--days", "30", "--format", "json", "-v"])
            assert args.days == 30
            assert args.format == "json"
            assert args.verbose is True

    def test_cache_clear_subcommand(self):
        """Test clear subcommand is registered."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.cache": mock_mod}):
            import importlib

            import attune.cli.parsers.cache as cache_mod

            importlib.reload(cache_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            cache_mod.register_parsers(sp)

            args = parent.parse_args(["cache", "clear"])
            assert args.cache_command == "clear"


# ---------------------------------------------------------------------------
# workflow.py parser tests
# ---------------------------------------------------------------------------


class TestWorkflowParser:
    """Tests for workflow parser registration."""

    def test_register_creates_workflow_parser(self):
        """Test that register_parsers creates 'workflow' parser."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.workflow": mock_mod}):
            import importlib

            import attune.cli.parsers.workflow as wf_mod

            importlib.reload(wf_mod)

            subparsers = _make_subparsers()
            wf_mod.register_parsers(subparsers)
            assert "workflow" in subparsers._name_parser_map

    def test_register_creates_workflow_setup_legacy(self):
        """Test that register_parsers creates deprecated 'workflow-setup' parser."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.workflow": mock_mod}):
            import importlib

            import attune.cli.parsers.workflow as wf_mod

            importlib.reload(wf_mod)

            subparsers = _make_subparsers()
            wf_mod.register_parsers(subparsers)
            assert "workflow-setup" in subparsers._name_parser_map

    def test_workflow_action_choices(self):
        """Test workflow action must be list, describe, run, or config."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.workflow": mock_mod}):
            import importlib

            import attune.cli.parsers.workflow as wf_mod

            importlib.reload(wf_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            wf_mod.register_parsers(sp)

            for action in ("list", "describe", "run", "config"):
                args = parent.parse_args(["workflow", action])
                assert args.action == action

    def test_workflow_optional_arguments(self):
        """Test workflow optional arguments parse correctly."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.workflow": mock_mod}):
            import importlib

            import attune.cli.parsers.workflow as wf_mod

            importlib.reload(wf_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            wf_mod.register_parsers(sp)

            args = parent.parse_args(
                [
                    "workflow",
                    "run",
                    "my-wf",
                    "--input",
                    '{"key":"val"}',
                    "--provider",
                    "anthropic",
                    "--force",
                    "--json",
                    "--use-recommended-tier",
                    "--write-tests",
                    "--output-dir",
                    "tests/out",
                    "--health-score-threshold",
                    "80",
                ]
            )
            assert args.name == "my-wf"
            assert args.input == '{"key":"val"}'
            assert args.provider == "anthropic"
            assert args.force is True
            assert args.json is True
            assert args.use_recommended_tier is True
            assert args.write_tests is True
            assert args.output_dir == "tests/out"
            assert args.health_score_threshold == 80

    def test_workflow_defaults(self):
        """Test workflow default values."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.workflow": mock_mod}):
            import importlib

            import attune.cli.parsers.workflow as wf_mod

            importlib.reload(wf_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            wf_mod.register_parsers(sp)

            args = parent.parse_args(["workflow", "list"])
            assert args.name is None
            assert args.provider is None
            assert args.force is False
            assert args.output_dir == "tests/generated"
            assert args.health_score_threshold == 95


# ---------------------------------------------------------------------------
# provider.py parser tests
# ---------------------------------------------------------------------------


class TestProviderParser:
    """Tests for provider parser registration."""

    def test_register_creates_provider_parser(self):
        """Test that register_parsers creates 'provider' parser."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.provider": mock_mod}):
            import importlib

            import attune.cli.parsers.provider as prov_mod

            importlib.reload(prov_mod)

            subparsers = _make_subparsers()
            prov_mod.register_parsers(subparsers)
            assert "provider" in subparsers._name_parser_map

    def test_provider_show_subcommand(self):
        """Test 'show' subcommand parses correctly."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.provider": mock_mod}):
            import importlib

            import attune.cli.parsers.provider as prov_mod

            importlib.reload(prov_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            prov_mod.register_parsers(sp)

            args = parent.parse_args(["provider", "show"])
            assert args.provider_command == "show"

    def test_provider_set_subcommand(self):
        """Test 'set' subcommand with provider name."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.provider": mock_mod}):
            import importlib

            import attune.cli.parsers.provider as prov_mod

            importlib.reload(prov_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            prov_mod.register_parsers(sp)

            args = parent.parse_args(["provider", "set", "anthropic"])
            assert args.name == "anthropic"

    def test_provider_set_rejects_invalid(self):
        """Test 'set' rejects non-anthropic providers."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.provider": mock_mod}):
            import importlib

            import attune.cli.parsers.provider as prov_mod

            importlib.reload(prov_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            prov_mod.register_parsers(sp)

            with pytest.raises(SystemExit):
                parent.parse_args(["provider", "set", "openai"])

    def test_provider_hybrid_subcommand(self):
        """Test deprecated 'hybrid' subcommand parses correctly."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.provider": mock_mod}):
            import importlib

            import attune.cli.parsers.provider as prov_mod

            importlib.reload(prov_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            prov_mod.register_parsers(sp)

            args = parent.parse_args(["provider", "hybrid"])
            assert args.provider_command == "hybrid"


# ---------------------------------------------------------------------------
# metrics.py parser tests
# ---------------------------------------------------------------------------


class TestMetricsParser:
    """Tests for metrics parser registration."""

    def test_register_creates_metrics_and_state_parsers(self):
        """Test that register_parsers creates 'metrics' and 'state' parsers."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.metrics": mock_mod}):
            import importlib

            import attune.cli.parsers.metrics as met_mod

            importlib.reload(met_mod)

            subparsers = _make_subparsers()
            met_mod.register_parsers(subparsers)
            assert "metrics" in subparsers._name_parser_map
            assert "state" in subparsers._name_parser_map

    def test_metrics_user_argument(self):
        """Test metrics command requires user argument."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.metrics": mock_mod}):
            import importlib

            import attune.cli.parsers.metrics as met_mod

            importlib.reload(met_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            met_mod.register_parsers(sp)

            args = parent.parse_args(["metrics", "user123"])
            assert args.user == "user123"
            assert args.db == "./metrics.db"

    def test_metrics_custom_db(self):
        """Test metrics --db flag."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.metrics": mock_mod}):
            import importlib

            import attune.cli.parsers.metrics as met_mod

            importlib.reload(met_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            met_mod.register_parsers(sp)

            args = parent.parse_args(["metrics", "u1", "--db", "/tmp/my.db"])
            assert args.db == "/tmp/my.db"

    def test_state_defaults(self):
        """Test state command default values."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.metrics": mock_mod}):
            import importlib

            import attune.cli.parsers.metrics as met_mod

            importlib.reload(met_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            met_mod.register_parsers(sp)

            args = parent.parse_args(["state"])
            assert args.state_dir == ".attune/state"

    def test_state_custom_dir(self):
        """Test state --state-dir flag."""
        mock_mod = MagicMock()
        with patch.dict("sys.modules", {"attune.cli.commands.metrics": mock_mod}):
            import importlib

            import attune.cli.parsers.metrics as met_mod

            importlib.reload(met_mod)

            parent = argparse.ArgumentParser()
            sp = parent.add_subparsers()
            met_mod.register_parsers(sp)

            args = parent.parse_args(["state", "--state-dir", "/custom/state"])
            assert args.state_dir == "/custom/state"


# ---------------------------------------------------------------------------
# MetricsCollector tests
# ---------------------------------------------------------------------------


class TestMetricsCollector:
    """Tests for the deprecated MetricsCollector class."""

    def test_init_default_db_path(self):
        """Test default initialization with no db_path."""
        from attune.metrics.collector import MetricsCollector

        mc = MetricsCollector()
        assert mc.db_path is None

    def test_init_custom_db_path(self):
        """Test initialization with custom db_path."""
        from attune.metrics.collector import MetricsCollector

        mc = MetricsCollector(db_path="/tmp/test.db")
        assert mc.db_path == "/tmp/test.db"

    def test_collect_returns_empty_dict(self):
        """Test collect returns empty dict (deprecated stub)."""
        from attune.metrics.collector import MetricsCollector

        mc = MetricsCollector()
        assert mc.collect() == {}

    def test_get_stats_returns_empty_dict(self):
        """Test get_stats returns empty dict (deprecated stub)."""
        from attune.metrics.collector import MetricsCollector

        mc = MetricsCollector()
        assert mc.get_stats() == {}
