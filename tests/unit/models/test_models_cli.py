"""Unit tests for models CLI module

Tests CLI commands for model management, cost estimation, and telemetry.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.models.cli import (
    configure_provider,
    main,
    print_costs,
    print_effective_config,
    print_provider_config,
    print_registry,
    print_tasks,
    print_telemetry_costs,
    print_telemetry_fallbacks,
    print_telemetry_providers,
    print_telemetry_summary,
)
from attune.models.registry import ModelInfo
from attune.models.tasks import ModelTier


@pytest.mark.unit
class TestPrintRegistry:
    """Test print_registry function."""

    @patch("attune.models.cli.get_all_models")
    def test_print_registry_table_format(self, mock_get_all_models, capsys):
        """Test printing registry in table format."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-3-haiku-20240307",
                    provider="anthropic",
                    tier="cheap",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                ),
                "capable": ModelInfo(
                    id="claude-3-sonnet-20240229",
                    provider="anthropic",
                    tier="capable",
                    input_cost_per_million=3.0,
                    output_cost_per_million=15.0,
                    max_tokens=4096,
                    supports_vision=True,
                    supports_tools=True,
                ),
            },
        }

        print_registry()

        captured = capsys.readouterr()
        assert "MODEL REGISTRY" in captured.out
        assert "claude-3-haiku" in captured.out
        assert "claude-3-sonnet" in captured.out
        assert "$0.25" in captured.out

    @patch("attune.models.cli.get_all_models")
    def test_print_registry_json_format(self, mock_get_all_models, capsys):
        """Test printing registry in JSON format."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-3-haiku-20240307",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="cheap",
                ),
            },
        }

        print_registry(format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "anthropic" in output
        assert "cheap" in output["anthropic"]
        assert output["anthropic"]["cheap"]["id"] == "claude-3-haiku-20240307"

    @patch("attune.models.cli.get_all_models")
    def test_print_registry_with_provider_filter(self, mock_get_all_models, capsys):
        """Test printing registry with provider filter."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-3-haiku-20240307",
                    provider="anthropic",
                    tier="cheap",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                ),
            },
            "openai": {
                "cheap": ModelInfo(
                    id="gpt-3.5-turbo",
                    provider="openai",
                    tier="cheap",
                    input_cost_per_million=0.50,
                    output_cost_per_million=1.50,
                ),
            },
        }

        print_registry(provider="anthropic")

        # Should only call get_all_models once
        mock_get_all_models.assert_called_once()

        captured = capsys.readouterr()
        assert "ANTHROPIC" in captured.out

    @patch("attune.models.cli.get_all_models")
    def test_print_registry_unknown_provider(self, mock_get_all_models, capsys):
        """Test printing registry with unknown provider."""
        mock_get_all_models.return_value = {"anthropic": {}, "openai": {}}

        with pytest.raises(SystemExit) as exc_info:
            print_registry(provider="unknown")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown provider" in captured.out


