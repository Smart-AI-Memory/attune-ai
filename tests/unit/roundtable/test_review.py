"""cross-review T1: target resolution, manifest math, lint matrix,
advisory invariant, board degrade, ledger rendering."""

from __future__ import annotations

import subprocess
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

    def test_ledger_row_placeholder_skips_validation(self, repo: Path) -> None:
        result = review.run_review(
            repo, base_ref="main", board=RecordingBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        assert review.ledger_row(result).endswith("| not-triaged |")


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
        assert review.ledger_row(result, disposition="real").endswith("| real |")


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
        assert result["scope_misses"] == []
        assert result["manifest"]["sent"] == ["small.py"]
        assert "big.py" not in result["manifest"]["omitted"]
        assert "SCOPED to 1 path(s)" in result["target"]
        # The seat's brief says so too — a scoped lane must not read as full.
        assert "SCOPED" in invoke.calls[0]["brief"]

    def test_scope_miss_is_recorded_not_silent(self, repo: Path) -> None:
        result = review.run_review(
            repo,
            base_ref="main",
            invoke_seat=_invoke_stub("NO FINDINGS"),
            paths=["small.py", "not/in/diff.py"],
        )
        assert result["scope_misses"] == ["not/in/diff.py"]
        assert result["scoped_to"] == ["small.py"]

    def test_unscoped_run_carries_no_scope_keys(self, repo: Path) -> None:
        result = review.run_review(repo, base_ref="main", invoke_seat=_invoke_stub("NO FINDINGS"))
        assert "scoped_to" not in result
        assert "scope_misses" not in result


class TestScopedReviewFailClosed:
    """Codex D11 findings on the O2 branch, pinned (2026-08-24)."""

    def test_all_miss_scope_raises_instead_of_clean(self, repo: Path) -> None:
        with pytest.raises(review.ReviewTargetError, match="matched no files"):
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
