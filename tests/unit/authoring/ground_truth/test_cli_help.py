"""Tests for the CLI-help ground-truth extractor.

Subprocess calls are mocked so tests are deterministic and never
shell out to a real CLI (mirrors the pattern in
``tests/unit/authoring/fact_check/test_cli_refs.py``).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.authoring.ground_truth import cli_help


def setup_function() -> None:
    """Each test starts with an empty ``lru_cache`` so mocks are honored."""
    cli_help.clear_cache()


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


def test_extract_cli_help_returns_stdout_on_success(tmp_path: Path) -> None:
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed("Usage: attune ops [OPTIONS]\n"),
    ):
        result = cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
    assert result == "Usage: attune ops [OPTIONS]\n"


def test_extract_cli_help_missing_executable_returns_empty(tmp_path: Path) -> None:
    """No ``executable`` short-circuits before the subprocess is ever spawned."""
    with patch.object(cli_help.subprocess, "run") as mock_run:
        result = cli_help.extract_cli_help("", "ops", project_root=tmp_path)
    assert result == ""
    mock_run.assert_not_called()


def test_extract_cli_help_missing_subcommand_returns_empty(tmp_path: Path) -> None:
    """No ``subcommand`` short-circuits before the subprocess is ever spawned."""
    with patch.object(cli_help.subprocess, "run") as mock_run:
        result = cli_help.extract_cli_help("attune", "", project_root=tmp_path)
    assert result == ""
    mock_run.assert_not_called()


def test_help_cached_oserror_returns_empty_string(tmp_path: Path) -> None:
    """A missing/unspawnable CLI (``OSError``, e.g. FileNotFoundError) degrades
    to an empty string rather than raising."""
    with patch.object(
        cli_help.subprocess,
        "run",
        side_effect=OSError("no such file or directory: 'ghost-cli'"),
    ):
        result = cli_help.extract_cli_help("ghost-cli", "ops", project_root=tmp_path)
    assert result == ""


def test_help_cached_timeout_returns_empty_string(tmp_path: Path) -> None:
    """A CLI that hangs past the 10-second cap degrades to an empty string."""
    with patch.object(
        cli_help.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(cmd="attune", timeout=10),
    ):
        result = cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
    assert result == ""


def test_help_cached_nonzero_returncode_returns_empty_string(tmp_path: Path) -> None:
    """A nonzero exit (e.g. unknown subcommand) degrades to an empty string
    and does not surface stderr to the caller."""
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed(stdout="", returncode=2),
    ):
        result = cli_help.extract_cli_help("attune", "ghost", project_root=tmp_path)
    assert result == ""


def test_help_cached_nonzero_returncode_logs_truncated_stderr(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The warning log includes the exit code and a truncated stderr tail."""

    long_stderr = "x" * 500
    caplog.set_level(logging.WARNING, logger="attune.authoring.ground_truth.cli_help")
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=long_stderr
        ),
    ):
        result = cli_help.extract_cli_help("attune", "broken", project_root=tmp_path)
    assert result == ""
    assert any("exited 1" in record.message for record in caplog.records)


def test_extract_cli_help_result_is_cached_per_executable_subcommand_cwd(tmp_path: Path) -> None:
    """Repeated calls with identical args hit the ``lru_cache`` — the
    subprocess is spawned exactly once."""
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed("Usage: attune ops [OPTIONS]\n"),
    ) as mock_run:
        first = cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
        second = cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
    assert first == second == "Usage: attune ops [OPTIONS]\n"
    assert mock_run.call_count == 1


def test_clear_cache_forces_resubprocess(tmp_path: Path) -> None:
    """``clear_cache`` resets the ``lru_cache`` so a subsequent call
    re-spawns the subprocess instead of returning a stale hit."""
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed("first\n"),
    ) as mock_run:
        cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
    cli_help.clear_cache()
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed("second\n"),
    ) as mock_run_2:
        result = cli_help.extract_cli_help("attune", "ops", project_root=tmp_path)
    assert result == "second\n"
    assert mock_run_2.call_count == 1
    assert mock_run.call_count == 1


def test_extract_cli_help_passes_cwd_and_args(tmp_path: Path) -> None:
    """``project_root`` is forwarded as the subprocess ``cwd``, and the
    argv is ``[executable, subcommand, "--help"]``."""
    with patch.object(
        cli_help.subprocess,
        "run",
        return_value=_completed("help text\n"),
    ) as mock_run:
        cli_help.extract_cli_help("attune", "workflow", project_root=tmp_path)
    call_kwargs = mock_run.call_args.kwargs
    call_args = mock_run.call_args.args
    argv = call_args[0] if call_args else call_kwargs.get("args")
    assert argv == ["attune", "workflow", "--help"]
    assert call_kwargs["cwd"] == str(tmp_path)
