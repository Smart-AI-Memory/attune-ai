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
            repo, base_ref="main", board=RecordingBoard(), invoke_seat=_invoke_stub("NO FINDINGS")
        )
        assert review.ledger_row(result, disposition="real").endswith("| real |")
