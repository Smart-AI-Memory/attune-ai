"""cross-review T1: target resolution, manifest math, lint matrix,
advisory invariant, board degrade, ledger rendering."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from attune.roundtable import review
from attune.roundtable.compiler import ROLE_REPLY_CHARS


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=fixture@test",
            "-c",
            "user.name=Fixture",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "small.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "small.py")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "feature/rv")
    (root / "small.py").write_text("x = 2\n", encoding="utf-8")
    (root / "big.py").write_text("\n".join(f"line{i} = {i}" for i in range(60)) + "\n", "utf-8")
    _git(root, "add", "small.py", "big.py")
    _git(root, "commit", "-q", "-m", "feature work")
    return root


class RecordingBoard:
    def __init__(self) -> None:
        self.posts: list[dict[str, Any]] = []

    def post_message(self, thread: str, author: str, kind: str, body: str, **extra: Any) -> int:
        self.posts.append({"thread": thread, "author": author, "kind": kind, "body": body, **extra})
        return len(self.posts)


class DeadBoard:
    def post_message(self, *args: Any, **kwargs: Any) -> int:
        raise ConnectionError("redis unreachable")


def _invoke_stub(reply: str, code: int = 0):
    calls: list[dict[str, Any]] = []

    def invoke(recipe, brief, reply_chars=8000):
        calls.append({"recipe": tuple(recipe), "brief": brief, "reply_chars": reply_chars})
        return code, reply

    invoke.calls = calls
    return invoke


class TestTargetResolution:
    def test_branch_mode_diffs_vs_merge_base(self, repo: Path) -> None:
        target = review.resolve_target(repo, base_ref="main")
        assert target["branch"] == "feature/rv"
        assert set(target["per_file"]) == {"small.py", "big.py"}
        assert "x = 2" in target["per_file"]["small.py"]

    def test_staged_mode(self, repo: Path) -> None:
        (repo / "staged.py").write_text("s = 1\n", encoding="utf-8")
        _git(repo, "add", "staged.py")
        target = review.resolve_target(repo, mode="staged")
        assert set(target["per_file"]) == {"staged.py"}

    def test_unknown_mode_rejected(self, repo: Path) -> None:
        with pytest.raises(review.ReviewTargetError, match="unknown review mode"):
            review.resolve_target(repo, mode="everything")

    def test_mutating_git_subcommand_rejected(self, repo: Path) -> None:
        with pytest.raises(review.ReviewTargetError, match="not allowlisted"):
            review._git(repo, "commit", "-m", "nope")


class TestManifest:
    def test_cap_splits_sent_and_omitted_largest_first(self) -> None:
        per_file = {"a.py": "x" * 50, "b.py": "y" * 200, "c.py": "z" * 30}
        manifest = review.budget_manifest(per_file, cap_chars=100)
        assert manifest["sent"] == ["a.py", "c.py"]
        assert manifest["omitted"] == ["b.py"]
        assert manifest["chars"] == 80

    def test_src_outranks_larger_projection_under_cap(self) -> None:
        """The cap eats projections, never the src edit (2026-08-19 retro)."""
        per_file = {
            "plugin/help/generated/concepts/hooks.md": "p" * 90,
            "src/attune/hooks/config.py": "s" * 30,
            "tests/hooks/test_config.py": "t" * 30,
        }
        manifest = review.budget_manifest(per_file, cap_chars=100)
        assert manifest["sent"] == [
            "src/attune/hooks/config.py",
            "tests/hooks/test_config.py",
        ]
        assert manifest["omitted"] == ["plugin/help/generated/concepts/hooks.md"]

    def test_projection_prefixes_rank_last_within_docs(self) -> None:
        """Hand-authored non-src files still outrank known projections."""
        per_file = {
            ".help/templates/hooks/faq.md": "a" * 40,
            "docs/architecture/post-compact-continuity.md": "b" * 40,
            "attune-ai-dev/help/hooks/faq.html": "c" * 40,
        }
        manifest = review.budget_manifest(per_file, cap_chars=90)
        assert manifest["sent"][0] == "docs/architecture/post-compact-continuity.md"
        assert len(manifest["omitted"]) == 1

    def test_manifest_note_names_omissions(self) -> None:
        manifest = {"sent": ["a.py"], "omitted": ["b.py"], "chars": 10, "cap": 100}
        note = review.manifest_note(manifest)
        assert "OMITTED" in note and "b.py" in note and "PARTIAL" in note

    def test_no_omissions_no_partial_language(self) -> None:
        manifest = {"sent": ["a.py"], "omitted": [], "chars": 10, "cap": 100}
        note = review.manifest_note(manifest)
        assert "PARTIAL" not in note


class TestLintMatrix:
    def test_compliant_findings(self) -> None:
        text = "FINDING: src/x.py:12 [high] off-by-one in loop bound"
        assert review.lint_review(text) == []
        findings = review.parse_findings(text)
        assert findings == [
            {
                "file": "src/x.py",
                "line": 12,
                "severity": "high",
                "claim": "off-by-one in loop bound",
            }
        ]

    def test_no_findings_literal_is_compliant(self) -> None:
        assert review.lint_review("NO FINDINGS") == []

    def test_prose_is_noncompliant(self) -> None:
        assert review.lint_review("Looks good to me overall!") != []

    def test_empty_is_noncompliant(self) -> None:
        assert review.lint_review("  \n") != []


class TestAdvisoryInvariant:
    """ok is True for findings / clean / absent / noncompliant alike."""

    def test_findings_run(self, repo: Path) -> None:
        board = RecordingBoard()
        invoke = _invoke_stub("FINDING: big.py:3 [low] magic numbers")
        result = review.run_review(repo, base_ref="main", board=board, invoke_seat=invoke)
        assert result["ok"] is True
        assert result["status"] == "findings"
        assert len(result["findings"]) == 1
        assert result["board"] == "posted"
        assert board.posts[0]["status"] == "findings"
        assert board.posts[0]["thread"].startswith("review-feature-rv-")
        assert invoke.calls[0]["reply_chars"] == ROLE_REPLY_CHARS["reviewer"]

    def test_clean_run(self, repo: Path) -> None:
        result = review.run_review(
            repo, base_ref="main", board=RecordingBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        assert result["ok"] is True
        assert result["status"] == "clean"
        assert result["findings"] == []

    def test_absent_seat_never_fabricates(self, repo: Path) -> None:
        board = RecordingBoard()
        result = review.run_review(
            repo,
            base_ref="main",
            board=board,
            invoke_seat=_invoke_stub("codex: not found", code=127),
        )
        assert result["ok"] is True
        assert result["status"] == "absent"
        assert result["findings"] == []
        assert board.posts[0]["body"].startswith("ABSENT — exit 127")

    def test_noncompliant_posted_as_received(self, repo: Path) -> None:
        board = RecordingBoard()
        result = review.run_review(
            repo,
            base_ref="main",
            board=board,
            invoke_seat=_invoke_stub("I think this is fine."),
        )
        assert result["ok"] is True
        assert result["status"] == "format_noncompliant"
        assert board.posts[0]["body"] == "I think this is fine."

    def test_dead_board_degrades_not_fails(self, repo: Path) -> None:
        result = review.run_review(
            repo, base_ref="main", board=DeadBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        assert result["ok"] is True
        assert result["board"].startswith("skipped")

    def test_unknown_seat_rejected(self, repo: Path) -> None:
        with pytest.raises(review.ReviewTargetError, match="unknown seat"):
            review.run_review(repo, seat="gpt-9", base_ref="main")


class TestLedger:
    @pytest.mark.parametrize(
        ("env", "host", "self_review", "stamp"),
        [
            ({"CODEX_SESSION_ID": "s1"}, "codex", True, "true"),
            ({"CLAUDECODE": "1"}, "claude", False, "false"),
            ({}, None, None, "null"),
            ({"CLAUDECODE": "1", "CODEX_SESSION_ID": "s1"}, None, None, "null"),
        ],
    )
    def test_saved_receipts_preserve_independence(
        self, repo, monkeypatch, env, host, self_review, stamp
    ) -> None:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        board = RecordingBoard()
        result = review.run_review(
            repo,
            seat="codex",
            base_ref="main",
            board=board,
            invoke_seat=_invoke_stub("NO FINDINGS"),
        )
        assert board.posts[0]["host"] == host
        assert board.posts[0]["self_review"] is self_review
        assert board.posts[0]["claude_auth"] is None
        cells = [c.strip() for c in review.ledger_row(result).strip("|").split("|")]
        assert len(cells) == 6
        assert f"host={host or 'unknown'}" in cells[2]
        assert f"self_review={stamp}" in cells[2]

    def test_row_shape(self, repo: Path) -> None:
        result = review.run_review(
            repo,
            base_ref="main",
            board=RecordingBoard(),
            invoke_seat=_invoke_stub("FINDING: big.py:3 [low] magic numbers"),
        )
        row = review.ledger_row(result)
        cells = [c.strip() for c in row.strip("|").split("|")]
        assert cells[1] == "codex"
        assert cells[3] == "2 sent / 0 omitted"
        assert cells[4] == "1 (findings)"
        assert cells[5] == "not-triaged"

    def test_disposition_override(self, repo: Path) -> None:
        result = review.run_review(
            repo,
            base_ref="main",
            board=RecordingBoard(),
            invoke_seat=_invoke_stub("FINDING: big.py:3 [low] magic numbers"),
        )
        assert review.ledger_row(result, disposition="real — accepted").endswith(
            "| real — accepted |"
        )


class TestDispositionCheck:
    """check_disposition mirrors both ledger gates (2026-08-24 retro).

    The two fixtures below are the EXACT rows that went red on PR #2268
    — one per gate — pinned so the mirror never loses the discriminators
    that were paid for with two CI rounds.
    """

    def test_unclassifiable_leading_shape_flagged(self) -> None:
        problems = review.check_disposition("1 modified, 2 rejected — modified-accept (…)", 3)
        assert problems and "cannot classify" in problems[0]

    def test_rejected_without_claim_reason_flagged(self) -> None:
        problems = review.check_disposition("rejected — all three. The merge-patch claim (…)", 3)
        assert problems and "D11a" in problems[0]

    def test_compliant_forms_pass(self) -> None:
        for disposition, findings in [
            ("clean — NO FINDINGS", 0),
            ("real — accepted and fixed in-branch", 2),
            ("both real — accepted", 2),
            ("2 real, 2 rejected — real (medium): …", 4),
            ('rejected — claim: "x" — reason: refuted by inspection', 1),
        ]:
            assert review.check_disposition(disposition, findings) == [], disposition

    def test_count_contradictions_flagged(self) -> None:
        assert review.check_disposition("5 real", 3)
        assert review.check_disposition("clean", 2)

    def test_ledger_row_raises_on_noncompliant_disposition(self, repo: Path) -> None:
        result = review.run_review(
            repo,
            base_ref="main",
            board=RecordingBoard(),
            invoke_seat=_invoke_stub("FINDING: big.py:3 [low] magic numbers"),
        )
        with pytest.raises(ValueError, match="fails the gates"):
            review.ledger_row(result, disposition="1 modified, 2 rejected — …")

    def test_clean_lane_self_classifies_and_passes_the_gates(self, repo: Path) -> None:
        """A clean lane must not emit the placeholder.

        ``not-triaged`` is not a legal disposition — ledger_precision's
        tally rejects any row it cannot classify — so emitting it for a
        no-findings lane made the module's own output fail the repo's
        own pre-commit gate, and every clean lane cost a hand-edit
        (2026-09-08). The round-trip through check_disposition is the
        point of this test, not the wording.
        """
        result = review.run_review(
            repo, base_ref="main", board=RecordingBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        row = review.ledger_row(result)
        disposition = [c.strip() for c in row.strip("|").split("|")][5]
        assert disposition.startswith("clean")
        assert review.check_disposition(disposition, 0) == []

    def test_clean_on_partial_manifest_says_so_in_the_disposition(self) -> None:
        """Clean-on-partial is the case the spec warns about."""
        result = {
            "seat": "codex",
            "target": "branch vs merge-base abc1234",
            "status": "clean",
            "findings": [],
            "manifest": {"sent": ["a.py"], "omitted": ["b.py", "c.py"]},
        }
        disposition = [c.strip() for c in review.ledger_row(result).strip("|").split("|")][5]
        assert "OMITTED 2" in disposition
        assert review.check_disposition(disposition, 0) == []

    @pytest.mark.parametrize("status", ["absent", "format_noncompliant"])
    def test_lane_that_judged_nothing_keeps_the_placeholder(self, status: str) -> None:
        """Zero findings is not "clean" when the seat never reviewed.

        An ABSENT lane carries zero findings because it read nothing;
        the tally deliberately skips those rows, and auto-classifying
        one as clean would launder a non-review into a receipt.
        """
        result = {
            "seat": "codex",
            "target": "branch vs merge-base abc1234",
            "status": status,
            "findings": [],
            "manifest": {"sent": [], "omitted": []},
        }
        assert review.ledger_row(result).endswith("| not-triaged |")

    def test_explicit_disposition_still_overrides_a_clean_lane(self, repo: Path) -> None:
        result = review.run_review(
            repo, base_ref="main", board=RecordingBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        assert review.ledger_row(result, disposition="clean — triaged by hand").endswith(
            "| clean — triaged by hand |"
        )


class TestPriorRejections:
    """Re-lane briefs carry earlier rejections (2026-08-24 retro)."""

    def test_rejections_reach_the_brief(self, repo: Path) -> None:
        seen: list[str] = []

        def spy_invoke(recipe, brief, reply_chars=0):
            seen.append(brief)
            return 0, "NO FINDINGS"

        review.run_review(
            repo,
            base_ref="main",
            board=RecordingBoard(),
            invoke_seat=spy_invoke,
            prior_rejections=["cwd=self.repo_path — no such attribute exists (refuted)"],
        )
        assert "Previously REJECTED" in seen[0]
        assert "cwd=self.repo_path" in seen[0]

    def test_no_rejections_no_block(self, repo: Path) -> None:
        seen: list[str] = []

        def spy_invoke(recipe, brief, reply_chars=0):
            seen.append(brief)
            return 0, "NO FINDINGS"

        review.run_review(repo, base_ref="main", board=RecordingBoard(), invoke_seat=spy_invoke)
        assert "Previously REJECTED" not in seen[0]

    def test_all_real_count_contradictions_flagged(self) -> None:
        """Lane finding (2026-08-24): 'both real' with 1 finding and bare
        'real' with 0 findings are contradictions, not valid rows."""
        assert review.check_disposition("both real — accepted", 1)
        assert review.check_disposition("real — accepted", 0)
        assert review.check_disposition("both real — accepted", 2) == []

    def test_rejections_are_bounded(self, repo: Path) -> None:
        """A long rejection history cannot crowd out the diff (re-lane
        finding, 2026-08-24): entries cap at 300 chars, list at 12."""
        seen: list[str] = []

        def spy_invoke(recipe, brief, reply_chars=0):
            seen.append(brief)
            return 0, "NO FINDINGS"

        review.run_review(
            repo,
            base_ref="main",
            board=RecordingBoard(),
            invoke_seat=spy_invoke,
            prior_rejections=[f"claim {i}: " + "x" * 1000 for i in range(30)],
        )
        block = seen[0].split("Previously REJECTED")[1]
        assert len(block) < 12 * 320 + 200
        assert "+18 more rejections truncated" in block


class TestGovernancePriority:
    """Governance surfaces rank behind tests, ahead of docs (retro O2)."""

    def test_tiny_governance_file_beats_large_doc(self) -> None:
        per_file = {
            "docs/guide.md": "d" * 80,
            ".claude/gates/empathy-allowlist.txt": "g" * 10,
            "pyproject.toml": "p" * 10,
        }
        manifest = review.budget_manifest(per_file, cap_chars=30)
        assert manifest["sent"] == [
            ".claude/gates/empathy-allowlist.txt",
            "pyproject.toml",
        ]
        assert manifest["omitted"] == ["docs/guide.md"]

    def test_src_and_tests_still_outrank_governance(self) -> None:
        per_file = {
            "pyproject.toml": "p" * 40,
            "src/attune/a.py": "s" * 40,
            "tests/unit/test_a.py": "t" * 40,
        }
        manifest = review.budget_manifest(per_file, cap_chars=90)
        assert manifest["sent"] == ["src/attune/a.py", "tests/unit/test_a.py"]
        assert manifest["omitted"] == ["pyproject.toml"]


class TestScopedReview:
    """paths= scopes the lane to named files (the partial-lane re-run)."""

    def test_scoped_run_reviews_only_named_paths(self, repo: Path) -> None:
        invoke = _invoke_stub("NO FINDINGS")
        result = review.run_review(
            repo,
            base_ref="main",
            invoke_seat=invoke,
            paths=["small.py"],
        )
        assert result["scoped_to"] == ["small.py"]
        assert result["manifest"]["sent"] == ["small.py"]
        assert "big.py" not in result["manifest"]["omitted"]
        assert "SCOPED to 1 path(s)" in result["target"]
        # The seat's brief says so too — a scoped lane must not read as full.
        assert "SCOPED" in invoke.calls[0]["brief"]

    def test_partial_scope_miss_raises_fail_closed(self, repo: Path) -> None:
        """Codex re-lane finding: a silently shrunk scope must not pass."""
        with pytest.raises(review.ReviewTargetError, match="not/in/diff.py"):
            review.run_review(
                repo,
                base_ref="main",
                invoke_seat=_invoke_stub("NO FINDINGS"),
                paths=["small.py", "not/in/diff.py"],
            )

    def test_unscoped_run_carries_no_scope_keys(self, repo: Path) -> None:
        result = review.run_review(repo, base_ref="main", invoke_seat=_invoke_stub("NO FINDINGS"))
        assert "scoped_to" not in result
        assert "scope_misses" not in result


class TestScopedReviewFailClosed:
    """Codex D11 findings on the O2 branch, pinned (2026-08-24)."""

    def test_all_miss_scope_raises_instead_of_clean(self, repo: Path) -> None:
        with pytest.raises(review.ReviewTargetError, match="not in the diff"):
            review.run_review(
                repo,
                base_ref="main",
                invoke_seat=_invoke_stub("NO FINDINGS"),
                paths=["not/in/diff.py", "also/missing.py"],
            )

    def test_lookalike_governance_names_do_not_outrank_docs(self) -> None:
        per_file = {
            "docs/guide.md": "d" * 20,
            "pyproject.toml.bak": "b" * 20,
            "codecov.yml.old": "o" * 20,
        }
        manifest = review.budget_manifest(per_file, cap_chars=20)
        assert manifest["sent"] == ["docs/guide.md"]


@pytest.mark.parametrize("cap", [0, -1, 250001, True, 1.5, "60000"])
def test_invalid_explicit_diff_budget_fails_before_launch(repo, cap):
    invoke = _invoke_stub("NO FINDINGS")
    with pytest.raises(review.ReviewTargetError, match="diff_cap_chars"):
        review.run_review(repo, base_ref="main", invoke_seat=invoke, diff_cap_chars=cap)
    assert not invoke.calls


def test_complete_review_refuses_omitted_files_before_launch(repo):
    invoke = _invoke_stub("NO FINDINGS")
    with pytest.raises(review.ReviewTargetError, match="incomplete review:.*big.py"):
        review.run_review(
            repo, base_ref="main", invoke_seat=invoke, diff_cap_chars=100, require_complete=True
        )
    assert not invoke.calls


def test_complete_review_covers_file_larger_than_default_cap(repo):
    (repo / "large.json").write_text("x" * 82000 + "\n", encoding="utf-8")
    _git(repo, "add", "large.json")
    _git(repo, "commit", "-q", "-m", "large fixture")
    invoke = _invoke_stub("NO FINDINGS")
    result = review.run_review(
        repo, base_ref="main", invoke_seat=invoke, diff_cap_chars=250000, require_complete=True
    )
    assert not result["manifest"]["omitted"]
    assert set(result["manifest"]["sent"]) == {"big.py", "small.py", "large.json"}
    assert "x" * 82000 in invoke.calls[0]["brief"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"claude_auth": "unknown"},
        {"claude_auth": "subscription", "seat": "codex"},
        {
            "claude_auth": "subscription",
            "seat": "claude",
            "invoke_seat": _invoke_stub("NO FINDINGS"),
        },
    ],
)
def test_invalid_subscription_dispatch_fails(repo, kwargs):
    with pytest.raises(review.ReviewTargetError):
        review.run_review(repo, base_ref="main", **kwargs)


def test_subscription_review_uses_verified_launcher(repo, monkeypatch):
    from attune.roundtable import subscription_review

    calls = []

    def launch(brief, **kwargs):
        calls.append(brief)
        return 0, "NO FINDINGS"

    monkeypatch.setattr(subscription_review, "invoke_subscription_review", launch)
    result = review.run_review(
        repo, base_ref="main", seat="claude", claude_auth="subscription", require_complete=True
    )
    assert result["claude_auth"] == "subscription"
    assert result["status"] == "clean" and len(calls) == 1


def test_default_claude_still_refuses_zero_api_budget(repo, monkeypatch):
    from attune.gates.session_ledger import SessionSpendCapError

    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
    monkeypatch.delenv("ATTUNE_SESSION_LEDGER", raising=False)
    with pytest.raises(SessionSpendCapError):
        review.run_review(repo, base_ref="main", seat="claude")


@pytest.mark.parametrize(
    ("env", "host", "seat"),
    [
        ({"CLAUDECODE": "1"}, "claude", "codex"),
        ({"CODEX_SESSION_ID": "s1"}, "codex", "claude"),
        ({"CODEX_SANDBOX": "1"}, "codex", "claude"),
        ({}, None, "codex"),
        ({"CLAUDECODE": "1", "CODEX_SESSION_ID": "s1"}, None, "codex"),
    ],
)
def test_default_seat_is_never_the_moderating_host(env, host, seat):
    """The whole point of the feature: the default seat is not the author.

    The ambiguous row (both markers) resolves to None deliberately — a
    nested launch cannot be told apart by environment, and guessing is
    what would put the authoring seat back on its own diff.
    """
    assert review.detect_moderator_host(env) == host
    resolved = review.resolve_default_seat(host)
    assert resolved == seat
    assert resolved != host


def test_claude_host_still_gets_the_open_1_ruled_default():
    """OPEN-1 (2026-07-28) ruled `codex`; that value is unchanged where it applied."""
    assert review.resolve_default_seat("claude") == review.DEFAULT_SEAT
    assert review.resolve_default_seat(None) == review.DEFAULT_SEAT


def test_codex_host_default_reaches_claude_not_itself(repo, monkeypatch):
    monkeypatch.setenv("CODEX_SESSION_ID", "s1")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    invoke = _invoke_stub("NO FINDINGS")
    result = review.run_review(repo, base_ref="main", invoke_seat=invoke)
    assert result["host"] == "codex"
    assert result["seat"] == "claude"
    assert result["self_review"] is False


def test_named_self_review_is_stamped_not_silently_passed_off(repo, monkeypatch):
    """Explicit seat==host stays allowed, but the result says so.

    A self-review that returned a clean verdict without this stamp is
    indistinguishable from a real cross-review in the ledger row.
    """
    monkeypatch.setenv("CODEX_SESSION_ID", "s1")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    invoke = _invoke_stub("NO FINDINGS")
    result = review.run_review(repo, base_ref="main", seat="codex", invoke_seat=invoke)
    assert result["host"] == "codex"
    assert result["self_review"] is True
    assert result["status"] == "clean"


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({"CODEX_SESSION_ID": "s1"}, "subscription"),
        ({"CLAUDECODE": "1"}, "api"),
        ({}, "api"),
        ({"CLAUDECODE": "1", "CODEX_SESSION_ID": "s1"}, "api"),
    ],
)
def test_auto_auth_picks_subscription_only_cross_host(env, expected):
    """`auto` is narrow: a KNOWN non-Claude host, nothing else.

    The unknown-host row is the load-bearing one — it keeps CI and a
    laptop on the same route, and keeps the zero-cap refusal that
    test_default_claude_still_refuses_zero_api_budget pins.
    """
    host = review.detect_moderator_host(env)
    assert (
        review._resolve_claude_auth("claude", host, "auto", review.default_invoke_seat) == expected
    )


def test_auto_auth_never_overrides_an_explicit_route():
    for explicit in ("api", "subscription"):
        assert (
            review._resolve_claude_auth("claude", "codex", explicit, review.default_invoke_seat)
            == explicit
        )


def test_auto_auth_ignores_non_claude_seats_and_injected_invokers():
    assert (
        review._resolve_claude_auth("codex", "claude", "auto", review.default_invoke_seat) == "api"
    )
    assert (
        review._resolve_claude_auth("claude", "codex", "auto", _invoke_stub("NO FINDINGS")) == "api"
    )


def test_codex_host_bare_run_reaches_the_subscription_launcher(repo, monkeypatch):
    """The end-to-end shape of the original ask: bare /cross-review in Codex."""
    from attune.roundtable import subscription_review

    monkeypatch.setenv("CODEX_SESSION_ID", "s1")
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.setenv("ATTUNE_SESSION_SPEND_CAP_USD", "0")
    monkeypatch.delenv("ATTUNE_SESSION_LEDGER", raising=False)
    calls = []
    monkeypatch.setattr(
        subscription_review,
        "invoke_subscription_review",
        lambda brief, **kw: (calls.append(brief), (0, "NO FINDINGS"))[1],
    )
    board = RecordingBoard()
    result = review.run_review(repo, base_ref="main", board=board)
    assert result["seat"] == "claude"
    assert result["claude_auth"] == "subscription"
    assert result["self_review"] is False
    assert result["status"] == "clean" and len(calls) == 1
    assert board.posts[0]["claude_auth"] == "subscription"
    assert board.posts[0]["host"] == "codex"
    assert board.posts[0]["self_review"] is False
    assert "claude_auth=subscription" in review.ledger_row(result)


@pytest.fixture(autouse=True)
def _neutral_host(monkeypatch):
    """Clear ambient host markers so a test's route never depends on the shell.

    Without this the suite is environment-dependent: run from a Codex
    session, `test_default_claude_still_refuses_zero_api_budget` resolves
    the subscription route and reaches the real launcher instead of
    raising (codex D11 lane, 2026-09-09). Tests that want a host set it
    explicitly.
    """
    for key in list(os.environ):
        if any(key.startswith(prefix) for _, prefix in review.HOST_ENV_PREFIXES):
            monkeypatch.delenv(key, raising=False)


def test_unknown_host_reports_unverified_independence_not_false(repo):
    """`self_review` is None when the host is unknown — never a bare False."""
    invoke = _invoke_stub("NO FINDINGS")
    result = review.run_review(repo, base_ref="main", invoke_seat=invoke)
    assert result["host"] is None
    assert result["self_review"] is None, "False would claim independence we cannot evidence"


def test_ambiguous_host_also_reports_unverified(repo, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CODEX_SESSION_ID", "s1")
    invoke = _invoke_stub("NO FINDINGS")
    result = review.run_review(repo, base_ref="main", invoke_seat=invoke)
    assert result["host"] is None and result["self_review"] is None


class TestLedgerCli:
    """``python -m attune.roundtable ledger`` (retro 2026-09-12 item 1)."""

    @staticmethod
    def _result(status: str = "findings", findings: int = 1) -> dict[str, Any]:
        return {
            "seat": "codex",
            "host": "claude",
            "self_review": False,
            "claude_auth": None,
            "status": status,
            "target": "branch vs merge-base abc1234 (origin/main)",
            "manifest": {"sent": ["a.py"], "omitted": [], "chars": 10},
            "findings": [{"file": "a.py", "line": 1, "severity": "low", "claim": "x"}] * findings,
        }

    def test_parses_the_last_line_behind_a_digest_line(self, tmp_path: Path) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(
            "2026-09-11 17:00:50 [info] cross_review board=posted findings=1\n"
            + json.dumps(self._result())
            + "\n",
            encoding="utf-8",
        )
        assert review.load_review_result(capture)["seat"] == "codex"

    @pytest.mark.parametrize("body", ["", "   \n", "not json\n", '{"seat": "codex"}\n'])
    def test_rejects_captures_without_a_result(self, tmp_path: Path, body: str) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(body, encoding="utf-8")
        with pytest.raises(ValueError):
            review.load_review_result(capture)

    def test_prints_and_appends_a_validated_row(self, tmp_path: Path, capsys) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(json.dumps(self._result()), encoding="utf-8")
        ledger = tmp_path / "receipts.md"
        ledger.write_text("| header |\n", encoding="utf-8")
        rc = review.ledger_cli(
            ["--result", str(capture), "--disposition", "1 real — fixed", "--append", str(ledger)]
        )
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert out.endswith("| 1 (findings) | 1 real — fixed |")
        assert ledger.read_text(encoding="utf-8") == "| header |\n" + out + "\n"

    def test_disposition_file_and_clean_default(self, tmp_path: Path, capsys) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(json.dumps(self._result(status="clean", findings=0)), encoding="utf-8")
        assert review.ledger_cli(["--result", str(capture)]) == 0
        assert "clean — no findings; complete manifest" in capsys.readouterr().out
        dfile = tmp_path / "d.txt"
        dfile.write_text("clean — triaged by hand\n", encoding="utf-8")
        assert review.ledger_cli(["--result", str(capture), "--disposition-file", str(dfile)]) == 0
        assert capsys.readouterr().out.strip().endswith("| clean — triaged by hand |")

    def test_gate_failing_disposition_exits_1_and_appends_nothing(
        self, tmp_path: Path, capsys
    ) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(json.dumps(self._result()), encoding="utf-8")
        ledger = tmp_path / "receipts.md"
        rc = review.ledger_cli(
            ["--result", str(capture), "--disposition", "5 real", "--append", str(ledger)]
        )
        assert rc == 1
        assert "exceeds the findings count" in capsys.readouterr().err
        assert not ledger.exists()

    def test_module_entry_point_round_trip(self, tmp_path: Path) -> None:
        capture = tmp_path / "review.json"
        capture.write_text(json.dumps(self._result()), encoding="utf-8")
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "attune.roundtable",
                "ledger",
                "--result",
                str(capture),
                "--disposition",
                "1 real — fixed",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert run.returncode == 0, run.stderr
        assert run.stdout.strip().endswith("| 1 real — fixed |")
        usage = subprocess.run(
            [sys.executable, "-m", "attune.roundtable"], capture_output=True, text=True, timeout=60
        )
        assert usage.returncode == 2 and "usage:" in usage.stderr
