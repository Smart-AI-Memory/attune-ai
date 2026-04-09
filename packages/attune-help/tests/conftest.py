"""Shared fixtures for attune-help plugin tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
PYPROJECT = REPO_ROOT / "pyproject.toml"


@pytest.fixture
def plugin_root() -> Path:
    """Absolute path to the plugin directory."""
    return PLUGIN_ROOT


@pytest.fixture
def pyproject_path() -> Path:
    """Absolute path to pyproject.toml."""
    return PYPROJECT
