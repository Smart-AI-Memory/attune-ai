"""Rotating-skeptic tests (round-table P3).

Real git repos and worktrees in tmp for the receipt re-runs — no
mocked git (the isolated-rerun seam is the point of the feature).
Seat invocations and the board are injected fakes: substrate
governance (different-model rule, one bounce, TAC-4 no-laundering,
R8 never-promotes) is asserted from the pass record + posted
messages.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from attune.roundtable.rotation import CANONICAL_SEATS
from attune.roundtable.skeptic import (
    MAX_RECEIPT_CMDS,
    SkepticError,
    build_skeptic_brief,
    main,
    parse_receipt_commands,
    parse_skeptic_verdict,
    rerun_receipts,
    run_skeptic_pass,
    skeptic_for,
    staged_closure_text,
    uncommitted_paths,
)


@pytest.fixture
def repo(tmp_path):
    """A tiny real git repo with one committed file."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    (repo / "hello.py").write_text('GREETING = "hello"\n')
    git("add", "hello.py")
    git("commit", "-q", "-m", "seed")
    return repo


class FakeBoard:
    """Collects posts; asserts R8 by never exposing a promote path."""

    def __init__(self):
        self.posts = []

    def post_message(self, thread, seat, kind, body, **fields):
        self.posts.append({"thread": thread, "seat": seat, "kind": kind, "body": body, **fields})
        return len(self.posts)


#: Fake recipes keyed so the invoker can tell which seat it plays.
RECIPES = tuple((seat, (f"seat-{seat}",)) for seat in CANONICAL_SEATS)


def invoker(replies):
    """Build an invoke_seat fake: seat name -> (code, reply)."""

    def invoke(recipe, brief):
        seat = recipe[0].removeprefix("seat-")
        return replies.get(seat, (1, ""))

    return invoke


CLOSURE = (
    "## 2026-07-21 — closure staged\n"
    "**Status:** shipped (2026-07-21)\n"
    f"RECEIPT-CMD: smoke :: {sys.executable} -c pass\n"
)

COUNTERSIGN = "VERDICT: COUNTERSIGN\nCITE: smoke :: python -c pass\n"
DISSENT = "VERDICT: DISSENT\nCITE: smoke :: python -c pass\nREASON: tail shows a failure\n"


class TestParseReceiptCommands:
    def test_basic_and_order(self):
        text = "RECEIPT-CMD: a :: echo one\nRECEIPT-CMD: b :: pytest -q tests\n"
        assert parse_receipt_commands(text) == [
            ("a", ["echo", "one"]),
            ("b", ["pytest", "-q", "tests"]),
        ]

    def test_staged_diff_plus_prefix(self):
        assert parse_receipt_commands("+RECEIPT-CMD: a :: echo hi\n") == [("a", ["echo", "hi"])]

    def test_no_declarations(self):
        assert parse_receipt_commands("## just prose\n") == []

    def test_duplicate_label_rejected(self):
        with pytest.raises(SkepticError, match="duplicate"):
            parse_receipt_commands("RECEIPT-CMD: a :: echo 1\nRECEIPT-CMD: a :: echo 2\n")

    def test_cap_enforced(self):
        lines = "\n".join(f"RECEIPT-CMD: c{i} :: echo {i}" for i in range(MAX_RECEIPT_CMDS + 1))
        with pytest.raises(SkepticError, match="capped"):
            parse_receipt_commands(lines)

    def test_unparseable_command_rejected(self):
        with pytest.raises(SkepticError, match="unparseable"):
            parse_receipt_commands('RECEIPT-CMD: a :: echo "unclosed\n')


class TestSkepticFor:
    def test_first_pick_skips_author(self):
        assert skeptic_for("claude", ()) == "antigravity"
        assert skeptic_for("antigravity", ()) == "claude"

    def test_pointer_advances_past_served(self):
        records = [{"actual_skeptic": "antigravity", "served": True}]
        assert skeptic_for("claude", records) == "codex"

    def test_unserved_never_advances(self):
        records = [{"actual_skeptic": "antigravity", "served": False}]
        assert skeptic_for("claude", records) == "antigravity"

    def test_advance_lands_on_author_then_skips(self):
        records = [{"actual_skeptic": "codex", "served": True}]
        # next in cycle is claude == author -> skip to antigravity
        assert skeptic_for("claude", records) == "antigravity"

    def test_unknown_author_rejected(self):
        with pytest.raises(SkepticError, match="unknown author"):
            skeptic_for("gpt", ())


