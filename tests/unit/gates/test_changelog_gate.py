"""Pins the changelog-entry gate's decision rule.

Origin (2026-08-28): 10 of the last 14 ``src/``-touching PRs merged with
no CHANGELOG entry, and v16.1.0's notes had to be reconstructed by hand
at release time. The gate makes the author declare user-visibility while
they still know it.

The fixtures below are drawn from REAL merged PRs, including the two the
calibration pass identified as the reason a title-prefix rule was
rejected — ``refactor:``-titled PRs that were nonetheless user-visible
(#2321, #2319) alongside ``refactor:``/``fix:``-titled ones that were
purely internal (#2314, #2303). Under a declaration rule all four land in
the same bucket ("must declare"), which is exactly the point: the gate no
longer has to guess which kind it is looking at. If a future change
reintroduces title parsing, these cases are what it must still get right.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_GATE = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "changelog_gate.py"
_spec = importlib.util.spec_from_file_location("changelog_gate", _GATE)
assert _spec and _spec.loader
changelog_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(changelog_gate)

is_satisfied = changelog_gate.is_satisfied
touches_shipped_code = changelog_gate.touches_shipped_code
OPT_OUT_LABEL = changelog_gate.OPT_OUT_LABEL


class TestShippedCodeDetection:
    """Only paths that reach a user through the wheel count."""

    @pytest.mark.parametrize(
        "path",
        [
            "src/attune/roundtable/board.py",
            "attune_redis/memory.py",
        ],
    )
    def test_shipped_paths_are_detected(self, path: str) -> None:
        assert touches_shipped_code([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "tests/unit/roundtable/test_board.py",
            "docs/reference/API_REFERENCE.md",
            "website/app/page.tsx",
            "CHANGELOG.md",
            ".github/workflows/tests.yml",
            "scripts/bump_version.py",
        ],
    )
    def test_unshipped_paths_are_ignored(self, path: str) -> None:
        """tests/docs/website/scripts ship nothing — demanding prose for
        them is the noise that gets a gate allowlisted into uselessness."""
        assert touches_shipped_code([path]) is False


class TestGateDecision:
    """The three satisfying conditions, and the one failing one."""

    def test_shipped_change_without_entry_or_label_fails(self) -> None:
        assert is_satisfied(["src/attune/roundtable/board.py"], []) is False

    def test_changelog_entry_satisfies(self) -> None:
        assert is_satisfied(["src/attune/roundtable/board.py", "CHANGELOG.md"], []) is True

    def test_opt_out_label_satisfies(self) -> None:
        assert is_satisfied(["src/attune/roundtable/board.py"], [OPT_OUT_LABEL]) is True

    def test_unrelated_labels_do_not_satisfy(self) -> None:
        """Only the opt-out label counts; 'tests'/'core' must not leak
        through as an accidental exemption."""
        assert is_satisfied(["src/attune/models/auth.py"], ["tests", "core"]) is False

    def test_pr_shipping_nothing_is_exempt(self) -> None:
        assert is_satisfied(["tests/unit/test_x.py", "docs/guide.md"], []) is True

    def test_empty_diff_is_exempt(self) -> None:
        assert is_satisfied([], []) is True


class TestRealPRFixtures:
    """Cases from real merged PRs — the calibration record.

    A title-prefix rule was rejected because it split these four the wrong
    way. All must require a declaration; none may be silently exempt.
    """

    @pytest.mark.parametrize(
        "pr, paths",
        [
            # refactor:-titled but USER-VISIBLE (a title rule would miss these)
            ("#2321 config section rename", ["src/attune/config/core.py"]),
            ("#2319 deprecate WorkflowConfig twin", ["src/attune/config/models.py"]),
            # refactor:/fix:-titled and INTERNAL-ONLY (a title rule would
            # either miss them or, if refactor: were required, cry wolf)
            ("#2314 kill upward import", ["src/attune/models/router.py"]),
            (
                "#2303 monotonic clock de-flake",
                ["src/attune/agent_factory/decorators.py"],
            ),
        ],
    )
    def test_all_four_require_a_declaration(self, pr: str, paths: list[str]) -> None:
        assert is_satisfied(paths, []) is False, f"{pr} should require a declaration"

    @pytest.mark.parametrize(
        "pr, paths",
        [
            ("#2314 kill upward import", ["src/attune/models/router.py"]),
            (
                "#2303 monotonic clock de-flake",
                ["src/attune/agent_factory/decorators.py"],
            ),
        ],
    )
    def test_internal_only_prs_clear_with_the_label(self, pr: str, paths: list[str]) -> None:
        """The escape for genuinely internal work is one label, not an
        allowlist entry that outlives the PR."""
        assert is_satisfied(paths, [OPT_OUT_LABEL]) is True, pr


class TestFailClosed:
    """An uncomputable diff must ask for a declaration, not wave through."""

    def test_diff_failure_sentinel_requires_declaration(self) -> None:
        """``changed_paths`` returns ["src/"] when git fails; that sentinel
        must land on the failing side (contract principle 7)."""
        assert is_satisfied(["src/"], []) is False

    def test_diff_failure_sentinel_still_respects_the_label(self) -> None:
        assert is_satisfied(["src/"], [OPT_OUT_LABEL]) is True
