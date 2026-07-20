"""Tests for .github/scripts/auto_merge_guard.py.

Loaded via importlib.util because .github/scripts/ is not a Python
package — matches the repo convention used in
tests/unit/github_scripts/test_analyze_security_results.py.

The guard decides whether a PR's changed-file set is wholly within
the pre-authorized auto-merge class (test/docs only). These tests
are the regression guard for the class definition: any drift that
lets a src/ or CI change slip into the class must fail here.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "auto_merge_guard.py"


@pytest.fixture
def guard():
    spec = importlib.util.spec_from_file_location("_auto_merge_guard", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_auto_merge_guard"] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop("_auto_merge_guard", None)


# ---------------------------------------------------------------------------
# is_in_class — single path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "tests/unit/test_foo.py",
        "tests/conftest.py",
        "docs/guide.md",
        "docs/specs/x/decisions.md",
        ".help/templates/memory/concept.md",
        "README.md",
        "CHANGELOG.md",
        "SECURITY.md",
    ],
)
def test_in_class_paths_accepted(guard, path):
    assert guard.is_in_class(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "src/attune/config.py",
        "src/attune/workflows/base.py",
        ".github/workflows/tests.yml",
        ".github/scripts/auto_merge_guard.py",  # the guard cannot self-merge
        ".github/workflows/auto-merge-safe.yml",
        "pyproject.toml",
        "uv.lock",
        "requirements.txt",
        "mkdocs.yml",  # not *.md, not under docs/ -> excluded
        "attune_redis/foo.py",
        "scripts/release.py",
        "docs",  # bare dir name, no trailing slash -> not under docs/
        ".helpers/x.md",  # sibling of .help must not match the prefix
    ],
)
def test_out_of_class_paths_rejected(guard, path):
    assert guard.is_in_class(path) is False


def test_traversal_segment_rejected(guard):
    assert guard.is_in_class("tests/../src/evil.py") is False
    assert guard.is_in_class("docs/../../etc/passwd") is False


def test_empty_path_rejected(guard):
    assert guard.is_in_class("") is False


def test_nested_markdown_under_src_rejected(guard):
    # A markdown file NOT at root and not under an in-class dir.
    assert guard.is_in_class("src/attune/NOTES.md") is False


# ---------------------------------------------------------------------------
# is_safe_change — full set
# ---------------------------------------------------------------------------


def test_all_in_class_is_safe(guard):
    safe, offending = guard.is_safe_change(
        ["tests/unit/test_a.py", "docs/b.md", "README.md", ".help/x.md"]
    )
    assert safe is True
    assert offending == []


def test_any_out_of_class_is_unsafe(guard):
    safe, offending = guard.is_safe_change(["tests/unit/test_a.py", "src/attune/config.py"])
    assert safe is False
    assert offending == ["src/attune/config.py"]


def test_empty_set_is_unsafe_failclosed(guard):
    safe, offending = guard.is_safe_change([])
    assert safe is False
    assert offending == []


def test_rename_previous_path_out_of_class_is_unsafe(guard):
    # Workflow feeds filename + previous_filename; a rename out of
    # src/ into tests/ must be caught via the previous path.
    safe, offending = guard.is_safe_change(["tests/moved.py", "src/old.py"])
    assert safe is False
    assert "src/old.py" in offending


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_argv_safe_exits_zero(guard):
    assert guard.main(["prog", "tests/a.py", "docs/b.md"]) == 0


def test_cli_argv_unsafe_exits_one(guard):
    assert guard.main(["prog", "tests/a.py", "src/x.py"]) == 1


def test_cli_empty_argv_reads_stdin(guard, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("tests/a.py\ndocs/b.md\n"))
    assert guard.main(["prog"]) == 0


def test_cli_stdin_unsafe_exits_one(guard, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("src/x.py\n"))
    assert guard.main(["prog"]) == 1


def test_cli_empty_stdin_is_unsafe(guard, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert guard.main(["prog"]) == 1


# ---------------------------------------------------------------------------
# when-green mode (Class 2 — opt-in `auto-merge-when-green` label, D8)
#
# The when-green class allows ANY path EXCEPT `.github/` (merge
# automation and CI config can never self-merge, even labeled). The
# green-ness gate itself is GitHub native auto-merge, not this guard.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "src/attune/config.py",
        "pyproject.toml",
        "uv.lock",
        "tests/unit/test_a.py",
        "docs/guide.md",
        "plugin/skills/x/SKILL.md",
        "scripts/release.py",
        "mkdocs.yml",
        "attune_redis/foo.py",
    ],
)
def test_when_green_allows_non_github_paths(guard, path):
    assert guard.is_when_green_safe(path) is True


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/auto-merge-safe.yml",
        ".github/scripts/auto_merge_guard.py",
        ".github/workflows/tests.yml",
        ".github/dependabot.yml",
    ],
)
def test_when_green_blocks_github_paths(guard, path):
    assert guard.is_when_green_safe(path) is False


def test_when_green_blocks_traversal_and_empty(guard):
    assert guard.is_when_green_safe("src/../.github/evil.yml") is False
    assert guard.is_when_green_safe("") is False


def test_when_green_mode_full_set_flags_github_offender(guard):
    safe, offending = guard.is_safe_change(
        ["src/a.py", ".github/workflows/x.yml"], mode="when-green"
    )
    assert safe is False
    assert offending == [".github/workflows/x.yml"]


def test_when_green_mode_all_safe(guard):
    safe, offending = guard.is_safe_change(
        ["src/a.py", "pyproject.toml", "tests/t.py"], mode="when-green"
    )
    assert safe is True
    assert offending == []


def test_when_green_mode_empty_set_failclosed(guard):
    safe, offending = guard.is_safe_change([], mode="when-green")
    assert safe is False
    assert offending == []


def test_when_green_rename_out_of_github_is_unsafe(guard):
    # filename + previous_filename: a rename OUT of .github/ must be
    # caught via the previous path.
    safe, offending = guard.is_safe_change(
        ["scripts/moved.py", ".github/scripts/old.py"], mode="when-green"
    )
    assert safe is False
    assert ".github/scripts/old.py" in offending


def test_default_mode_is_tests_docs(guard):
    # No mode arg -> the original tight class; src/ stays out.
    safe, _ = guard.is_safe_change(["src/a.py"])
    assert safe is False


# ---------------------------------------------------------------------------
# CLI — --mode flag
# ---------------------------------------------------------------------------


def test_cli_mode_when_green_safe_exits_zero(guard):
    assert guard.main(["prog", "--mode", "when-green", "src/a.py"]) == 0


def test_cli_mode_when_green_unsafe_exits_one(guard):
    assert guard.main(["prog", "--mode", "when-green", ".github/workflows/tests.yml"]) == 1


def test_cli_mode_when_green_reads_stdin(guard, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("src/a.py\npyproject.toml\n"))
    assert guard.main(["prog", "--mode", "when-green"]) == 0


def test_cli_default_mode_unchanged(guard):
    # Regression guard: adding --mode must not loosen the default class.
    assert guard.main(["prog", "src/a.py"]) == 1


def test_cli_unknown_mode_exits_two(guard):
    assert guard.main(["prog", "--mode", "bogus", "src/a.py"]) == 2