class TestParseVerdict:
    def test_countersign(self):
        v = parse_skeptic_verdict(COUNTERSIGN)
        assert v.kind == "countersign"
        assert v.cite == "smoke :: python -c pass"

    def test_dissent_with_cite_and_reason(self):
        v = parse_skeptic_verdict(DISSENT)
        assert (v.kind, v.reason) == ("dissent", "tail shows a failure")

    def test_dissent_without_cite_is_malformed(self):
        v = parse_skeptic_verdict("VERDICT: DISSENT\nREASON: because\n")
        assert v.kind == "malformed"

    def test_countersign_without_cite_is_malformed(self):
        # an uncited countersign is the rubber stamp the ruling names
        v = parse_skeptic_verdict("VERDICT: COUNTERSIGN\n")
        assert v.kind == "malformed"

    def test_invented_cite_label_is_malformed(self):
        v = parse_skeptic_verdict(COUNTERSIGN, valid_labels=["other"])
        assert v.kind == "malformed"
        assert v.cite == "smoke :: python -c pass"  # kept for the chair

    def test_matching_cite_label_accepted(self):
        v = parse_skeptic_verdict(COUNTERSIGN, valid_labels=["smoke"])
        assert v.kind == "countersign"

    def test_garbage_is_malformed_never_laundered(self):
        assert parse_skeptic_verdict("LGTM, ship it!").kind == "malformed"


class TestRerunReceipts:
    def test_isolated_pass_and_fail_receipts(self, repo, tmp_path):
        checks = [
            ("ok", [sys.executable, "-c", "print('fine')"]),
            ("boom", [sys.executable, "-c", "raise SystemExit(3)"]),
        ]
        receipts = rerun_receipts(repo, checks, scratch_root=tmp_path / "scratch")
        assert [r.passed for r in receipts] == [True, False]
        assert receipts[1].exit_code == 3
        # isolation receipt: the scratch worktree is gone afterwards
        assert not list((tmp_path / "scratch").glob("rt-skeptic-*"))

    def test_worktree_sees_committed_tree(self, repo, tmp_path):
        checks = [
            (
                "read",
                [
                    sys.executable,
                    "-c",
                    "import pathlib;print(pathlib.Path('hello.py').read_text())",
                ],
            )
        ]
        receipts = rerun_receipts(repo, checks, scratch_root=tmp_path / "s2")
        assert receipts[0].passed and "hello" in receipts[0].tail


class TestStagedClosureText:
    def test_added_lines_only(self, repo):
        spec = repo / "docs" / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "decisions.md").write_text("# Decisions\n\nold line\n")
        subprocess.run(["git", "-C", str(repo), "add", "docs"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "spec"],
            check=True,
            capture_output=True,
        )
        (spec / "decisions.md").write_text(
            "# Decisions\n\nold line\n\n## closure\nRECEIPT-CMD: a :: echo hi\n"
        )
        text = staged_closure_text(repo, "docs/specs/demo")
        assert "RECEIPT-CMD: a :: echo hi" in text
        assert "old line" not in text

    def test_clean_tree_is_empty(self, repo):
        assert staged_closure_text(repo, "docs/specs/none") == ""

    def test_git_failure_raises_not_empty(self, tmp_path):
        # a failed git diff must never read as "nothing to review"
        with pytest.raises(SkepticError, match="git diff failed"):
            staged_closure_text(tmp_path / "not-a-repo", "docs/specs/x")


class TestUncommittedPaths:
    def test_clean_repo_is_empty(self, repo):
        assert uncommitted_paths(repo) == []

    def test_dirty_and_untracked_listed(self, repo):
        (repo / "hello.py").write_text('GREETING = "changed"\n')
        (repo / "new.py").write_text("x = 1\n")
        assert sorted(uncommitted_paths(repo)) == ["hello.py", "new.py"]

    def test_exclude_hides_the_closure_entry(self, repo):
        (repo / "hello.py").write_text('GREETING = "changed"\n')
        assert uncommitted_paths(repo, exclude=("hello.py",)) == []

    def test_git_failure_raises(self, tmp_path):
        with pytest.raises(SkepticError, match="git status failed"):
            uncommitted_paths(tmp_path / "not-a-repo")