@pytest.mark.unit
class TestPrintTasks:
    """Test print_tasks function."""

    @patch("attune.models.cli.get_all_tasks")
    def test_print_tasks_table_format(self, mock_get_all_tasks, capsys):
        """Test printing tasks in table format."""
        mock_get_all_tasks.return_value = {
            "cheap": ["summarize", "classify"],
            "capable": ["fix_bug", "review_code"],
            "premium": ["coordinate", "architect"],
        }

        print_tasks()

        captured = capsys.readouterr()
        assert "TASK-TO-TIER MAPPINGS" in captured.out
        assert "summarize" in captured.out
        assert "fix_bug" in captured.out
        assert "coordinate" in captured.out

    @patch("attune.models.cli.get_all_tasks")
    def test_print_tasks_json_format(self, mock_get_all_tasks, capsys):
        """Test printing tasks in JSON format."""
        mock_get_all_tasks.return_value = {
            "cheap": ["summarize"],
            "capable": ["fix_bug"],
        }

        print_tasks(format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "cheap" in output
        assert "summarize" in output["cheap"]

    @patch("attune.models.cli.get_all_tasks")
    def test_print_tasks_with_tier_filter(self, mock_get_all_tasks, capsys):
        """Test printing tasks with tier filter."""
        mock_get_all_tasks.return_value = {
            "cheap": ["summarize"],
            "capable": ["fix_bug"],
        }

        print_tasks(tier="cheap")

        captured = capsys.readouterr()
        assert "CHEAP" in captured.out
        assert "summarize" in captured.out
        # Should not show capable tasks
        assert "fix_bug" not in captured.out

    @patch("attune.models.cli.get_all_tasks")
    def test_print_tasks_unknown_tier(self, mock_get_all_tasks, capsys):
        """Test printing tasks with unknown tier."""
        mock_get_all_tasks.return_value = {"cheap": [], "capable": []}

        with pytest.raises(SystemExit) as exc_info:
            print_tasks(tier="unknown")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Unknown tier" in captured.out


@pytest.mark.unit
class TestPrintCosts:
    """Test print_costs function."""

    @patch("attune.models.cli.get_all_models")
    def test_print_costs_table_format(self, mock_get_all_models, capsys):
        """Test printing costs in table format."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-haiku",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="cheap",
                ),
            },
        }

        print_costs(input_tokens=10000, output_tokens=2000)

        captured = capsys.readouterr()
        assert "COST ESTIMATES" in captured.out
        assert "10,000 input / 2,000 output tokens" in captured.out
        assert "$" in captured.out

    @patch("attune.models.cli.get_all_models")
    def test_print_costs_json_format(self, mock_get_all_models, capsys):
        """Test printing costs in JSON format."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-haiku",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="cheap",
                ),
            },
        }

        print_costs(input_tokens=10000, output_tokens=2000, format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "anthropic" in output
        assert "cheap" in output["anthropic"]
        assert "total_cost" in output["anthropic"]["cheap"]

    @patch("attune.models.cli.get_all_models")
    def test_print_costs_with_provider_filter(self, mock_get_all_models, capsys):
        """Test printing costs with provider filter."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="test",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="capable",
                ),
            },
        }

        print_costs(provider="anthropic")

        captured = capsys.readouterr()
        assert "ANTHROPIC" in captured.out

    @patch("attune.models.cli.get_all_models")
    def test_print_costs_unknown_provider(self, mock_get_all_models, capsys):
        """Test printing costs with unknown provider."""
        mock_get_all_models.return_value = {"anthropic": {}}

        with pytest.raises(SystemExit) as exc_info:
            print_costs(provider="unknown")

        assert exc_info.value.code == 1


@pytest.mark.unit
class TestPrintEffectiveConfig:
    """Test print_effective_config function."""

    @patch("attune.models.cli.get_all_models")
    @patch("attune.models.cli.get_tier_for_task")
    def test_print_effective_config(self, mock_get_tier, mock_get_all_models, capsys):
        """Test printing effective configuration."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="claude-haiku",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="cheap",
                ),
                "capable": ModelInfo(
                    id="claude-sonnet",
                    input_cost_per_million=3.0,
                    output_cost_per_million=15.0,
                    max_tokens=4096,
                    supports_vision=True,
                    supports_tools=True,
                    provider="anthropic",
                    tier="capable",
                ),
                "premium": ModelInfo(
                    id="claude-opus",
                    input_cost_per_million=15.0,
                    output_cost_per_million=75.0,
                    max_tokens=4096,
                    supports_vision=True,
                    supports_tools=True,
                    provider="anthropic",
                    tier="premium",
                ),
            },
        }
        mock_get_tier.return_value = ModelTier.CHEAP

        print_effective_config(provider="anthropic")

        captured = capsys.readouterr()
        assert "EFFECTIVE CONFIGURATION" in captured.out
        assert "ANTHROPIC" in captured.out
        assert "claude-haiku" in captured.out
        assert "Task Routing Examples" in captured.out

    @patch("attune.models.cli.get_all_models")
    def test_print_effective_config_unknown_provider(self, mock_get_all_models, capsys):
        """Test effective config with unknown provider."""
        mock_get_all_models.return_value = {"anthropic": {}}

        with pytest.raises(SystemExit) as exc_info:
            print_effective_config(provider="unknown")

        assert exc_info.value.code == 1


