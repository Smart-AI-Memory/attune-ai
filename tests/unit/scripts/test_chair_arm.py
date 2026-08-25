"""Tests for scripts/chair_arm.py — the CHAIR-ARMS paved path.

Covers the pure decision logic: governance-surface classification,
preflight blockers, arm-state evaluation, and the SHA-bound receipt
body. The gh-calling seams (fetch/label/comment) are exercised through
``main`` with a stubbed ``run_gh`` so no test touches the network.

Loads the script via importlib (matches the existing scripts-test
pattern).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "chair_arm.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_chair_arm", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_chair_arm"] = m
    spec.loader.exec_module(m)
    return m


def _view(**overrides) -> dict:
    """A green, armable PR view; override fields per test."""
    base = {
        "state": "OPEN",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature-branch",
        "headRefOid": "a" * 40,
        "mergeStateStatus": "BLOCKED",
        "labels": [],
        "autoMergeRequest": None,
        "title": "test PR",
        "url": "https://example.invalid/pr/1",
        "additions": 1,
        "deletions": 0,
        "files": [{"path": "src/attune/x.py"}],
        "isCrossRepository": False,
    }
    base.update(overrides)
    return base


class TestGovernancePaths:
    """Advisory CHAIR-ARMS surface classification."""

    def test_plain_source_paths_are_not_governance(self, mod):
        assert mod.governance_paths(["src/attune/utils/tokens.py"]) == []

    def test_exact_and_prefix_surfaces_hit(self, mod):
        paths = [
            ".claude/CLAUDE.md",
            ".claude/rules/attune/decision-routine.md",
            "tests/unit/gates/test_brand_drift.py",
            "scripts/project_collaboration_contract.py",
            "src/attune/workflows/ok.py",
        ]
        hits = mod.governance_paths(paths)
        assert "src/attune/workflows/ok.py" not in hits
        assert len(hits) == 4

    def test_spec_decisions_files_hit(self, mod):
        hits = mod.governance_paths(
            [
                "docs/specs/feature-lead-governance/decisions.md",
                "docs/specs/feature-lead-governance/tasks.md",
            ]
        )
        assert hits == ["docs/specs/feature-lead-governance/decisions.md"]

    def test_r5_ledger_hits(self, mod):
        assert mod.governance_paths(["docs/specs/cross-review/receipts.md"])

    def test_ratchet_allowlists_hit(self, mod):
        """Gate allowlists ARE enforcement surface.

        Origin: 2026-08-25 — #2301 removed a line from
        `.claude/gates/empathy-allowlist.txt` (a shrink-only ratchet)
        and chair_arm printed "no governance-class surfaces detected".
        Loosening a ratchet is precisely a CHAIR-ARMS-class act.
        """
        assert mod.governance_paths([".claude/gates/empathy-allowlist.txt"]) == [
            ".claude/gates/empathy-allowlist.txt"
        ]

    def test_agents_md_and_contract_projection_hit(self, mod):
        # codex finding 2026-07-30: these governance surfaces were
        # omitted from the map; a diff touching them reported clean.
        hits = mod.governance_paths(["AGENTS.md", "content/collaboration/contract.md"])
        assert len(hits) == 2


class TestFindBlockers:
    """Preflight gates that must refuse the arm."""

    def test_green_open_pr_has_no_blockers(self, mod):
        assert mod.find_blockers(_view(), ["src/attune/x.py"]) == []

    def test_closed_draft_fork_wrong_base_all_block(self, mod):
        view = _view(
            state="CLOSED",
            isDraft=True,
            baseRefName="develop",
            isCrossRepository=True,
        )
        blockers = mod.find_blockers(view, [])
        assert len(blockers) == 4

    def test_dirty_merge_state_blocks(self, mod):
        blockers = mod.find_blockers(_view(mergeStateStatus="DIRTY"), [])
        assert any("DIRTY" in b for b in blockers)

    def test_github_paths_block_with_carveout_reason(self, mod):
        blockers = mod.find_blockers(_view(), [".github/workflows/tests.yml"])
        assert any("carve-out" in b for b in blockers)


class TestEvaluateArmState:
    """Poll-loop classification of the PR view."""

    def test_merged_wins(self, mod):
        assert mod.evaluate_arm_state(_view(state="MERGED")) == "merged"

    def test_armed_requires_label_and_auto_merge_request(self, mod):
        view = _view(
            labels=[{"name": mod.LABEL}],
            autoMergeRequest={"enabledAt": "now"},
        )
        assert mod.evaluate_arm_state(view) == "armed"

    def test_armed_without_label_is_label_stripped(self, mod):
        # codex round-2 finding: lingering autoMergeRequest after a
        # half-failed guard disarm must not count as armed.
        view = _view(labels=[], autoMergeRequest={"enabledAt": "now"})
        assert mod.evaluate_arm_state(view) == "label-stripped"

    def test_label_stripped_detected(self, mod):
        assert mod.evaluate_arm_state(_view(labels=[])) == "label-stripped"

    def test_pending_while_labeled_and_unarmed(self, mod):
        view = _view(labels=[{"name": mod.LABEL}])
        assert mod.evaluate_arm_state(view) == "pending"


class TestReceiptBody:
    """SHA-bound read-receipt text."""

    def test_body_carries_sha_and_invalidation_rule(self, mod):
        sha = "b" * 40
        body = mod.receipt_body(sha)
        assert f"chair-armed at {sha}" in body
        assert "subsequent push invalidates" in body

    def test_body_asserts_this_run_not_label_history(self, mod):
        # codex round-3 wording finding: the receipt asserts the
        # chair's act via THIS run, not who applied the label.
        assert "ran" in mod.receipt_body("d" * 40)

    def test_merged_suffix(self, mod):
        assert "already green" in mod.receipt_body("c" * 40, merged=True)


class TestMainFlow:
    """End-to-end through main() with a stubbed gh seam."""

    def _stub_gh(self, mod, monkeypatch, view: dict, comments: str = ""):
        calls: list[list[str]] = []

        def fake_run_gh(args, repo=None):
            calls.append(args)
            if args[:2] == ["pr", "view"]:
                fields = args[args.index("--json") + 1].split(",")
                return json.dumps({k: view[k] for k in fields})
            if args[:2] == ["api", "user"]:
                return "the-chair\n"
            if args[0] == "api":
                return comments
            return ""

        monkeypatch.setattr(mod, "run_gh", fake_run_gh)
        return calls

    def test_blocked_pr_exits_1_without_labeling(self, mod, monkeypatch):
        view = _view(isDraft=True)
        calls = self._stub_gh(mod, monkeypatch, view)
        assert mod.main(["7"]) == 1
        assert not any(a[:2] == ["pr", "edit"] for a in calls)

    def test_dry_run_reads_only(self, mod, monkeypatch):
        view = _view()
        calls = self._stub_gh(mod, monkeypatch, view)
        assert mod.main(["7", "--dry-run"]) == 0
        assert not any(a[:2] == ["pr", "edit"] for a in calls)
        assert not any(a[:2] == ["pr", "comment"] for a in calls)

    def test_arm_verify_and_receipt(self, mod, monkeypatch):
        view = _view(labels=[{"name": mod.LABEL}])
        calls = self._stub_gh(mod, monkeypatch, view)

        def arm_after_label(args, repo=None):
            if args[:2] == ["pr", "edit"]:
                view["autoMergeRequest"] = {"enabledAt": "now"}
            return original(args, repo)

        original = mod.run_gh
        monkeypatch.setattr(mod, "run_gh", arm_after_label)
        assert mod.main(["7"]) == 0
        assert any(a[:2] == ["pr", "comment"] for a in calls)

    def test_label_stripped_exits_2(self, mod, monkeypatch):
        # Label applied, but the guard strips it before the first poll.
        view = _view(labels=[])
        self._stub_gh(mod, monkeypatch, view)
        assert mod.main(["7"]) == 2

    def test_armed_outside_flow_refuses_receipt(self, mod, monkeypatch):
        # codex finding 2026-07-30 [high]: armed with NO label = armed
        # outside the chair-arm flow; posting the receipt would launder
        # it. Must exit 2 and post nothing.
        view = _view(
            labels=[],
            autoMergeRequest={
                "enabledAt": "2026-07-30T00:00:00Z",
                "enabledBy": {"login": "someone-else"},
            },
        )
        calls = self._stub_gh(mod, monkeypatch, view)
        assert mod.main(["7"]) == 2
        assert not any(a[:2] == ["pr", "comment"] for a in calls)
        assert not any(a[:2] == ["pr", "edit"] for a in calls)

    def test_existing_receipt_not_duplicated(self, mod, monkeypatch):
        sha = "a" * 40
        view = _view(
            labels=[{"name": mod.LABEL}],
            autoMergeRequest={"enabledAt": "now"},
        )
        calls = self._stub_gh(mod, monkeypatch, view, comments=f"chair-armed at {sha}\n")
        assert mod.main(["7"]) == 0
        assert not any(a[:2] == ["pr", "comment"] for a in calls)
        # codex round-3 finding: dedup must be author-scoped, so an
        # arbitrary commenter cannot pre-seed the receipt string and
        # suppress the real one.
        comment_reads = [a for a in calls if a[0] == "api" and a[1] == "--paginate"]
        assert comment_reads and 'select(.user.login == "the-chair")' in comment_reads[0][-1]

    def test_head_move_during_verify_disarms(self, mod, monkeypatch):
        # codex round-3 finding: a head that moves during verify must
        # not stay armed on an unread diff — disarm + unlabel, exit 2.
        view = _view(
            labels=[{"name": mod.LABEL}],
            autoMergeRequest={"enabledAt": "now"},
        )
        calls: list[list[str]] = []

        def fake_run_gh(args, repo=None):
            calls.append(args)
            if args[:2] == ["pr", "view"]:
                fields = args[args.index("--json") + 1].split(",")
                data = {k: view[k] for k in fields}
                if "title" not in fields:  # the poll fetch — head moved
                    data["headRefOid"] = "e" * 40
                return json.dumps(data)
            if args[:2] == ["api", "user"]:
                return "the-chair\n"
            return ""

        monkeypatch.setattr(mod, "run_gh", fake_run_gh)
        assert mod.main(["7"]) == 2
        assert ["pr", "merge", "7", "--disable-auto"] in calls
        assert ["pr", "edit", "7", "--remove-label", mod.LABEL] in calls
        assert not any(a[:2] == ["pr", "comment"] for a in calls)


class TestLocalHeadBlocker:
    """The head you arm must be the head in your checkout.

    Origin: 2026-08-25 — a fix was committed to a sibling branch while
    the operator believed otherwise; ``git push origin <name>`` exited 0
    having pushed the unchanged ref, and the PR was armed on a head that
    did not contain the fix. Nothing in the preflight noticed.
    """

    def test_matching_local_head_does_not_block(self, mod):
        assert mod.find_blockers(_view(), [], "a" * 40, "match") == []

    def test_absent_local_ref_does_not_block(self, mod):
        """Arming from a clone without the branch stays possible."""
        assert mod.find_blockers(_view(), [], None, "absent") == []

    def test_unpushed_local_commits_block(self, mod):
        blockers = mod.find_blockers(_view(), [], "b" * 40, "ahead")
        assert len(blockers) == 1
        assert "does NOT" in blockers[0]
        assert "push, then re-run" in blockers[0]

    def test_stale_local_ref_blocks(self, mod):
        blockers = mod.find_blockers(_view(), [], "b" * 40, "behind")
        assert len(blockers) == 1
        assert "fetch, then re-run" in blockers[0]

    def test_diverged_blocks(self, mod):
        blockers = mod.find_blockers(_view(), [], "b" * 40, "diverged")
        assert len(blockers) == 1
        assert "diverged" in blockers[0]

    def test_blocker_names_both_shas_and_the_branch(self, mod):
        blockers = mod.find_blockers(_view(), [], "b" * 40, "ahead")
        assert "b" * 12 in blockers[0]
        assert "a" * 12 in blockers[0]
        assert "feature-branch" in blockers[0]


class TestLocalHeadStateAgainstRealGit:
    """``local_head_state`` is only useful if it reads git correctly."""

    @staticmethod
    def _git(repo, *args):
        import subprocess

        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    @pytest.fixture
    def repo(self, tmp_path, monkeypatch):
        import subprocess

        subprocess.run(["git", "init", "-q", "-b", "feature"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.invalid"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "f.txt").write_text("one")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "--no-gpg-sign", "-m", "first"], cwd=tmp_path, check=True
        )
        monkeypatch.chdir(tmp_path)
        return tmp_path

    def test_match_when_head_equals_pr_head(self, mod, repo):
        sha = self._git(repo, "rev-parse", "HEAD")
        assert mod.local_head_state("feature", sha) == (sha, "match")

    def test_absent_branch_reports_absent(self, mod, repo):
        assert mod.local_head_state("no-such-branch", "a" * 40) == (None, "absent")

    def test_local_commit_ahead_of_pr_head_is_ahead(self, mod, repo):
        import subprocess

        pr_head = self._git(repo, "rev-parse", "HEAD")
        (repo / "f.txt").write_text("two")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "commit", "-q", "--no-gpg-sign", "-m", "unpushed"], cwd=repo, check=True
        )

        local, relation = mod.local_head_state("feature", pr_head)
        assert relation == "ahead"
        assert local == self._git(repo, "rev-parse", "HEAD")

    def test_local_behind_pr_head_is_behind(self, mod, repo):
        """The PR head is a descendant the clone HAS — a stale local ref."""
        import subprocess

        (repo / "f.txt").write_text("two")
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "commit", "-q", "--no-gpg-sign", "-m", "newer"], cwd=repo, check=True
        )
        pr_head = self._git(repo, "rev-parse", "HEAD")
        subprocess.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=repo, check=True)

        local, relation = mod.local_head_state("feature", pr_head)
        assert relation == "behind"
        assert local == self._git(repo, "rev-parse", "HEAD")

    def test_unknown_remote_sha_reports_diverged_not_a_crash(self, mod, repo):
        """A head this clone never fetched must not be classified by guess."""
        local, relation = mod.local_head_state("feature", "0" * 40)
        assert relation == "diverged"
        assert local == self._git(repo, "rev-parse", "HEAD")