class TestRunSkepticPass:
    def _run(self, repo, closure=CLOSURE, replies=None, records=(), author="claude"):
        board = FakeBoard()
        record = run_skeptic_pass(
            "demo-spec",
            closure,
            repo,
            author,
            board=board,
            invoke_seat=invoker(replies or {}),
            seat_recipes=RECIPES,
            prior_records=records,
            thread="t-demo",
        )
        return record, board

    def test_countersign_path(self, repo):
        record, board = self._run(repo, replies={"antigravity": (0, COUNTERSIGN)})
        assert record.outcome == "countersigned"
        assert record.skeptic == "antigravity"
        assert record.invocations == 1
        kinds = [p["kind"] for p in board.posts]
        assert kinds == ["question", "position", "synthesis"]

    def test_dissent_gets_one_author_bounce(self, repo):
        record, board = self._run(
            repo,
            replies={"antigravity": (0, DISSENT), "claude": (0, "I concede; will amend.")},
        )
        assert record.outcome == "dissent"
        assert record.bounce_reply == "I concede; will amend."
        assert record.invocations == 2
        bounce = [p for p in board.posts if p.get("bounce")]
        assert len(bounce) == 1 and bounce[0]["seat"] == "claude"

    def test_malformed_verdict_recorded_not_laundered(self, repo):
        record, _ = self._run(repo, replies={"antigravity": (0, "ship it")})
        assert record.outcome == "malformed-verdict"
        assert record.bounce_reply is None

    def test_absent_skeptic_falls_back_once(self, repo):
        record, board = self._run(repo, replies={"antigravity": (1, ""), "codex": (0, COUNTERSIGN)})
        assert record.skeptic == "codex"
        assert record.outcome == "countersigned"
        absents = [p for p in board.posts if p.get("absent")]
        assert len(absents) == 1

    def test_all_absent_is_chair_visible(self, repo):
        record, board = self._run(repo, replies={})
        assert record.outcome == "skeptic-absent"
        assert any(p["kind"] == "halt" for p in board.posts)

    def test_author_never_plays_skeptic(self, repo):
        # every seat would countersign; the author's recipe must only
        # ever be invoked for a bounce (never for the verdict)
        invoked = []

        def invoke(recipe, brief):
            invoked.append(recipe[0].removeprefix("seat-"))
            return (0, COUNTERSIGN)

        board = FakeBoard()
        record = run_skeptic_pass(
            "demo-spec",
            CLOSURE,
            repo,
            "claude",
            board=board,
            invoke_seat=invoke,
            seat_recipes=RECIPES,
            thread="t-demo",
        )
        assert record.skeptic != "claude"
        assert invoked == ["antigravity"]

    def test_rotation_records_shift_the_pick(self, repo):
        record, _ = self._run(
            repo,
            replies={"codex": (0, COUNTERSIGN)},
            records=[{"actual_skeptic": "antigravity", "served": True}],
        )
        assert record.skeptic == "codex"

    def test_no_receipts_declared(self, repo):
        record, board = self._run(repo, closure="## closure with no receipts\n")
        assert record.outcome == "no-receipts"
        assert record.invocations == 0
        assert board.posts[0]["kind"] == "halt"

    def test_bad_declaration_refused(self, repo):
        closure = "RECEIPT-CMD: a :: echo 1\nRECEIPT-CMD: a :: echo 2\n"
        record, board = self._run(repo, closure=closure)
        assert record.outcome == "bad-declaration"
        assert board.posts[0]["kind"] == "halt"

    def test_invented_cite_recorded_as_malformed(self, repo):
        # the executed receipt label is "smoke"; the seat cites a
        # check that never ran — never recorded as a valid verdict
        invented = "VERDICT: COUNTERSIGN\nCITE: full-suite :: pytest -q\n"
        record, _ = self._run(repo, replies={"antigravity": (0, invented)})
        assert record.outcome == "malformed-verdict"

    def test_isolation_gap_surfaced_when_spec_dir_given(self, repo):
        (repo / "drifting.py").write_text("x = 1\n")
        board = FakeBoard()
        record = run_skeptic_pass(
            "demo-spec",
            CLOSURE,
            repo,
            "claude",
            board=board,
            invoke_seat=invoker({"antigravity": (0, COUNTERSIGN)}),
            seat_recipes=RECIPES,
            thread="t-demo",
            spec_dir="docs/specs/demo-spec",
        )
        assert record.isolation_gap == ["drifting.py"]
        brief = board.posts[0]["body"]
        assert "Isolation note" in brief and "drifting.py" in brief
        digest = [p for p in board.posts if p["kind"] == "synthesis"][0]
        assert "isolation gap: 1 uncommitted path(s)" in digest["body"]

    def test_no_spec_dir_means_no_gap_scan(self, repo):
        (repo / "drifting.py").write_text("x = 1\n")
        record, board = self._run(repo, replies={"antigravity": (0, COUNTERSIGN)})
        assert record.isolation_gap == []
        assert "Isolation note" not in board.posts[0]["body"]

    def test_never_promotes_and_never_flips_status(self, repo):
        _, board = self._run(repo, replies={"antigravity": (0, COUNTERSIGN)})
        assert all(p["kind"] != "ruling" for p in board.posts)
        digest = [p for p in board.posts if p["kind"] == "synthesis"][0]
        assert "never flips the spec status" in digest["body"]


