"""Unit tests for scripts/check_readme_anchors.py.

The README's "Contents" nav links to headings by GitHub's auto-generated
slug; renaming a heading silently breaks every link that pointed at it.
The guard failed on first contact with the live README (``#privacy--
telemetry`` after ``## Privacy & Telemetry`` became ``## Security,
Privacy & Telemetry``, fixed in the same PR that landed the script), so
these tests pin the slug rules, both detection directions, the
suggestion text, and the live README staying clean.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "check_readme_anchors.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_check_readme_anchors", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestSlug:
    def test_lowercases_and_hyphenates_whitespace(self, mod):
        assert mod.slugify("Quick Start") == "quick-start"

    def test_drops_punctuation_but_keeps_hyphens(self, mod):
        # "Security, Privacy & Telemetry" -> the "&" vanishes, leaving a
        # double hyphen — exactly the shape GitHub renders.
        assert mod.slugify("Security, Privacy & Telemetry") == "security-privacy--telemetry"

    def test_duplicate_headings_get_numbered(self, mod, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Usage\n\n## Usage\n\n[a](#usage) [b](#usage-1)\n")
        assert mod.check(readme) == []


class TestCheck:
    def test_resolving_links_pass(self, mod, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Quick Start\n\n[go](#quick-start)\n")
        assert mod.check(readme) == []

    def test_renamed_heading_breaks_the_link(self, mod, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Security, Privacy & Telemetry\n\n[p](#privacy--telemetry)\n")
        problems = mod.check(readme)
        assert len(problems) == 1
        assert "#privacy--telemetry matches no heading" in problems[0]
        # The failure names what to write instead, not just what broke.
        assert "did you mean #security-privacy--telemetry" in problems[0]

    def test_missing_file_is_a_problem_not_a_crash(self, mod, tmp_path):
        problems = mod.check(tmp_path / "nope.md")
        assert problems and "file not found" in problems[0]

    def test_main_exit_codes(self, mod, tmp_path, capsys):
        good = tmp_path / "good.md"
        good.write_text("## A\n\n[a](#a)\n")
        bad = tmp_path / "bad.md"
        bad.write_text("## A\n\n[b](#b)\n")
        assert mod.main(["x", str(good)]) == 0
        assert mod.main(["x", str(bad)]) == 1
        assert "Broken in-page README links" in capsys.readouterr().err


def test_live_readme_anchors_resolve(mod):
    """The tracked README must stay clean — this is the CI gate's contract."""
    assert mod.check(REPO / "README.md") == []
