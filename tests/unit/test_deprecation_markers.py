"""Smoke tests for scripts/check_deprecation_markers.py.

The script is a CI gate, so we test the scan function directly with
synthetic file trees rather than spawning a subprocess.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def check_module():
    """Load scripts/check_deprecation_markers.py as a module."""
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "check_deprecation_markers.py"
    spec = importlib.util.spec_from_file_location("_check_dep_markers", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_dep_markers"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("_check_dep_markers", None)


def test_scan_finds_past_due_marker(check_module, tmp_path: Path) -> None:
    """A marker for a major <= current should be returned."""
    target = tmp_path / "legacy.py"
    target.write_text(
        '"""Old module.\n\nREMOVE IN v4.0.0 — see migration.md\n"""\n',
        encoding="utf-8",
    )
    offenders = check_module.scan(tmp_path, current_major=6)
    assert len(offenders) == 1
    path, lineno, _, version = offenders[0]
    assert path == target
    assert lineno == 3
    assert version == (4, 0, 0)


def test_scan_ignores_future_marker(check_module, tmp_path: Path) -> None:
    """A marker scheduled for a future major must not be flagged."""
    (tmp_path / "modern.py").write_text(
        '"""# REMOVE IN v9.0.0 — gated on future spec\n"""\n',
        encoding="utf-8",
    )
    assert check_module.scan(tmp_path, current_major=6) == []


def test_scan_handles_equal_major_as_past_due(check_module, tmp_path: Path) -> None:
    """Equal majors mean we're already shipping the version that was
    supposed to have deleted the code — count as past due."""
    (tmp_path / "edge.py").write_text(
        "# REMOVE IN v6.0.0 — same major as current\n", encoding="utf-8"
    )
    offenders = check_module.scan(tmp_path, current_major=6)
    assert len(offenders) == 1


def test_scan_ignores_non_python_non_markdown(check_module, tmp_path: Path) -> None:
    """Files outside .py/.md should be skipped."""
    (tmp_path / "skipme.txt").write_text(
        "REMOVE IN v4.0.0 — but in a .txt file\n", encoding="utf-8"
    )
    assert check_module.scan(tmp_path, current_major=99) == []


def test_repo_state_is_clean(check_module) -> None:
    """Regression guard: the live repo must have no past-due markers.

    If this fails, either delete the deprecated code that's past its
    target version, or bump the marker to a realistic future major.
    """
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = repo_root / "pyproject.toml"
    current_major = check_module._read_current_major(pyproject)
    src = repo_root / "src"
    offenders = check_module.scan(src, current_major)
    assert offenders == [], (
        f"Past-due deprecation markers found: " f"{[(str(p), v) for p, _, _, v in offenders]}"
    )
