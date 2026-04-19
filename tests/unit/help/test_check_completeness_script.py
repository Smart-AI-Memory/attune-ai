"""Tests for scripts/check_help_completeness.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check_help_completeness.py"


@pytest.fixture
def check_module():
    """Load the script as a module."""
    spec = importlib.util.spec_from_file_location("_check_help_completeness", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_check_help_completeness"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_check_help_completeness", None)


def _write_manifest(help_dir: Path, features: list[str]) -> None:
    body = "version: 1\nfeatures:\n"
    for feat in features:
        body += f"  {feat}:\n    description: x\n    files:\n      - src/**\n"
    (help_dir / "features.yaml").write_text(body, encoding="utf-8")


def _write_templates(help_dir: Path, feature: str, kinds: list[str]) -> None:
    feat_dir = help_dir / "templates" / feature
    feat_dir.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        (feat_dir / f"{kind}.md").write_text(f"# {kind}\n", encoding="utf-8")


def test_ok_when_complete(tmp_path, check_module):
    help_dir = tmp_path / ".help"
    (help_dir / "templates").mkdir(parents=True)
    _write_manifest(help_dir, ["alpha"])
    _write_templates(help_dir, "alpha", sorted(check_module.EXPECTED_KINDS))

    result = check_module.check(help_dir)

    assert result["ok"] is True
    assert result["orphans"] == []
    assert result["incomplete"] == {}


def test_detects_orphan_dir(tmp_path, check_module):
    help_dir = tmp_path / ".help"
    (help_dir / "templates").mkdir(parents=True)
    _write_manifest(help_dir, ["alpha"])
    _write_templates(help_dir, "alpha", sorted(check_module.EXPECTED_KINDS))
    _write_templates(help_dir, "orphan-feat", ["concept", "task", "reference"])

    result = check_module.check(help_dir)

    assert result["ok"] is False
    assert result["orphans"] == ["orphan-feat"]


def test_detects_incomplete_feature(tmp_path, check_module):
    help_dir = tmp_path / ".help"
    (help_dir / "templates").mkdir(parents=True)
    _write_manifest(help_dir, ["alpha"])
    _write_templates(help_dir, "alpha", ["concept", "task", "reference"])

    result = check_module.check(help_dir)

    assert result["ok"] is False
    assert "alpha" in result["incomplete"]
    missing = set(result["incomplete"]["alpha"])
    assert "faq" in missing
    assert "quickstart" in missing


def test_detects_missing_dir_for_manifest_feature(tmp_path, check_module):
    help_dir = tmp_path / ".help"
    (help_dir / "templates").mkdir(parents=True)
    _write_manifest(help_dir, ["alpha", "beta"])
    _write_templates(help_dir, "alpha", sorted(check_module.EXPECTED_KINDS))

    result = check_module.check(help_dir)

    assert result["ok"] is False
    assert result["missing_dirs"] == ["beta"]