class TestMain:
    """CLI seam — path validation and concise failure surfacing."""

    def _stage_closure(self, repo, closure_tail):
        spec = repo / "docs" / "specs" / "demo"
        spec.mkdir(parents=True)
        (spec / "decisions.md").write_text("# Decisions\n")
        subprocess.run(["git", "-C", str(repo), "add", "docs"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "spec"],
            check=True,
            capture_output=True,
        )
        (spec / "decisions.md").write_text("# Decisions\n\n## closure\n" + closure_tail)

    def test_traversal_spec_dir_rejected(self, repo, capsys):
        code = main(["../evil", "--author", "claude", "--repo", str(repo)])
        assert code == 2
        assert "invalid spec_dir" in capsys.readouterr().out

    def test_absolute_spec_dir_rejected(self, repo, capsys):
        code = main([str(repo / "docs"), "--author", "claude", "--repo", str(repo)])
        assert code == 2
        assert "invalid spec_dir" in capsys.readouterr().out

    def test_git_failure_surfaces_concise(self, tmp_path, capsys):
        code = main(["docs/specs/x", "--author", "claude", "--repo", str(tmp_path / "nope")])
        assert code == 2
        assert "git diff failed" in capsys.readouterr().out

    def test_nothing_staged_exits_1(self, repo, capsys):
        code = main(["docs/specs/none", "--author", "claude", "--repo", str(repo)])
        assert code == 1
        assert "nothing to review" in capsys.readouterr().out

    def test_dry_run_prints_brief_with_gap(self, repo, capsys):
        self._stage_closure(repo, f"RECEIPT-CMD: smoke :: {sys.executable} -c pass\n")
        (repo / "drifting.py").write_text("x = 1\n")
        code = main(["docs/specs/demo", "--author", "claude", "--repo", str(repo), "--dry-run"])
        out = capsys.readouterr().out
        assert code == 0
        assert "Re-run receipts" in out
        assert "drifting.py" in out  # isolation gap named in the brief

    def test_dry_run_bad_declaration_exits_2(self, repo, capsys):
        self._stage_closure(repo, "RECEIPT-CMD: a :: echo 1\nRECEIPT-CMD: a :: echo 2\n")
        code = main(["docs/specs/demo", "--author", "claude", "--repo", str(repo), "--dry-run"])
        assert code == 2
        assert "refusing this declaration" in capsys.readouterr().out

    def test_dry_run_no_receipt_lines_exits_1(self, repo, capsys):
        self._stage_closure(repo, "prose only, no receipts\n")
        code = main(["docs/specs/demo", "--author", "claude", "--repo", str(repo), "--dry-run"])
        assert code == 1
        assert "no RECEIPT-CMD declarations" in capsys.readouterr().out


class TestBrief:
    def test_brief_carries_evidence_and_calibration(self, repo, tmp_path):
        receipts = rerun_receipts(
            repo,
            [("smoke", [sys.executable, "-c", "print('receipt-tail-marker')"])],
            scratch_root=tmp_path / "s3",
        )
        brief = build_skeptic_brief("demo", CLOSURE, receipts)
        assert "receipt-tail-marker" in brief
        assert "rubber-stamp" in brief
        assert "VERDICT: DISSENT" in brief
