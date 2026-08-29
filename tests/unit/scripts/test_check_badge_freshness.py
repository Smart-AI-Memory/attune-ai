"""Unit tests for scripts/check_badge_freshness.py's New-in check.

Check 4 (retro ruling 2026-08-29, item 1): the README's rotating
"New in <version>" slot sat two releases stale (15.0.0 while 16.1.0
shipped) before a manual truth pass caught it. ``newin_problem``
makes the rotation mechanical; these tests pin both directions and
the missing-slot case, plus the live README/pyproject pair staying
in sync.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "check_badge_freshness.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_check_badge_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestNewinProblem:
    def test_fresh_slot_passes(self, mod):
        assert mod.newin_problem("## New in 16.1.0 — headline\n", "16.1.0") is None

    def test_stale_slot_fails(self, mod):
        problem = mod.newin_problem("## New in 15.0.0 — headline\n", "16.1.0")
        assert problem is not None and "STALE" in problem

    def test_missing_slot_fails(self, mod):
        problem = mod.newin_problem("# README\nno rotating slot here\n", "16.1.0")
        assert problem is not None and "not found" in problem

    def test_heading_must_be_h2_at_line_start(self, mod):
        # An inline mention ("Previously new in 15.0.0" in a details
        # summary) must not satisfy or trip the check.
        text = "<summary>Previously new in 15.0.0</summary>\n## New in 16.1.0 — x\n"
        assert mod.newin_problem(text, "16.1.0") is None


def test_live_readme_slot_matches_package(mod):
    """The real README's slot must match the real pyproject version."""
    text = (REPO / "README.md").read_text(encoding="utf-8")
    pkg = mod._pkg_version()
    assert pkg, "pyproject version not parseable"
    assert mod.newin_problem(text, pkg) is None
