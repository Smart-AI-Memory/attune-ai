"""Tests for the ref-triggered queue-jump (memory-status-integrity P2 task 7).

All external probes go through an injectable ``runner`` — no real git or
gh is ever invoked, and every failure path must FAIL OPEN (no flag), per
ruling D7.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from attune.memory.curated_audit import load_memory
from attune.memory.ref_triggers import (
    MAX_REFS_PER_MEMORY,
    check_ref,
    extract_refs,
    queue_jump_reasons,
)


def _completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestExtractRefs:
    def test_extracts_all_four_kinds(self) -> None:
        text = (
            "depends on pr:123 and issue:45; the fix is in "
            "file:src/attune/x.py at sha:abc1234def"
        )
        refs = extract_refs(text)
        assert ("pr", "123") in refs
        assert ("issue", "45") in refs
        assert ("file", "src/attune/x.py") in refs
        assert ("sha", "abc1234def") in refs

    def test_bare_hash_refs_are_deliberately_ignored(self) -> None:
        """Half the corpus cites merged PRs as provenance ('shipped #1979')
        — without state-at-write those would all false-fire."""
        assert extract_refs("shipped in #1979 and #2004") == []

    def test_caps_and_dedupes(self) -> None:
        text = " ".join(f"pr:{n}" for n in range(20)) + " pr:0"
        refs = extract_refs(text)
        assert len(refs) == MAX_REFS_PER_MEMORY
        assert len(set(refs)) == len(refs)

    def test_cap_respects_global_first_appearance_order(self) -> None:
        """Codex D11 finding: kind-grouped extraction let the cap discard an
        EARLIER dependency in favour of later refs of another kind."""
        text = "sha:abc1234 file:a.py pr:1 pr:2 pr:3 pr:4 pr:5"
        refs = extract_refs(text)
        assert refs[0] == ("sha", "abc1234")
        assert refs[1] == ("file", "a.py")
        assert len(refs) == MAX_REFS_PER_MEMORY

    def test_tilde_paths_are_not_recognized_as_file_refs(self) -> None:
        """file: refs are repo-relative by definition — a home-relative ref
        would falsely report missing when resolved under repo_root."""
        assert extract_refs("see file:~/notes/x.md") == []


class TestCheckRef:
    def test_file_missing_triggers(self, tmp_path: Path) -> None:
        assert check_ref("file", "gone.py", repo_root=tmp_path) == "file:gone.py no longer exists"

    def test_file_present_holds(self, tmp_path: Path) -> None:
        (tmp_path / "here.py").write_text("x = 1\n", encoding="utf-8")
        assert check_ref("file", "here.py", repo_root=tmp_path) is None

    def test_file_escaping_root_is_unverifiable_not_a_trigger(self, tmp_path: Path) -> None:
        assert check_ref("file", "../../etc/passwd", repo_root=tmp_path) is None

    def test_sibling_dir_with_root_prefix_does_not_bypass_containment(self, tmp_path: Path) -> None:
        """Codex D11 finding: string-prefix containment let `/repo-evil`
        pass for root `/repo`. Path-based containment must refuse it."""
        root = tmp_path / "repo"
        root.mkdir()
        sibling = tmp_path / "repo-evil"
        sibling.mkdir()
        (sibling / "x.py").write_text("x = 1\n", encoding="utf-8")
        assert check_ref("file", "../repo-evil/x.py", repo_root=root) is None

    def test_sha_unknown_triggers(self, tmp_path: Path) -> None:
        runner = lambda *a, **k: _completed(returncode=1)  # noqa: E731
        assert (
            check_ref("sha", "abc1234", repo_root=tmp_path, runner=runner)
            == "sha:abc1234 not in local git"
        )

    def test_sha_known_holds(self, tmp_path: Path) -> None:
        runner = lambda *a, **k: _completed(returncode=0)  # noqa: E731
        assert check_ref("sha", "abc1234", repo_root=tmp_path, runner=runner) is None

    def test_sha_git_missing_fails_open(self, tmp_path: Path) -> None:
        def _no_git(*a, **k):
            raise FileNotFoundError("git not installed")

        assert check_ref("sha", "abc1234", repo_root=tmp_path, runner=_no_git) is None

    def test_pr_not_open_triggers(self) -> None:
        runner = lambda *a, **k: _completed(stdout='{"state": "MERGED"}')  # noqa: E731
        assert check_ref("pr", "123", runner=runner) == "pr:123 is MERGED"

    def test_pr_open_holds(self) -> None:
        runner = lambda *a, **k: _completed(stdout='{"state": "OPEN"}')  # noqa: E731
        assert check_ref("pr", "123", runner=runner) is None

    def test_gh_error_fails_open(self) -> None:
        runner = lambda *a, **k: _completed(returncode=1)  # noqa: E731
        assert check_ref("pr", "123", runner=runner) is None
        assert check_ref("issue", "45", runner=runner) is None

    def test_gh_missing_fails_open(self) -> None:
        def _no_gh(*a, **k):
            raise FileNotFoundError("gh not installed")

        assert check_ref("pr", "123", runner=_no_gh) is None

    def test_malformed_gh_json_fails_open(self) -> None:
        runner = lambda *a, **k: _completed(stdout="not json")  # noqa: E731
        assert check_ref("pr", "123", runner=runner) is None

    def test_unknown_kind_holds(self) -> None:
        assert check_ref("branch", "main") is None


class TestQueueJumpReasons:
    def _mem(self, tmp_path: Path, stem: str, mem_type: str, body: str):
        path = tmp_path / f"{stem}.md"
        path.write_text(
            "---\n"
            f"name: {stem}\n"
            "description: a claim\n"
            "metadata:\n"
            f"  type: {mem_type}\n"
            f"---\n\n{body}\n",
            encoding="utf-8",
        )
        return load_memory(path)

    def test_project_memory_with_triggered_ref(self, tmp_path: Path) -> None:
        mem = self._mem(tmp_path, "project_p", "project", "waiting on pr:77")
        runner = lambda *a, **k: _completed(stdout='{"state": "CLOSED"}')  # noqa: E731
        assert queue_jump_reasons(mem, runner=runner) == ["pr:77 is CLOSED"]

    def test_non_project_type_never_probes(self, tmp_path: Path) -> None:
        mem = self._mem(tmp_path, "feedback_f", "feedback", "waiting on pr:77")

        def _forbidden(*a, **k):
            raise AssertionError("non-project memories must not probe")

        assert queue_jump_reasons(mem, runner=_forbidden) == []

    def test_unreadable_body_still_checks_description_refs(self, tmp_path: Path) -> None:
        """A vanished file's refs still resolve from the parsed description."""
        mem = self._mem(tmp_path, "project_gone", "project", "body")
        object.__setattr__(mem, "description", "depends on pr:88")
        mem.path.unlink()
        runner = lambda *a, **k: _completed(stdout='{"state": "MERGED"}')  # noqa: E731
        assert queue_jump_reasons(mem, runner=runner) == ["pr:88 is MERGED"]

    def test_no_refs_no_probes(self, tmp_path: Path) -> None:
        mem = self._mem(tmp_path, "project_plain", "project", "mentions #123 only")

        def _forbidden(*a, **k):
            raise AssertionError("no explicit refs -> no probes")

        assert queue_jump_reasons(mem, runner=_forbidden) == []
