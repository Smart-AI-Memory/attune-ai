"""Tests for autonomous_test_gen module.

Tests ValidationResult, CoverageResult dataclasses, and
AutonomousTestGenerator initialization and validation.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

from attune.workflows.autonomous_test_gen import CoverageResult, ValidationResult

# ---------------------------------------------------------------------------
# Tests for ValidationResult dataclass
# ---------------------------------------------------------------------------


class TestValidationResult:
    """Tests for the ValidationResult dataclass."""

    def test_passed_result(self):
        """ValidationResult with passed=True."""
        r = ValidationResult(passed=True, failures="", error_count=0, output="all passed")

        assert r.passed is True
        assert r.error_count == 0

    def test_failed_result(self):
        """ValidationResult with failures."""
        r = ValidationResult(
            passed=False,
            failures="test_foo FAILED",
            error_count=2,
            output="2 failed",
        )

        assert r.passed is False
        assert r.error_count == 2
        assert "FAILED" in r.failures


# ---------------------------------------------------------------------------
# Tests for CoverageResult dataclass
# ---------------------------------------------------------------------------


class TestCoverageResult:
    """Tests for the CoverageResult dataclass."""

    def test_coverage_result(self):
        """CoverageResult stores coverage data."""
        r = CoverageResult(
            coverage=85.5,
            missing_lines=[10, 20, 30],
            total_statements=100,
            covered_statements=85,
        )

        assert r.coverage == 85.5
        assert len(r.missing_lines) == 3
        assert r.total_statements == 100
        assert r.covered_statements == 85


# ---------------------------------------------------------------------------
# Tests for AutonomousTestGenerator
# ---------------------------------------------------------------------------


class TestAutonomousTestGeneratorInit:
    """Tests for AutonomousTestGenerator initialization."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_init_emits_deprecation_warning(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """Constructor emits DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                AutonomousTestGenerator(
                    agent_id="test-agent",
                    batch_num=1,
                    modules=[],
                )

            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
            assert "deprecated since v5.3.0" in str(w[-1].message).lower() or any(
                "deprecated" in str(warning.message).lower() for warning in w
            )

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_init_stores_config(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """Constructor stores configuration parameters."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator(
                    agent_id="agent-1",
                    batch_num=5,
                    modules=[{"file": "src/attune/foo.py"}],
                    enable_refinement=False,
                    max_refinement_iterations=5,
                    enable_coverage_guided=True,
                    target_coverage=0.90,
                )

            assert gen.agent_id == "agent-1"
            assert gen.batch_num == 5
            assert len(gen.modules) == 1
            assert gen.enable_refinement is False
            assert gen.max_refinement_iterations == 5
            assert gen.enable_coverage_guided is True
            assert gen.target_coverage == 0.90

    @patch(
        "attune.workflows.autonomous_test_gen.RedisShortTermMemory",
        side_effect=Exception("No Redis"),
    )
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    def test_init_graceful_redis_failure(self, mock_coord, mock_redis):
        """Handles Redis initialization failure gracefully."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator(
                    agent_id="test",
                    batch_num=1,
                    modules=[],
                )

            # Should still initialize with fallback coordinator
            assert gen.coordinator is not None
            assert gen.event_streamer is None
            assert gen.feedback_loop is None


# ---------------------------------------------------------------------------
# Tests for _validate_test_file
# ---------------------------------------------------------------------------


class TestValidateTestFile:
    """Tests for AutonomousTestGenerator._validate_test_file."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_invalid_syntax_returns_false(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """File with syntax errors fails validation."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator("test", 1, [])

        test_file = tmp_path / "test_bad.py"
        test_file.write_text("def broken(\n")

        assert gen._validate_test_file(test_file) is False

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_valid_syntax_file(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """File with valid syntax passes AST check (pytest collect may still fail)."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator("test", 1, [])

        test_file = tmp_path / "test_good.py"
        test_file.write_text("def test_example():\n    assert True\n")

        # Syntax check passes; pytest --collect-only may fail in isolation
        # but the AST parse step succeeds
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert gen._validate_test_file(test_file) is True


# ---------------------------------------------------------------------------
# Tests for _count_tests
# ---------------------------------------------------------------------------


class TestCountTests:
    """Tests for AutonomousTestGenerator._count_tests."""

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_count_returns_zero_on_error(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """Returns 0 when subprocess fails."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator("test", 1, [])

        with patch("subprocess.run", side_effect=Exception("fail")):
            assert gen._count_tests() == 0

    @patch("attune.workflows.autonomous_test_gen.RedisShortTermMemory")
    @patch("attune.workflows.autonomous_test_gen.HeartbeatCoordinator")
    @patch("attune.workflows.autonomous_test_gen.EventStreamer")
    @patch("attune.workflows.autonomous_test_gen.FeedbackLoop")
    def test_count_parses_output(
        self, mock_feedback, mock_streamer, mock_coord, mock_redis, tmp_path
    ):
        """Parses '42 tests collected' from pytest output."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with patch.object(Path, "mkdir"):
                from attune.workflows.autonomous_test_gen import AutonomousTestGenerator

                gen = AutonomousTestGenerator("test", 1, [])

        mock_result = MagicMock()
        mock_result.stdout = "42 tests collected\n"
        with patch("subprocess.run", return_value=mock_result):
            assert gen._count_tests() == 42