@pytest.mark.unit
class TestPrintTelemetrySummary:
    """Test print_telemetry_summary function."""

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_summary_table(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing telemetry summary in table format."""
        mock_store = MagicMock()
        mock_call = MagicMock()
        mock_call.estimated_cost = 0.01
        mock_call.success = True
        mock_store.get_calls.return_value = [mock_call, mock_call]
        mock_store.get_workflows.return_value = [MagicMock()]
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.tier_distribution.return_value = {
            "cheap": {"count": 10, "percent": 50.0},
            "capable": {"count": 10, "percent": 50.0},
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_summary(days=7)

        captured = capsys.readouterr()
        assert "TELEMETRY SUMMARY" in captured.out
        assert "Total LLM calls: 2" in captured.out
        assert "Total workflows: 1" in captured.out

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_summary_json(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing telemetry summary in JSON format."""
        mock_store = MagicMock()
        mock_call = MagicMock()
        mock_call.estimated_cost = 0.01
        mock_call.success = True
        mock_store.get_calls.return_value = [mock_call]
        mock_store.get_workflows.return_value = []
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_summary(days=7, format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "total_calls" in output
        assert output["period_days"] == 7


@pytest.mark.unit
class TestPrintTelemetryCosts:
    """Test print_telemetry_costs function."""

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_costs_table(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing telemetry costs in table format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.cost_savings_report.return_value = {
            "workflow_count": 10,
            "total_actual_cost": 1.50,
            "total_baseline_cost": 10.00,
            "total_savings": 8.50,
            "savings_percent": 85.0,
            "avg_cost_per_workflow": 0.15,
        }
        mock_analytics.top_expensive_workflows.return_value = [
            {"workflow_name": "code-review", "total_cost": 0.50, "run_count": 5},
        ]
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_costs(days=30)

        captured = capsys.readouterr()
        assert "COST SAVINGS REPORT" in captured.out
        assert "Workflow runs: 10" in captured.out
        assert "$1.5000" in captured.out
        assert "85.0%" in captured.out

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_costs_json(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing telemetry costs in JSON format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.cost_savings_report.return_value = {
            "total_savings": 5.0,
            "savings_percent": 50.0,
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_costs(days=30, format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "total_savings" in output


@pytest.mark.unit
class TestPrintTelemetryProviders:
    """Test print_telemetry_providers function."""

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_providers_table(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing provider usage in table format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.provider_usage_summary.return_value = {
            "anthropic": {
                "call_count": 100,
                "total_tokens": 50000,
                "total_cost": 2.50,
                "error_count": 2,
                "by_tier": {"cheap": 50, "capable": 40, "premium": 10},
            },
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_providers(days=30)

        captured = capsys.readouterr()
        assert "PROVIDER USAGE" in captured.out
        assert "ANTHROPIC" in captured.out
        assert "Calls: 100" in captured.out
        assert "$2.5000" in captured.out

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_providers_json(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing provider usage in JSON format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.provider_usage_summary.return_value = {
            "anthropic": {"call_count": 50},
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_providers(days=30, format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "anthropic" in output


@pytest.mark.unit
class TestPrintTelemetryFallbacks:
    """Test print_telemetry_fallbacks function."""

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_fallbacks_table(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing fallback stats in table format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.fallback_stats.return_value = {
            "total_calls": 100,
            "fallback_count": 5,
            "fallback_percent": 5.0,
            "error_count": 2,
            "error_rate": 2.0,
            "by_original_provider": {"anthropic": 3, "openai": 2},
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_fallbacks(days=30)

        captured = capsys.readouterr()
        assert "FALLBACK STATISTICS" in captured.out
        assert "Total calls: 100" in captured.out
        assert "Fallback count: 5" in captured.out
        assert "5.00%" in captured.out

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_fallbacks_json(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test printing fallback stats in JSON format."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.fallback_stats.return_value = {
            "total_calls": 50,
            "fallback_count": 2,
        }
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_fallbacks(days=30, format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "total_calls" in output
        assert output["fallback_count"] == 2


@pytest.mark.unit
class TestPrintProviderConfig:
    """Test print_provider_config function."""

    @patch("attune.models.cli.get_provider_config")
    def test_print_provider_config_table(self, mock_get_config, capsys):
        """Test printing provider config in table format."""
        mock_config = MagicMock()
        mock_config.mode.value = "hybrid"
        mock_config.primary_provider = "anthropic"
        mock_config.cost_optimization = True
        mock_config.prefer_local = False
        mock_config.available_providers = ["anthropic", "openai"]
        mock_config.tier_providers = {}

        mock_model = MagicMock()
        mock_model.id = "claude-sonnet"
        mock_model.provider = "anthropic"
        mock_config.get_effective_registry.return_value = {
            "cheap": mock_model,
            "capable": mock_model,
            "premium": mock_model,
        }
        mock_get_config.return_value = mock_config

        print_provider_config()

        captured = capsys.readouterr()
        assert "PROVIDER CONFIGURATION" in captured.out
        assert "Mode: hybrid" in captured.out
        assert "anthropic" in captured.out

    @patch("attune.models.cli.get_provider_config")
    def test_print_provider_config_json(self, mock_get_config, capsys):
        """Test printing provider config in JSON format."""
        mock_config = MagicMock()
        mock_config.to_dict.return_value = {"mode": "hybrid"}
        mock_config.available_providers = ["anthropic"]
        mock_model = MagicMock()
        mock_model.id = "test-model"
        mock_model.provider = "anthropic"
        mock_config.get_effective_registry.return_value = {"cheap": mock_model}
        mock_get_config.return_value = mock_config

        print_provider_config(format="json")

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "mode" in output


@pytest.mark.unit
class TestConfigureProvider:
    """Test configure_provider function."""

    @patch("attune.models.cli.configure_provider_interactive")
    def test_configure_provider_interactive(self, mock_configure_interactive):
        """Test interactive configuration."""
        result = configure_provider(interactive=True)

        assert result == 0
        mock_configure_interactive.assert_called_once()

    @patch("attune.models.cli.configure_provider_cli")
    @patch("attune.models.cli.print_provider_config")
    def test_configure_provider_set(self, mock_print_config, mock_configure_cli, capsys):
        """Test setting provider via CLI."""
        mock_config = MagicMock()
        mock_config.mode.value = "single"
        mock_config.primary_provider = "anthropic"
        mock_model = MagicMock()
        mock_model.id = "claude-sonnet"
        mock_config.get_effective_registry.return_value = {"cheap": mock_model}
        mock_configure_cli.return_value = mock_config

        result = configure_provider(provider="anthropic")

        assert result == 0
        mock_config.save.assert_called_once()
        captured = capsys.readouterr()
        assert "Provider configuration updated" in captured.out

    @patch("attune.models.cli.print_provider_config")
    def test_configure_provider_show_current(self, mock_print_config):
        """Test showing current configuration."""
        result = configure_provider()

        assert result == 0
        mock_print_config.assert_called_once()


@pytest.mark.unit
class TestMainCLI:
    """Test main CLI entry point."""

    @patch("attune.models.cli.print_registry")
    def test_main_registry_command(self, mock_print_registry):
        """Test registry command."""
        with patch.object(sys, "argv", ["cli", "registry"]):
            result = main()

        assert result == 0
        mock_print_registry.assert_called_once_with(None, "table")

    @patch("attune.models.cli.print_tasks")
    def test_main_tasks_command(self, mock_print_tasks):
        """Test tasks command."""
        with patch.object(sys, "argv", ["cli", "tasks"]):
            result = main()

        assert result == 0
        mock_print_tasks.assert_called_once_with(None, "table")

    @patch("attune.models.cli.print_costs")
    def test_main_costs_command(self, mock_print_costs):
        """Test costs command."""
        with patch.object(sys, "argv", ["cli", "costs"]):
            result = main()

        assert result == 0
        mock_print_costs.assert_called_once()

    @patch("attune.models.cli.print_effective_config")
    def test_main_effective_command(self, mock_print_effective):
        """Test effective command."""
        with patch.object(sys, "argv", ["cli", "effective"]):
            result = main()

        assert result == 0
        mock_print_effective.assert_called_once_with("anthropic")

    @patch("attune.models.cli.print_telemetry_summary")
    def test_main_telemetry_summary(self, mock_print_summary):
        """Test telemetry summary command."""
        with patch.object(sys, "argv", ["cli", "telemetry"]):
            result = main()

        assert result == 0
        mock_print_summary.assert_called_once()

    @patch("attune.models.cli.print_telemetry_costs")
    def test_main_telemetry_costs(self, mock_print_costs):
        """Test telemetry costs command."""
        with patch.object(sys, "argv", ["cli", "telemetry", "--costs"]):
            result = main()

        assert result == 0
        mock_print_costs.assert_called_once()

    @patch("attune.models.cli.print_telemetry_providers")
    def test_main_telemetry_providers(self, mock_print_providers):
        """Test telemetry providers command."""
        with patch.object(sys, "argv", ["cli", "telemetry", "--providers"]):
            result = main()

        assert result == 0
        mock_print_providers.assert_called_once()

    @patch("attune.models.cli.print_telemetry_fallbacks")
    def test_main_telemetry_fallbacks(self, mock_print_fallbacks):
        """Test telemetry fallbacks command."""
        with patch.object(sys, "argv", ["cli", "telemetry", "--fallbacks"]):
            result = main()

        assert result == 0
        mock_print_fallbacks.assert_called_once()

    @patch("attune.models.cli.print_provider_config")
    def test_main_provider_command(self, mock_print_provider):
        """Test provider command without arguments shows current config."""
        with patch.object(sys, "argv", ["cli", "provider"]):
            result = main()

        assert result == 0
        mock_print_provider.assert_called_once()

    def test_main_no_command(self, capsys):
        """Test main with no command."""
        with patch.object(sys, "argv", ["cli"]):
            result = main()

        assert result == 1


@pytest.mark.unit
class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    @patch("attune.models.cli.get_all_models")
    def test_print_costs_with_zero_tokens(self, mock_get_all_models, capsys):
        """Test printing costs with zero tokens."""
        mock_get_all_models.return_value = {
            "anthropic": {
                "cheap": ModelInfo(
                    id="test",
                    input_cost_per_million=0.25,
                    output_cost_per_million=1.25,
                    max_tokens=4096,
                    supports_vision=False,
                    supports_tools=True,
                    provider="anthropic",
                    tier="capable",
                ),
            },
        }

        print_costs(input_tokens=0, output_tokens=0)

        captured = capsys.readouterr()
        assert "$0.0000" in captured.out

    @patch("attune.models.cli.TelemetryAnalytics")
    @patch("attune.models.cli.TelemetryStore")
    def test_print_telemetry_summary_no_calls(self, mock_store_cls, mock_analytics_cls, capsys):
        """Test telemetry summary with no calls."""
        mock_store = MagicMock()
        mock_store.get_calls.return_value = []
        mock_store.get_workflows.return_value = []
        mock_store_cls.return_value = mock_store

        mock_analytics = MagicMock()
        mock_analytics.tier_distribution.return_value = {}
        mock_analytics_cls.return_value = mock_analytics

        print_telemetry_summary(days=7)

        captured = capsys.readouterr()
        assert "Total LLM calls: 0" in captured.out

    @patch("attune.models.cli.print_registry")
    def test_main_registry_with_json_format(self, mock_print_registry):
        """Test registry command with JSON format."""
        with patch.object(sys, "argv", ["cli", "registry", "--format", "json"]):
            result = main()

        assert result == 0
        mock_print_registry.assert_called_once_with(None, "json")

    @patch("attune.models.cli.print_costs")
    def test_main_costs_with_custom_tokens(self, mock_print_costs):
        """Test costs command with custom token counts."""
        with patch.object(
            sys,
            "argv",
            ["cli", "costs", "--input-tokens", "50000", "--output-tokens", "10000"],
        ):
            result = main()

        assert result == 0
        # print_costs is called with positional arguments
        args = mock_print_costs.call_args[0]
        assert args[0] == 50000  # input_tokens
        assert args[1] == 10000  # output_tokens

    @patch("attune.models.cli.configure_provider")
    def test_main_provider_set_hybrid(self, mock_configure):
        """Test provider command with --set hybrid."""
        mock_configure.return_value = 0

        with patch.object(sys, "argv", ["cli", "provider", "--set", "hybrid"]):
            result = main()

        assert result == 0
        mock_configure.assert_called_once()
        args = mock_configure.call_args[1]
        assert args["provider"] == "hybrid"
