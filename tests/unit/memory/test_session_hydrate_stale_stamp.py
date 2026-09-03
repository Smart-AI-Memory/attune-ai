"""Stale-suspect stamp on recalled project-state memories (probe-before-claim).

Chair ruling 2026-09-03 (guard-intervention report "The Prose Gap",
recorded in ~/.claude/memory/feedback_probe_before_claim.md): when the
hydration source repo (~/attune-ai main checkout) trails reality, the
SessionStart hydrate hook already prints a ``[hydrate] STALE SOURCE``
line — but recalled PROJECT-STATE memories (curated nodes and file
memories describing repo/spec/ruling state) still read as current. In
the audited session a stale "coverage floor still open" memory was
presented as fact after decisions.md D7/D8 had already ruled.

The fix under test: ``hydrate.py`` prefixes the ``description`` field of
project-state entries (curated ``node_type: project_context`` nodes and
file-corpus ``type: project`` memories) with a ``[STALE-SUSPECT: ...]``
marker at hydrate time. Because the marker rides in the description
field, every recall surface — ``FCALL recall_digest``, ``FT.SEARCH ...
RETURN description``, ``recall_related`` — shows it with no Lua or
client changes, so a session re-probes the tree (decisions.md, git log)
before presenting a recalled "open item" as current.

Scope note (matches test_session_hydrate_fail_open.py): the hook lives
in the personal attune-agent-memory checkout at ``~/.attune/memory/``,
not in this repo — these tests import the REAL ``hydrate.py`` where that
checkout exists and skip elsewhere (CI skips). Staleness detection is
exercised against throwaway git repos in ``tmp_path`` (the module's
``LESSONS_PATH`` anchor is monkeypatched), so no real checkout state and
no network are touched. Fail-open discipline: detection failure must
degrade to "fresh", never raise — hydration never blocks a session.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

HYDRATE_SCRIPT = Path.home() / ".attune" / "memory" / "hydrate.py"

pytestmark = pytest.mark.skipif(
    not HYDRATE_SCRIPT.exists(),
    reason="personal-infra hydrate hook not present on this machine "
    "(~/.attune/memory/hydrate.py — attune-agent-memory checkout)",
)


@pytest.fixture(scope="module")
def hydrate():
    """Import the real hydrate.py as a module (no Redis connection made)."""
    spec = importlib.util.spec_from_file_location("hydrate_under_test", HYDRATE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hydrate_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    full_env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "HOME": str(repo),  # isolate from user gitconfig (GPG signing etc.)
        **(env or {}),
    }
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env=full_env,
        timeout=30,
    )


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "source-repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "commit", "--allow-empty", "-q", "-m", "one")
    return repo


def _point_hydrate_at(monkeypatch: pytest.MonkeyPatch, hydrate, repo: Path) -> None:
    # _staleness_reasons derives the repo as LESSONS_PATH.parents[1]
    monkeypatch.setattr(hydrate, "LESSONS_PATH", repo / ".claude" / "lessons.md")


class TestStalenessReasons:
    def test_fresh_repo_yields_no_reasons(self, tmp_path, monkeypatch, hydrate):
        repo = _make_repo(tmp_path)
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        _point_hydrate_at(monkeypatch, hydrate, repo)
        assert hydrate._staleness_reasons() == []

    def test_behind_origin_main_is_reported(self, tmp_path, monkeypatch, hydrate):
        repo = _make_repo(tmp_path)
        _git(repo, "commit", "--allow-empty", "-q", "-m", "two")
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        # move the branch back one commit WITHOUT touching the worktree
        _git(repo, "update-ref", "refs/heads/main", "HEAD~1")
        _point_hydrate_at(monkeypatch, hydrate, repo)
        reasons = hydrate._staleness_reasons()
        assert reasons == ["1 commits behind last-fetched origin/main"]

    def test_old_head_is_reported(self, tmp_path, monkeypatch, hydrate):
        repo = tmp_path / "old-repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        old = {
            "GIT_AUTHOR_DATE": "2020-01-01T00:00:00",
            "GIT_COMMITTER_DATE": "2020-01-01T00:00:00",
        }
        _git(repo, "commit", "--allow-empty", "-q", "-m", "ancient", env=old)
        _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        _point_hydrate_at(monkeypatch, hydrate, repo)
        reasons = hydrate._staleness_reasons()
        assert len(reasons) == 1
        assert "days old" in reasons[0]

    def test_non_git_dir_degrades_to_fresh(self, tmp_path, monkeypatch, hydrate):
        """Fail-open: detection failure means 'fresh', never an exception."""
        plain = tmp_path / "not-a-repo"
        plain.mkdir()
        _point_hydrate_at(monkeypatch, hydrate, plain)
        assert hydrate._staleness_reasons() == []


class TestStaleMarker:
    def test_fresh_source_produces_no_marker(self, hydrate):
        assert hydrate._stale_marker([]) == ""

    def test_marker_names_reasons_and_reprobe_targets(self, hydrate):
        marker = hydrate._stale_marker(["3 commits behind last-fetched origin/main"])
        assert marker.startswith("[STALE-SUSPECT: ")
        assert "3 commits behind last-fetched origin/main" in marker
        # the stamp must tell the reader HOW to re-probe, not just warn
        assert "decisions.md" in marker
        assert "git log" in marker

    def test_marker_joins_multiple_reasons(self, hydrate):
        marker = hydrate._stale_marker(["HEAD is 12 days old", "3 commits behind"])
        assert "HEAD is 12 days old; 3 commits behind" in marker


class TestStamp:
    MARKER = "[STALE-SUSPECT: test] "

    @pytest.mark.parametrize("entry_type", ["project_context", "project"])
    def test_project_state_types_are_stamped(self, hydrate, entry_type):
        assert entry_type in hydrate.PROJECT_STATE_TYPES
        out = hydrate._stamp("coverage floor still open", entry_type, self.MARKER)
        assert out == self.MARKER + "coverage floor still open"

    @pytest.mark.parametrize(
        "entry_type",
        ["feedback", "user_context", "reference", "user", ""],
    )
    def test_non_project_state_types_pass_through(self, hydrate, entry_type):
        out = hydrate._stamp("prefers terse replies", entry_type, self.MARKER)
        assert out == "prefers terse replies"

    def test_no_marker_means_no_stamp_even_for_project_state(self, hydrate):
        out = hydrate._stamp("coverage floor still open", "project_context", "")
        assert out == "coverage floor still open"
