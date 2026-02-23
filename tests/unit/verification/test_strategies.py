"""Tests for verification strategies."""

from __future__ import annotations

import pytest

from attune.verification.strategies import (
    STRATEGY_REGISTRY,
    BuildStrategy,
    CustomCommandStrategy,
    LintCheckStrategy,
    RunTestsStrategy,
    TypeCheckStrategy,
    get_strategy,
)


class TestBuiltinStrategies:
    """Test built-in strategy command generation."""

    def test_run_tests_command(self) -> None:
        """Test RunTestsStrategy returns pytest command."""
        strategy = RunTestsStrategy()
        cmd = strategy.get_command("test-gen", None)
        assert "pytest" in cmd
        assert strategy.name == "run-tests"

    def test_lint_check_command(self) -> None:
        """Test LintCheckStrategy returns ruff command."""
        strategy = LintCheckStrategy()
        cmd = strategy.get_command("code-review", None)
        assert "ruff" in cmd
        assert "--no-fix" in cmd
        assert strategy.name == "lint-check"

    def test_type_check_command(self) -> None:
        """Test TypeCheckStrategy returns mypy command."""
        strategy = TypeCheckStrategy()
        cmd = strategy.get_command("security-audit", None)
        assert "mypy" in cmd
        assert strategy.name == "type-check"

    def test_build_command(self) -> None:
        """Test BuildStrategy returns build command."""
        strategy = BuildStrategy()
        cmd = strategy.get_command("release-prep", None)
        assert "build" in cmd
        assert strategy.name == "build"

    def test_custom_command(self) -> None:
        """Test CustomCommandStrategy returns user command."""
        strategy = CustomCommandStrategy("curl http://localhost/health")
        cmd = strategy.get_command("any-workflow", None)
        assert cmd == "curl http://localhost/health"
        assert strategy.name == "custom-command"

    def test_parse_result_default_exit_0(self) -> None:
        """Test default parse_result passes on exit code 0."""
        strategy = RunTestsStrategy()
        assert strategy.parse_result(0, "ok", "") is True
        assert strategy.parse_result(1, "fail", "") is False
        assert strategy.parse_result(2, "", "error") is False


class TestStrategyRegistry:
    """Test strategy registry and lookup."""

    def test_registry_contains_all_builtins(self) -> None:
        """Test registry has all built-in strategies."""
        expected = {"run-tests", "lint-check", "type-check", "build"}
        assert set(STRATEGY_REGISTRY.keys()) == expected

    def test_get_strategy_builtin(self) -> None:
        """Test get_strategy returns correct instances."""
        for name in STRATEGY_REGISTRY:
            strategy = get_strategy(name)
            assert strategy is not None
            assert strategy.name == name

    def test_get_strategy_none(self) -> None:
        """Test get_strategy returns None for 'none'."""
        assert get_strategy("none") is None

    def test_get_strategy_custom_command(self) -> None:
        """Test get_strategy with custom-command."""
        strategy = get_strategy("custom-command", "echo hello")
        assert strategy is not None
        assert isinstance(strategy, CustomCommandStrategy)
        assert strategy.get_command("any", None) == "echo hello"

    def test_get_strategy_custom_command_no_command_raises(self) -> None:
        """Test custom-command without command raises ValueError."""
        with pytest.raises(ValueError, match="requires a 'command'"):
            get_strategy("custom-command")

    def test_get_strategy_unknown_raises(self) -> None:
        """Test unknown strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown verification strategy"):
            get_strategy("nonexistent-strategy")
