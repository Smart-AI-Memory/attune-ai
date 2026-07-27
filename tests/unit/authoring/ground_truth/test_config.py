"""Tests for ground-truth config loading from pyproject.toml."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from attune.authoring.ground_truth.config import GroundTruthConfig, load_config


def _write_pyproject(tmp_path: Path, contents: str) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(dedent(contents), encoding="utf-8")
    return pyproject


def test_defaults_when_no_pyproject(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.enabled is True
    assert cfg.inject_cli_help is True
    assert cfg.inject_public_api is True
    assert cfg.inject_dataclasses is True
    assert cfg.budget_bytes == 5 * 1024
    assert cfg.cli_executable == "attune"


def test_defaults_when_section_missing(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [project]
        name = "demo"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg == GroundTruthConfig()


def test_disable_master_switch(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.context-injection]
        enabled = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.enabled is False


def test_per_source_toggles(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.context-injection]
        inject_cli_help = false
        inject_public_api = true
        inject_dataclasses = false
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.inject_cli_help is False
    assert cfg.inject_public_api is True
    assert cfg.inject_dataclasses is False


def test_budget_override(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.context-injection]
        budget_bytes = 1024
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.budget_bytes == 1024


def test_cli_executable_override(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.context-injection]
        cli_executable = "myapp"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.cli_executable == "myapp"


def test_malformed_toml_falls_back_to_defaults(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("not = valid = toml", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg == GroundTruthConfig()


def test_invalid_budget_falls_back_to_default(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.context-injection]
        budget_bytes = "not a number"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.budget_bytes == 5 * 1024
