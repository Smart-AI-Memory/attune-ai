"""Tests for the pyproject.toml config loader."""

from __future__ import annotations

from pathlib import Path

from attune.authoring.fact_check.config import load_config
from attune.authoring.fact_check.report import CHECK_MD_LINKS


def test_load_config_no_pyproject_returns_defaults(tmp_path: Path) -> None:
    """Empty project root → all-enabled, soft-fail defaults."""
    cfg = load_config(tmp_path)
    assert cfg.enabled is True
    assert cfg.soft_fail is True
    assert cfg.check_python_refs is True
    assert cfg.check_cli_refs is True
    assert cfg.check_md_links is True
    assert cfg.check_numeric_refs is True
    assert cfg.skip == {}


def test_load_config_disables_individual_checks(tmp_path: Path) -> None:
    """Per-check booleans flip from the table."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.attune-author.fact-check]\n"
        "check_md_links = false\n"
        "check_numeric_refs = false\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.check_md_links is False
    assert cfg.check_numeric_refs is False
    # Untouched checks stay on.
    assert cfg.check_python_refs is True


def test_load_config_skip_table(tmp_path: Path) -> None:
    """The ``skip`` sub-table populates ``cfg.skip``."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.attune-author.fact-check.skip]\n" '"docs/foo.md" = ["check_md_links"]\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.skip == {"docs/foo.md": [CHECK_MD_LINKS]}


def test_load_config_strict_mode(tmp_path: Path) -> None:
    """``soft_fail = false`` round-trips."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.attune-author.fact-check]\nsoft_fail = false\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.soft_fail is False


def test_load_config_ignores_unknown_keys(tmp_path: Path) -> None:
    """Forward-compat: unknown keys are silently ignored."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.attune-author.fact-check]\nfuture_phase_2_toggle = true\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.enabled is True
