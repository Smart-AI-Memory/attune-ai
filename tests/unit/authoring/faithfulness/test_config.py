"""Tests for the faithfulness config loader."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from attune.authoring.faithfulness import FaithfulnessConfig, load_config


def _write_pyproject(tmp_path: Path, body: str) -> None:
    (tmp_path / "pyproject.toml").write_text(dedent(body), encoding="utf-8")


def test_default_disabled_when_no_pyproject(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg == FaithfulnessConfig()
    assert cfg.enabled is False


def test_defaults_when_section_missing(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.fact-check]
        soft_fail = true
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg == FaithfulnessConfig()


def test_enables_via_pyproject(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.fact-check.faithfulness]
        enabled = true
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.enabled is True


def test_custom_threshold_and_budget(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.fact-check.faithfulness]
        enabled = true
        threshold = 0.8
        budget_per_file_usd = 0.25
        model = "claude-haiku-4-5"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.threshold == 0.8
    assert cfg.budget_per_file_usd == 0.25
    assert cfg.model == "claude-haiku-4-5"


def test_invalid_threshold_falls_back_to_default(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.fact-check.faithfulness]
        threshold = "not a number"
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.threshold == 0.95


def test_block_polish_on_unavailable_toggle(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
        [tool.attune-author.fact-check.faithfulness]
        block_polish_on_unavailable = true
        """,
    )
    cfg = load_config(tmp_path)
    assert cfg.block_polish_on_unavailable is True
