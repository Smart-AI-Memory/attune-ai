"""Integration tests for :func:`ground_truth.build_context`."""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

from attune.authoring.ground_truth import (
    GroundTruthConfig,
    build_context,
    cli_help,
)
from attune.authoring.manifest import Feature


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(dedent(source), encoding="utf-8")
    return path


def _completed(stdout: str = "Usage: attune ops [OPTIONS]\n") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["attune", "ops", "--help"],
        returncode=0,
        stdout=stdout,
    )


def setup_function() -> None:
    cli_help.clear_cache()


def test_build_context_returns_none_when_disabled(tmp_path: Path) -> None:
    feature = Feature(name="demo", description="x", cli_command="ops")
    cfg = GroundTruthConfig(enabled=False)
    result = build_context(feature, [], project_root=tmp_path, config=cfg)
    assert result is None


def test_build_context_with_only_public_api(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        def public_function(x: int) -> int:
            return x
        """,
    )
    feature = Feature(name="demo", description="x", cli_command=None)
    cfg = GroundTruthConfig(inject_cli_help=False, inject_dataclasses=False)

    result = build_context(feature, [src], project_root=tmp_path, config=cfg)

    assert result is not None
    assert "<public_api>" in result
    assert "</public_api>" in result
    assert "public_function" in result
    assert "<cli_help>" not in result
    assert "<dataclasses>" not in result


def test_build_context_with_only_dataclasses(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Config:
            host: str
            port: int = 8080
        """,
    )
    feature = Feature(name="demo", description="x", cli_command=None)
    cfg = GroundTruthConfig(inject_cli_help=False, inject_public_api=False)

    result = build_context(feature, [src], project_root=tmp_path, config=cfg)

    assert result is not None
    assert "<dataclasses>" in result
    assert "class Config:" in result
    assert "host: str" in result


def test_build_context_with_cli_help_block(tmp_path: Path) -> None:
    feature = Feature(name="demo", description="x", cli_command="ops")
    cfg = GroundTruthConfig(inject_public_api=False, inject_dataclasses=False)

    with patch.object(cli_help.subprocess, "run") as mock_run:
        mock_run.return_value = _completed("Usage: attune ops --read-only\n")
        result = build_context(feature, [], project_root=tmp_path, config=cfg)

    assert result is not None
    assert "<cli_help>" in result
    assert "--read-only" in result


def test_build_context_skips_cli_help_when_feature_has_no_cli_command(tmp_path: Path) -> None:
    """A feature without cli_command set should not invoke the CLI subprocess."""
    feature = Feature(name="demo", description="x", cli_command=None)
    cfg = GroundTruthConfig(inject_public_api=False, inject_dataclasses=False)

    with patch.object(cli_help.subprocess, "run") as mock_run:
        result = build_context(feature, [], project_root=tmp_path, config=cfg)

    assert result is None
    mock_run.assert_not_called()


def test_build_context_returns_none_when_nothing_extractable(tmp_path: Path) -> None:
    """Empty source list + no cli_command + all-off configs returns None."""
    feature = Feature(name="demo", description="x", cli_command=None)
    result = build_context(feature, [], project_root=tmp_path)
    assert result is None


def test_build_context_returns_none_when_all_blocks_disabled(tmp_path: Path) -> None:
    src = _write(tmp_path, "module.py", "def x(): pass")
    feature = Feature(name="demo", description="x", cli_command="ops")
    cfg = GroundTruthConfig(
        inject_cli_help=False,
        inject_public_api=False,
        inject_dataclasses=False,
    )
    result = build_context(feature, [src], project_root=tmp_path, config=cfg)
    assert result is None


def test_build_context_includes_header(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "module.py",
        """
        def thing() -> None: pass
        """,
    )
    feature = Feature(name="demo", description="x", cli_command=None)
    cfg = GroundTruthConfig(inject_cli_help=False, inject_dataclasses=False)

    result = build_context(feature, [src], project_root=tmp_path, config=cfg)

    assert result is not None
    assert "## Ground-truth context" in result


def test_build_context_drops_blocks_to_fit_budget(tmp_path: Path) -> None:
    """Tight budget drops dataclasses before public_api."""
    api_src = _write(
        tmp_path,
        "api.py",
        """
        def big_function_name(x: int) -> int:
            return x
        """,
    )
    dc_src = _write(
        tmp_path,
        "models.py",
        """
        from dataclasses import dataclass

        @dataclass
        class Big:
            field_one: str
            field_two: str
            field_three: str
        """,
    )
    feature = Feature(name="demo", description="x", cli_command=None)
    # Budget big enough for public_api but not both.
    cfg = GroundTruthConfig(inject_cli_help=False, budget_bytes=200)

    result = build_context(feature, [api_src, dc_src], project_root=tmp_path, config=cfg)

    assert result is not None
    assert "public_api" in result
    assert "<dataclasses>" not in result
