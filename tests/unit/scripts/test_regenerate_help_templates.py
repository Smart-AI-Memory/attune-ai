"""Tests for ``scripts/regenerate_help_templates.py``.

Covers the load-bearing pure-Python helpers:

- ``_glob_to_regex`` — pattern → regex conversion
- ``_affected_features`` — changed-paths → affected-features filter
- ``_summarize_error`` — multi-line subprocess error → compact one-liner

The subprocess wrappers (``_regen_one`` / ``_stage_dir``) and
``main()`` orchestration are exercised manually in the warn-only +
auto-regen smoke runs documented in PR #400's follow-up; they're
not unit-tested here because mocking subprocess.run for a script
that ships outside the package surface adds maintenance for low
incremental confidence.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

# Load the script as a module without putting `scripts/` on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "regenerate_help_templates.py"
_spec = importlib.util.spec_from_file_location("regen_help_tpl", _SCRIPT)
assert _spec is not None and _spec.loader is not None
regen_module = importlib.util.module_from_spec(_spec)
sys.modules["regen_help_tpl"] = regen_module
_spec.loader.exec_module(regen_module)


@dataclass
class _FakeFeature:
    """Stand-in for attune.authoring Feature with the `files` attr we use."""

    files: list[str]


# ---------------------------------------------------------------------------
# _glob_to_regex
# ---------------------------------------------------------------------------


class TestGlobToRegex:
    def test_literal_match(self) -> None:
        pat = regen_module._glob_to_regex("src/foo.py")
        assert pat.fullmatch("src/foo.py")
        assert not pat.fullmatch("src/bar.py")

    def test_single_star_does_not_cross_separator(self) -> None:
        pat = regen_module._glob_to_regex("src/*.py")
        assert pat.fullmatch("src/foo.py")
        assert not pat.fullmatch("src/sub/foo.py")  # `*` is single-segment

    def test_double_star_crosses_separators(self) -> None:
        pat = regen_module._glob_to_regex("src/**/foo.py")
        assert pat.fullmatch("src/a/foo.py")
        assert pat.fullmatch("src/a/b/c/foo.py")

    def test_question_mark_single_char(self) -> None:
        pat = regen_module._glob_to_regex("src/f?o.py")
        assert pat.fullmatch("src/foo.py")
        assert pat.fullmatch("src/fxo.py")
        assert not pat.fullmatch("src/fo.py")
        assert not pat.fullmatch("src/foxo.py")

    def test_special_chars_escaped(self) -> None:
        # `.` in pattern should be a literal dot, not "any char"
        pat = regen_module._glob_to_regex("src/foo.py")
        assert not pat.fullmatch("src/fooXpy")

    def test_double_star_at_end_matches_subtree(self) -> None:
        pat = regen_module._glob_to_regex("src/attune/security/**")
        assert pat.fullmatch("src/attune/security/x.py")
        assert pat.fullmatch("src/attune/security/sub/x.py")


# ---------------------------------------------------------------------------
# _affected_features
# ---------------------------------------------------------------------------


class TestAffectedFeatures:
    def test_empty_features_returns_empty(self) -> None:
        result = regen_module._affected_features([Path("src/foo.py")], {})
        assert result == set()

    def test_no_match_returns_empty(self) -> None:
        features = {"a": _FakeFeature(files=["src/other/*.py"])}
        result = regen_module._affected_features([Path("src/foo.py")], features)
        assert result == set()

    def test_single_match(self) -> None:
        features = {
            "a": _FakeFeature(files=["src/attune/security/**"]),
            "b": _FakeFeature(files=["src/other/*.py"]),
        }
        result = regen_module._affected_features([Path("src/attune/security/foo.py")], features)
        assert result == {"a"}

    def test_multiple_paths_one_feature(self) -> None:
        # Two changed paths but only one feature matches them.
        features = {"a": _FakeFeature(files=["src/attune/security/**"])}
        result = regen_module._affected_features(
            [
                Path("src/attune/security/foo.py"),
                Path("src/attune/security/bar.py"),
            ],
            features,
        )
        assert result == {"a"}

    def test_multiple_features_one_path(self) -> None:
        # One changed path matches multiple features (overlap).
        features = {
            "a": _FakeFeature(files=["src/attune/security/**"]),
            "b": _FakeFeature(files=["src/attune/**"]),
        }
        result = regen_module._affected_features([Path("src/attune/security/foo.py")], features)
        assert result == {"a", "b"}

    def test_feature_with_empty_files_list(self) -> None:
        # No globs → no matches; doesn't crash on empty list.
        features = {"a": _FakeFeature(files=[])}
        result = regen_module._affected_features([Path("src/anything.py")], features)
        assert result == set()

    def test_feature_with_none_files(self) -> None:
        # Some Feature objects may have `files=None`; tolerate that.
        @dataclass
        class _NoneFeature:
            files: list[str] | None = None

        features = {"a": _NoneFeature()}
        result = regen_module._affected_features([Path("src/anything.py")], features)
        assert result == set()

    def test_first_match_wins_per_feature(self) -> None:
        # If first changed path matches feature A's first pattern,
        # we don't re-check later patterns for the same feature.
        features = {"a": _FakeFeature(files=["src/x.py", "src/y.py"])}
        result = regen_module._affected_features([Path("src/x.py"), Path("src/y.py")], features)
        assert result == {"a"}


# ---------------------------------------------------------------------------
# _summarize_error
# ---------------------------------------------------------------------------
