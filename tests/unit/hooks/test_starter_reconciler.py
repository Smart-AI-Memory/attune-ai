"""Tests for starter_reconciler.py SessionStart hook.

Covers:

- Thread extraction (PR numbers, branches, versions) with caps + dedupe
- Package-name parse from pyproject.toml (regex, no tomllib dep)
- Per-thread check functions (gh / git / PyPI) with subprocess stubbed
- reconcile() aggregates concurrent checks and degrades to "unverified"
- format_banner() rendering, including the empty-package and no-op cases
- main() no-ops cleanly on missing/empty files and never raises
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "attune"
    / "hooks"
    / "scripts"
    / "starter_reconciler.py"
)


@pytest.fixture(scope="module")
def hook_module():
    spec = importlib.util.spec_from_file_location("_starter_reconciler", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_starter_reconciler"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Thread extraction -----------------------------------------------


class TestExtractThreads:
    def test_extracts_prs_branches_versions(self, hook_module):
        text = (
            "Merged PR #1118 and #1121; branch claude/foo-bar was deleted.\n"
            "Shipped 9.0.0 to PyPI (was 8.5.0)."
        )
        prs, branches, versions = hook_module.extract_threads(text)
        assert prs == [1118, 1121]
        assert branches == ["claude/foo-bar"]
        assert versions == ["9.0.0", "8.5.0"]

    def test_markdown_heading_not_matched_as_pr(self, hook_module):
        # "# Heading" has a space after '#', so it is not a PR ref.
        prs, _, _ = hook_module.extract_threads("# Status\n## Section 9\n")
        assert prs == []

    def test_dedupe_preserves_order(self, hook_module):
        prs, _, versions = hook_module.extract_threads("#5 #5 #3 1.0.0 1.0.0")
        assert prs == [5, 3]
        assert versions == ["1.0.0"]

    def test_pr_and_branch_caps(self, hook_module):
        text = " ".join(f"#{n}" for n in range(100, 120))
        text += " " + " ".join(f"fix/b{n}" for n in range(20))
        prs, branches, _ = hook_module.extract_threads(text)
        assert len(prs) == hook_module.MAX_PRS
        assert len(branches) == hook_module.MAX_BRANCHES

    def test_doc_paths_not_matched_as_branches(self, hook_module):
        # 'docs/' and 'chore/' are deliberately excluded to avoid
        # matching doc paths like docs/specs/usage-signals.
        _, branches, _ = hook_module.extract_threads(
            "see docs/specs/usage-signals/ and chore/cleanup/notes"
        )
        assert branches == []


# --- Package name parse ----------------------------------------------


class TestPackageName:
    def test_reads_name_from_pyproject(self, hook_module, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "my-pkg"\nversion = "1.0.0"\n', encoding="utf-8"
        )
        assert hook_module._package_name(tmp_path) == "my-pkg"

    def test_none_when_no_pyproject(self, hook_module, tmp_path):
        assert hook_module._package_name(tmp_path) is None

    def test_none_when_no_name_field(self, hook_module, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        assert hook_module._package_name(tmp_path) is None

    def test_none_when_repo_root_none(self, hook_module):
        assert hook_module._package_name(None) is None


# --- Per-thread checks (subprocess / urllib stubbed) -----------------


class _FakeProc:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


class TestCheckPr:
    def test_returns_state_uppercased(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: _FakeProc("merged\n", 0))
        assert hook_module.check_pr(1118, None) == "MERGED"

    def test_unverified_on_nonzero(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: _FakeProc("", 1))
        assert hook_module.check_pr(1, None) == "unverified"

    def test_unverified_when_run_none(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)
        assert hook_module.check_pr(1, None) == "unverified"


class TestCheckBranch:
    def test_exists_when_ls_remote_has_output(self, hook_module, monkeypatch):
        monkeypatch.setattr(
            hook_module, "_run", lambda *a, **k: _FakeProc("abc123\trefs/heads/x", 0)
        )
        assert hook_module.check_branch("x", None) == "exists"

    def test_gone_when_ls_remote_empty(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: _FakeProc("", 0))
        assert hook_module.check_branch("x", None) == "gone"

    def test_unverified_when_run_none(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)
        assert hook_module.check_branch("x", None) == "unverified"


class TestRun:
    def test_run_returns_none_on_timeout(self, hook_module, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=1)

        monkeypatch.setattr(subprocess, "run", boom)
        assert hook_module._run(["git", "status"], None) is None

    def test_run_returns_none_on_oserror(self, hook_module, monkeypatch):
        def boom(*a, **k):
            raise OSError("no such binary")

        monkeypatch.setattr(subprocess, "run", boom)
        assert hook_module._run(["nope"], None) is None


class TestPypiLatest:
    def test_returns_none_on_error(self, hook_module, monkeypatch):
        def boom(*a, **k):
            raise OSError("offline")

        monkeypatch.setattr(hook_module.urllib.request, "urlopen", boom)
        assert hook_module.pypi_latest("attune-ai") is None


# --- reconcile() aggregation -----------------------------------------


class TestReconcile:
    def test_aggregates_all_checks(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        monkeypatch.setattr(hook_module, "check_branch", lambda b, c: "gone")
        monkeypatch.setattr(hook_module, "pypi_latest", lambda p: "9.0.0")
        # Keep the widening's git call hermetic.
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [])
        text = "PR #1118 on branch claude/foo shipped 9.0.0"
        results = hook_module.reconcile(text, "attune-ai", None)
        assert results["prs"] == {1118: "MERGED"}
        assert results["branches"] == {"claude/foo": "gone"}
        assert results["pypi"] == "9.0.0"

    def test_no_network_when_nothing_to_check(self, hook_module, monkeypatch):
        called = {"n": 0}

        def tracker(*a, **k):
            called["n"] += 1
            return "x"

        monkeypatch.setattr(hook_module, "check_pr", tracker)
        monkeypatch.setattr(hook_module, "check_branch", tracker)
        monkeypatch.setattr(hook_module, "pypi_latest", tracker)
        results = hook_module.reconcile("no threads here", None, None)
        assert called["n"] == 0
        assert results["prs"] == {} and results["branches"] == {}
        assert results["pypi"] is None

    def test_check_exception_does_not_sink_others(self, hook_module, monkeypatch):
        def boom(n, c):
            raise RuntimeError("gh exploded")

        monkeypatch.setattr(hook_module, "check_pr", boom)
        monkeypatch.setattr(hook_module, "pypi_latest", lambda p: "1.2.3")
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [])
        results = hook_module.reconcile("#42 v1.2.3", "pkg", None)
        # PR stays at its "unverified" seed; PyPI still resolves.
        assert results["prs"][42] == "unverified"
        assert results["pypi"] == "1.2.3"


# --- release_state_headline() -----------------------------------------


class TestReleaseStateHeadline:
    def _seed(self, home, project, body):
        d = home / ".claude" / "projects" / project / "memory"
        d.mkdir(parents=True)
        (d / "release_state.md").write_text(body, encoding="utf-8")

    def test_reads_headline_version(self, hook_module, tmp_path):
        self._seed(tmp_path, "-Users-x-attune-ai", "**16.0.0 IS PUBLISHED** attune-ai wheel")
        assert hook_module.release_state_headline("attune-ai", home=tmp_path) == "16.0.0"

    def test_none_when_pkg_absent_from_file(self, hook_module, tmp_path):
        self._seed(tmp_path, "-Users-x-other", "**2.0.0 IS PUBLISHED** other-pkg")
        assert hook_module.release_state_headline("attune-ai", home=tmp_path) is None

    def test_none_when_no_memory_exists(self, hook_module, tmp_path):
        assert hook_module.release_state_headline("attune-ai", home=tmp_path) is None

    def test_none_for_empty_pkg(self, hook_module, tmp_path):
        assert hook_module.release_state_headline("", home=tmp_path) is None

    def test_newest_file_wins(self, hook_module, tmp_path):
        import os

        self._seed(tmp_path, "-Users-x-a", "**15.0.0 IS PUBLISHED** attune-ai")
        self._seed(tmp_path, "-Users-x-b", "**16.0.0 IS PUBLISHED** attune-ai")
        old = tmp_path / ".claude/projects/-Users-x-a/memory/release_state.md"
        os.utime(old, (1, 1))
        assert hook_module.release_state_headline("attune-ai", home=tmp_path) == "16.0.0"

    def test_unreadable_file_degrades(self, hook_module, tmp_path, monkeypatch):
        self._seed(tmp_path, "-Users-x-attune-ai", "**16.0.0 IS PUBLISHED** attune-ai")
        monkeypatch.setattr(
            hook_module.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(OSError("nope"))
        )
        assert hook_module.release_state_headline("attune-ai", home=tmp_path) is None


# --- format_banner() --------------------------------------------------


class TestFormatBanner:
    def test_none_when_empty(self, hook_module, tmp_path):
        results = {"prs": {}, "branches": {}, "pypi": None, "versions": []}
        assert hook_module.format_banner(results, "global", tmp_path / "s.md") is None

    def test_renders_all_sections(self, hook_module, tmp_path):
        results = {
            "prs": {1118: "MERGED"},
            "branches": {"claude/foo": "gone"},
            "pypi": "9.0.0",
            "versions": ["9.0.0", "8.5.0"],
            "pkg": "attune-ai",
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "[starter-reconcile:global]" in out
        assert "#1118 MERGED" in out
        assert "claude/foo gone" in out
        assert "PyPI attune-ai latest=9.0.0" in out
        assert "starter mentions: 9.0.0, 8.5.0" in out

    def test_release_state_drift_warns(self, hook_module, tmp_path):
        results = {
            "prs": {},
            "branches": {},
            "pypi": "16.0.0",
            "versions": [],
            "pkg": "attune-ai",
            "release_state": "14.1.0",
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "release_state memory headlines 14.1.0" in out
        assert "latest=16.0.0" in out

    def test_release_state_in_sync_is_silent(self, hook_module, tmp_path):
        results = {
            "prs": {},
            "branches": {},
            "pypi": "16.0.0",
            "versions": [],
            "pkg": "attune-ai",
            "release_state": "16.0.0",
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "memory headlines" not in out

    def test_empty_package_has_no_double_space(self, hook_module, tmp_path):
        results = {
            "prs": {},
            "branches": {},
            "pypi": "1.0.0",
            "versions": [],
            "pkg": "",
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "PyPI  latest" not in out
        assert "PyPI latest=1.0.0" in out


# --- main() lifecycle -------------------------------------------------


class TestMain:
    def test_missing_files_no_output(self, hook_module, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(hook_module, "STARTER_PATH", tmp_path / "nope.md")
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
        assert hook_module.main() == 0
        assert capsys.readouterr().out == ""

    def test_empty_file_no_output(self, hook_module, tmp_path, monkeypatch, capsys):
        starter = tmp_path / "starter.md"
        starter.write_text("", encoding="utf-8")
        monkeypatch.setattr(hook_module, "STARTER_PATH", starter)
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
        assert hook_module.main() == 0
        assert capsys.readouterr().out == ""

    def test_emits_banner_for_global(self, hook_module, tmp_path, monkeypatch, capsys):
        starter = tmp_path / "starter.md"
        starter.write_text("Merged PR #1118.\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "STARTER_PATH", starter)
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-reconcile:global]" in out
        assert "#1118 MERGED" in out

    def test_emit_swallows_oserror(self, hook_module, monkeypatch):
        class _Boom:
            def is_file(self):
                raise OSError("vanished")

        assert hook_module._reconcile_and_emit(_Boom(), "global", None) is False

    def test_emits_banner_for_project(self, hook_module, tmp_path, monkeypatch, capsys):
        proj = tmp_path / "proj_starter.md"
        proj.write_text("Merged PR #42.\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: proj)
        # Absent global file → the global emit no-ops.
        monkeypatch.setattr(hook_module, "STARTER_PATH", tmp_path / "absent_global.md")
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-reconcile:project]" in out
        assert "#42 MERGED" in out

    def test_global_equal_to_project_skips_global_emit(
        self, hook_module, tmp_path, monkeypatch, capsys
    ):
        # When the global STARTER_PATH IS the project file, the global
        # emit is skipped (no double banner).
        proj = tmp_path / "proj.md"
        proj.write_text("PR #7 merged.\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "_find_project_starter", lambda *a, **k: proj)
        monkeypatch.setattr(hook_module, "STARTER_PATH", proj)
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        hook_module.main()
        out = capsys.readouterr().out
        assert "[starter-reconcile:project]" in out
        assert "[starter-reconcile:global]" not in out


# --- helper coverage: find/repo-root, pypi success, empty emit --------


class TestFindProjectStarter:
    """Cover _find_project_starter (the walk + default-cwd branch)."""

    def _make_repo(self, tmp_path, with_starter):
        (tmp_path / ".git").mkdir()
        if with_starter is not None:
            d = tmp_path / ".attune"
            d.mkdir()
            (d / "next_session_starter.md").write_text(with_starter, encoding="utf-8")
        return tmp_path

    def test_finds_starter_at_git_toplevel(self, hook_module, tmp_path):
        repo = self._make_repo(tmp_path, "handoff")
        nested = repo / "src" / "deep"
        nested.mkdir(parents=True)
        found = hook_module._find_project_starter(start=nested)
        assert found == repo / ".attune" / "next_session_starter.md"

    def test_none_when_no_repo(self, hook_module, tmp_path):
        assert hook_module._find_project_starter(start=tmp_path) is None

    def test_none_when_repo_but_no_starter(self, hook_module, tmp_path):
        repo = self._make_repo(tmp_path, None)
        assert hook_module._find_project_starter(start=repo) is None

    def test_default_start_uses_cwd(self, hook_module, tmp_path, monkeypatch):
        repo = self._make_repo(tmp_path, "# cwd handoff\n")
        monkeypatch.chdir(repo)
        found = hook_module._find_project_starter()  # no start= → cwd
        assert found == repo / ".attune" / "next_session_starter.md"


class TestRepoRoot:
    """Cover _repo_root (found, not-found, default-cwd)."""

    def test_finds_git_toplevel(self, hook_module, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        assert hook_module._repo_root(start=nested) == tmp_path

    def test_none_when_no_repo(self, hook_module, tmp_path):
        assert hook_module._repo_root(start=tmp_path) is None

    def test_default_start_uses_cwd(self, hook_module, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        assert hook_module._repo_root() == tmp_path


class TestPypiLatestSuccess:
    """Cover pypi_latest success path (json.load → version)."""

    def test_returns_version_from_json(self, hook_module, monkeypatch):
        import io

        payload = b'{"info": {"version": "9.0.0"}}'

        class _FakeResp:
            def __enter__(self):
                return io.BytesIO(payload)

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(hook_module.urllib.request, "urlopen", lambda *a, **k: _FakeResp())
        assert hook_module.pypi_latest("attune-ai") == "9.0.0"


class TestReconcileAndEmitNoThreads:
    """Cover _reconcile_and_emit's None-banner return (no threads, no pkg)."""

    def test_returns_false_and_silent(self, hook_module, tmp_path, capsys):
        starter = tmp_path / "s.md"
        starter.write_text("just prose, nothing to reconcile here\n", encoding="utf-8")
        # repo_root=None → pkg=None → no PyPI lookup → empty banner → False.
        assert hook_module._reconcile_and_emit(starter, "global", None) is False
        assert capsys.readouterr().out == ""


# --- widening: newer-merges-on-main staleness -------------------------


class TestMergedPrsOnMain:
    def test_parses_pr_markers_newest_first(self, hook_module, monkeypatch):
        log = (
            "feat(x): a (#1136)\n"
            "fix(y): b (#1135)\n"
            "chore: no marker here\n"
            "feat(z): c (#1133)\n"
        )
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: _FakeProc(log, 0))
        assert hook_module.merged_prs_on_main(None) == [1136, 1135, 1133]

    def test_empty_on_git_error(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: _FakeProc("", 1))
        assert hook_module.merged_prs_on_main(None) == []

    def test_empty_when_run_none(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)
        assert hook_module.merged_prs_on_main(None) == []

    def test_bare_hash_without_parens_ignored(self, hook_module, monkeypatch):
        # A bare '#1140' (cross-ref, not a squash marker) is NOT counted;
        # only the parenthesized '(#1141)' is.
        monkeypatch.setattr(
            hook_module,
            "_run",
            lambda *a, **k: _FakeProc("revert: drop #1140 hack (#1141)\n", 0),
        )
        assert hook_module.merged_prs_on_main(None) == [1141]


class TestNewerUnmentioned:
    def test_returns_newer_than_ceiling(self, hook_module):
        text = "Merged #1130, #1132. Working on #1127."
        merged = [1136, 1135, 1134, 1133, 1132, 1130, 1127]
        assert hook_module.newer_unmentioned(text, merged) == [1136, 1135, 1134, 1133]

    def test_high_mentioned_pr_raises_the_bar(self, hook_module):
        # The ceiling is max over ALL mentioned PRs, so mentioning #1135
        # raises the bar — #1134 (below it) is no longer "newer", and the
        # mentioned #1135 itself is excluded.
        text = "ceiling #1132 and also #1135"
        merged = [1136, 1135, 1134]
        assert hook_module.newer_unmentioned(text, merged) == [1136]

    def test_empty_when_no_prs_mentioned(self, hook_module):
        assert hook_module.newer_unmentioned("no prs", [1, 2, 3]) == []

    def test_empty_when_no_merged(self, hook_module):
        assert hook_module.newer_unmentioned("#10", []) == []

    def test_capped_at_max(self, hook_module):
        merged = list(range(200, 180, -1))  # 20 numbers, all > 100
        out = hook_module.newer_unmentioned("#100", merged)
        assert len(out) == hook_module.MAX_NEWER_MERGES
        assert out[0] == 200  # newest first

    def test_uses_full_text_ceiling_not_capped_extract(self, hook_module):
        # >MAX_PRS mentions; the true max (#900) is beyond the first 6, so
        # the ceiling must come from the full text, not extract_threads.
        text = " ".join(f"#{n}" for n in [10, 11, 12, 13, 14, 15, 900])
        merged = [901, 900, 800]
        assert hook_module.newer_unmentioned(text, merged) == [901]


class TestFormatBannerNewerMerges:
    def test_renders_newer_merges_line(self, hook_module, tmp_path):
        results = {
            "prs": {1132: "MERGED"},
            "branches": {},
            "pypi": None,
            "versions": [],
            "pkg": "",
            "newer_merges": [1136, 1135, 1133],
            "pr_ceiling": 1132,
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "NEWER merges the starter omits: #1136 #1135 #1133" in out
        assert "starter's newest: #1132" in out

    def test_newer_merges_alone_still_emits(self, hook_module, tmp_path):
        # A newer-merge finding alone (no verifiable PR/branch/pypi state)
        # is enough to surface a banner.
        results = {
            "prs": {},
            "branches": {},
            "pypi": None,
            "versions": [],
            "pkg": "",
            "newer_merges": [1136],
            "pr_ceiling": 1132,
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert out is not None
        assert "#1136" in out

    def test_no_line_when_no_newer_merges(self, hook_module, tmp_path):
        results = {
            "prs": {1132: "MERGED"},
            "branches": {},
            "pypi": None,
            "versions": [],
            "pkg": "",
            "newer_merges": [],
            "pr_ceiling": 1132,
        }
        out = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "NEWER merges" not in out


class TestReconcileWidening:
    def test_flags_newer_merges(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [1136, 1135, 1134, 1132])
        results = hook_module.reconcile("Merged #1132.", None, None)
        assert results["newer_merges"] == [1136, 1135, 1134]
        assert results["pr_ceiling"] == 1132

    def test_no_git_call_without_mentioned_prs(self, hook_module, monkeypatch):
        called = {"n": 0}

        def tracker(*a, **k):
            called["n"] += 1
            return []

        monkeypatch.setattr(hook_module, "merged_prs_on_main", tracker)
        results = hook_module.reconcile("no prs here", None, None)
        assert called["n"] == 0
        assert results["newer_merges"] == []
        assert results["pr_ceiling"] is None


class TestSpecStatusCrossRead:
    """The 2026-07-20 shipped-and-quiet guard: starter spec mentions
    are cross-read against the specs' own status lines."""

    def _spec(self, root, slug, statuses):
        d = root / "docs" / "specs" / slug
        d.mkdir(parents=True)
        for fname, status in statuses.items():
            (d / fname).write_text(f"# T\n\n{status}\n", encoding="utf-8")
        return d

    def test_terminal_spec_flagged(self, hook_module, tmp_path):
        self._spec(
            tmp_path,
            "done-spec",
            {"requirements.md": "**Status:** shipped (2026-07-20) — closed"},
        )
        specs = hook_module.check_specs("see docs/specs/done-spec for next work", tmp_path)
        assert specs == {"done-spec": "terminal:shipped"}

    def test_active_spec_reports_leading_token(self, hook_module, tmp_path):
        self._spec(
            tmp_path,
            "live-spec",
            {"requirements.md": "**Status:** active (2026-07-06) — fix plan drafted"},
        )
        specs = hook_module.check_specs("queue: docs/specs/live-spec", tmp_path)
        assert specs == {"live-spec": "active"}

    def test_whole_bold_convention_parses(self, hook_module, tmp_path):
        self._spec(
            tmp_path,
            "bold-spec",
            {"requirements.md": "**Status: approved (2026-07-19)** — chair"},
        )
        specs = hook_module.check_specs("docs/specs/bold-spec", tmp_path)
        assert specs == {"bold-spec": "approved"}

    def test_missing_dir_and_no_status(self, hook_module, tmp_path):
        self._spec(tmp_path, "silent-spec", {"decisions.md": "just a log"})
        text = "docs/specs/silent-spec and docs/specs/ghost-spec"
        specs = hook_module.check_specs(text, tmp_path)
        assert specs == {"silent-spec": "no-status", "ghost-spec": "missing"}

    def test_mixed_statuses_not_terminal(self, hook_module, tmp_path):
        self._spec(
            tmp_path,
            "half-spec",
            {
                "requirements.md": "**Status:** shipped (2026-07-19)",
                "tasks.md": "**Status:** parked (2026-07-13) — Resume-Trigger: evergreen",
            },
        )
        specs = hook_module.check_specs("docs/specs/half-spec", tmp_path)
        assert specs == {"half-spec": "shipped"}

    def test_banner_carries_closed_warning(self, hook_module, tmp_path):
        results = {
            "prs": {},
            "branches": {},
            "pypi": None,
            "versions": [],
            "newer_merges": [],
            "pr_ceiling": None,
            "specs": {"done-spec": "terminal:shipped", "live-spec": "active"},
        }
        banner = hook_module.format_banner(results, "global", tmp_path / "s.md")
        assert "done-spec=terminal:shipped" in banner
        assert "CLOSED spec(s): done-spec" in banner
        assert "live-spec" not in banner.split("CLOSED")[1]

    def test_none_repo_root_is_empty(self, hook_module):
        assert hook_module.check_specs("docs/specs/x", None) == {}


# --- provenance (session-start-integrity R1-R3) -----------------------


class _FakeGit:
    """Route _run calls by subcommand for provenance tests."""

    def __init__(self, remote="git@github.com:Smart-AI-Memory/attune-ai.git"):
        self.remote = remote

    def __call__(self, cmd, cwd):
        class _P:
            returncode = 0

            def __init__(self, out):
                self.stdout = out

        if cmd[:3] == ["git", "remote", "get-url"]:
            return _P(self.remote + "\n")
        if cmd[:3] == ["git", "branch", "--show-current"]:
            return _P("claude/some-branch\n")
        if cmd[:2] == ["git", "rev-parse"]:
            return _P("abc123def\n")
        return _P("")


class TestParseProvenance:
    def test_parses_and_strips_block(self, hook_module):
        text = (
            "---\n"
            "repo: smart-ai-memory/attune-ai\n"
            "branch: claude/x\n"
            "written_at: 2026-08-18T00:00:00+00:00\n"
            "---\n"
            "Body mentions #1234\n"
        )
        prov, body = hook_module.parse_provenance(text)
        assert prov["repo"] == "smart-ai-memory/attune-ai"
        assert prov["branch"] == "claude/x"
        assert body == "Body mentions #1234\n"

    def test_no_block_returns_text_unchanged(self, hook_module):
        prov, body = hook_module.parse_provenance("plain starter\n")
        assert prov == {}
        assert body == "plain starter\n"

    def test_branch_line_not_extracted_as_thread(self, hook_module):
        text = "---\nbranch: claude/prov-branch\n---\nno threads here\n"
        _, body = hook_module.parse_provenance(text)
        _, branches, _ = hook_module.extract_threads(body)
        assert branches == []

    def test_unknown_keys_ignored(self, hook_module):
        prov, _ = hook_module.parse_provenance("---\nfoo: bar\nrepo: a/b\n---\nx")
        assert prov == {"repo": "a/b"}


class TestRepoSlug:
    def test_ssh_remote_normalized(self, hook_module, monkeypatch, tmp_path):
        monkeypatch.setattr(hook_module, "_run", _FakeGit())
        assert hook_module.repo_slug(tmp_path) == "smart-ai-memory/attune-ai"

    def test_https_remote_normalized(self, hook_module, monkeypatch, tmp_path):
        monkeypatch.setattr(hook_module, "_run", _FakeGit("https://github.com/Owner/Repo.git"))
        assert hook_module.repo_slug(tmp_path) == "owner/repo"

    def test_no_remote_falls_back_to_dirname(self, hook_module, monkeypatch, tmp_path):
        monkeypatch.setattr(hook_module, "_run", lambda cmd, cwd: None)
        assert hook_module.repo_slug(tmp_path) == tmp_path.name.lower()

    def test_none_root_is_none(self, hook_module):
        assert hook_module.repo_slug(None) is None


class TestStarterAge:
    def test_absent_written_at_is_none(self, hook_module):
        assert hook_module.starter_age_hours({}) is None

    def test_unparseable_is_none(self, hook_module):
        assert hook_module.starter_age_hours({"written_at": "yesterday"}) is None

    def test_old_stamp_is_positive_hours(self, hook_module):
        age = hook_module.starter_age_hours({"written_at": "2020-01-01T00:00:00+00:00"})
        assert age is not None and age > 24 * 365


class TestFailClosedCrossRepo:
    def test_mismatch_refuses_verification(self, hook_module, tmp_path, capsys, monkeypatch):
        starter = tmp_path / "s.md"
        starter.write_text(
            "---\nrepo: other-org/other-repo\n---\nmerge PR #1118 now\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(hook_module, "repo_slug", lambda root: "smart-ai-memory/attune-ai")
        called = []
        monkeypatch.setattr(hook_module, "reconcile", lambda *a, **k: called.append(1))
        assert hook_module._reconcile_and_emit(starter, "global", tmp_path) is True
        out = capsys.readouterr().out
        assert "SKIPPED (cross-repo)" in out
        assert "other-org/other-repo" in out
        assert "#1118" not in out  # zero verdicts emitted
        assert called == []  # verification never ran

    def test_match_verifies_normally(self, hook_module, tmp_path, capsys, monkeypatch):
        starter = tmp_path / "s.md"
        starter.write_text(
            "---\nrepo: smart-ai-memory/attune-ai\n"
            "written_at: 2026-08-18T00:00:00+00:00\n---\nsee PR #7\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(hook_module, "repo_slug", lambda root: "smart-ai-memory/attune-ai")
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [])
        monkeypatch.setattr(hook_module, "_package_name", lambda root: None)
        assert hook_module._reconcile_and_emit(starter, "global", tmp_path) is True
        out = capsys.readouterr().out
        assert "#7 MERGED" in out
        assert "no provenance" not in out

    def test_stale_banner_line(self, hook_module, tmp_path, capsys, monkeypatch):
        starter = tmp_path / "s.md"
        starter.write_text(
            "---\nrepo: smart-ai-memory/attune-ai\n"
            "written_at: 2020-01-01T00:00:00+00:00\n---\nsee PR #7\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(hook_module, "repo_slug", lambda root: "smart-ai-memory/attune-ai")
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [])
        monkeypatch.setattr(hook_module, "_package_name", lambda root: None)
        hook_module._reconcile_and_emit(starter, "global", tmp_path)
        assert "STALE starter" in capsys.readouterr().out

    def test_unprovenanced_verdicts_carry_warning(self, hook_module, tmp_path, capsys, monkeypatch):
        starter = tmp_path / "s.md"
        starter.write_text("see PR #7\n", encoding="utf-8")
        monkeypatch.setattr(hook_module, "repo_slug", lambda root: "smart-ai-memory/attune-ai")
        monkeypatch.setattr(hook_module, "check_pr", lambda n, c: "MERGED")
        monkeypatch.setattr(hook_module, "merged_prs_on_main", lambda c: [])
        monkeypatch.setattr(hook_module, "_package_name", lambda root: None)
        hook_module._reconcile_and_emit(starter, "global", tmp_path)
        out = capsys.readouterr().out
        assert "no provenance" in out
        assert "#7 MERGED" in out


class TestStampProvenance:
    def test_stamp_writes_fields_and_is_idempotent(self, hook_module, tmp_path, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", _FakeGit())
        target = tmp_path / "starter.md"
        target.write_text("queue item one\n", encoding="utf-8")
        block = hook_module.stamp_provenance(target, tmp_path)
        assert "repo: smart-ai-memory/attune-ai" in block
        assert "branch: claude/some-branch" in block
        assert "head_sha: abc123def" in block
        first = target.read_text(encoding="utf-8")
        assert first.startswith("---\n")
        assert first.endswith("queue item one\n")
        # Second stamp replaces the block, never nests a second one.
        hook_module.stamp_provenance(target, tmp_path)
        second = target.read_text(encoding="utf-8")
        assert second.count("---\n") == 2
        assert second.endswith("queue item one\n")
        prov, body = hook_module.parse_provenance(second)
        assert prov["repo"] == "smart-ai-memory/attune-ai"
        assert body == "queue item one\n"


class TestStampPathGuard:
    """Cross-review F3 (codex, 2026-08-18): --stamp refuses
    non-markdown targets — frontmatter must never be injected into
    code or config files."""

    def test_non_markdown_target_refused(self, hook_module, tmp_path, monkeypatch, capsys):
        target = tmp_path / "settings.json"
        target.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(hook_module.sys, "argv", ["prog", "--stamp", str(target)])
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: tmp_path)
        assert hook_module.main() == 1
        assert target.read_text(encoding="utf-8") == "{}"
        assert "refusing to stamp" in capsys.readouterr().err


class TestStarterAgeNaiveStamp:
    """A naive (tz-less) written_at is treated as UTC, not rejected."""

    def test_naive_written_at_treated_as_utc(self, hook_module):
        age = hook_module.starter_age_hours({"written_at": "2020-01-01T00:00:00"})
        assert age is not None
        assert age > 0


class TestStampProvenanceDegrade:
    """With no derivable git identity (no repo root, every git call
    failing) the stamp still writes — provenance degrades to the
    written_at field alone rather than erroring (D2: absence soft)."""

    def test_stamps_written_at_only(self, hook_module, tmp_path, monkeypatch):
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)
        target = tmp_path / "starter.md"
        target.write_text("body\n", encoding="utf-8")

        block = hook_module.stamp_provenance(target, None)

        assert "written_at:" in block
        for absent in ("repo:", "branch:", "head_sha:"):
            assert absent not in block
        text = target.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert text.endswith("body\n")


class TestSpecLinesNoClosed:
    """Specs line renders without the closed-spec warning when no
    mentioned spec is in a terminal status."""

    def test_active_specs_render_without_warning(self, hook_module):
        lines = hook_module._spec_lines({"my-spec": "active: in progress"})
        assert lines == ["  specs: my-spec=active: in progress"]


class TestStampMainDefaultTargets:
    """main() --stamp with no explicit target derives the default:
    the project-local starter when a repo root exists, else the
    global starter — creating the file when absent."""

    def test_defaults_to_project_starter(self, hook_module, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(hook_module.sys, "argv", ["prog", "--stamp"])
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: tmp_path)
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)

        assert hook_module.main() == 0

        target = tmp_path / ".attune" / "next_session_starter.md"
        assert target.is_file()
        text = target.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert "written_at:" in text
        assert f"stamped {target}" in capsys.readouterr().out

    def test_explicit_existing_target_keeps_body(self, hook_module, tmp_path, monkeypatch, capsys):
        target = tmp_path / "starter.md"
        target.write_text("existing body\n", encoding="utf-8")
        monkeypatch.setattr(hook_module.sys, "argv", ["prog", "--stamp", str(target)])
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)

        assert hook_module.main() == 0

        text = target.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert text.endswith("existing body\n")
        assert "stamped" in capsys.readouterr().out

    def test_defaults_to_global_when_no_repo(self, hook_module, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(hook_module.sys, "argv", ["prog", "--stamp"])
        monkeypatch.setattr(hook_module, "_repo_root", lambda *a, **k: None)
        monkeypatch.setattr(hook_module, "_run", lambda *a, **k: None)
        global_starter = tmp_path / "home" / ".attune" / "next_session_starter.md"
        monkeypatch.setattr(hook_module, "STARTER_PATH", global_starter)

        assert hook_module.main() == 0

        assert global_starter.is_file()
        assert "written_at:" in global_starter.read_text(encoding="utf-8")
        assert f"stamped {global_starter}" in capsys.readouterr().out


# --- Shared wall-clock budget (L5 regression) ------------------------
#
# repo_slug + merged_prs_on_main run synchronously OUTSIDE the concurrent
# executor, once per reconcile pass, and there are two passes (project +
# global). With each git/gh call bounded only by SUBPROC_TIMEOUT (4s),
# the hook could take 12-32s against its registered 12s SessionStart
# timeout and get SIGKILLed mid-banner. The fix threads one shared
# ``_DEADLINE`` (GLOBAL_WALL_BUDGET) through ``_run`` / ``pypi_latest`` /
# the executor wait so total wall-clock stays under the registered
# timeout even when every git call blocks to its ceiling.


def _registered_session_start_timeout() -> int:
    """The starter_reconciler SessionStart timeout from settings.json."""
    settings = Path(__file__).resolve().parents[3] / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for group in data.get("hooks", {}).get("SessionStart", []):
        for hook in group.get("hooks", []):
            if "starter_reconciler.py" in hook.get("command", ""):
                return hook["timeout"]
    raise AssertionError("no starter_reconciler.py SessionStart hook in settings.json")


class TestSharedDeadline:
    def test_remaining_passthrough_without_deadline(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_DEADLINE", None)
        assert hook_module._remaining(4) == 4

    def test_remaining_clamps_to_time_left(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_DEADLINE", time.monotonic() + 0.5)
        remaining = hook_module._remaining(hook_module.SUBPROC_TIMEOUT)
        assert 0 < remaining <= 0.5
        assert remaining < hook_module.SUBPROC_TIMEOUT

    def test_run_clamps_timeout_to_remaining_budget(self, hook_module, monkeypatch):
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return _FakeProc("ok", 0)

        monkeypatch.setattr(hook_module.subprocess, "run", fake_run)
        monkeypatch.setattr(hook_module, "_DEADLINE", time.monotonic() + 0.5)
        hook_module._run(["git", "status"], None)
        assert captured["timeout"] <= 0.5
        assert captured["timeout"] < hook_module.SUBPROC_TIMEOUT

    def test_global_budget_under_registered_timeout(self, hook_module):
        # The whole point: the combined budget must leave the hook room to
        # finish (and print) before the harness SIGKILLs it.
        assert hook_module.GLOBAL_WALL_BUDGET < _registered_session_start_timeout()

    def test_hook_completes_under_registered_timeout_with_slow_git(self, hook_module, tmp_path):
        """End-to-end receipt: with git/gh sleeping far past their ceiling
        on PATH, and BOTH passes (project + global) active, the real hook
        script finishes well under its registered SessionStart timeout.

        Before the fix this same setup measured 24-32s (> 12s → SIGKILL,
        banner lost); after it, ~GLOBAL_WALL_BUDGET seconds.
        """
        fakebin = tmp_path / "bin"
        fakebin.mkdir()
        for name in ("git", "gh"):
            stub = fakebin / name
            stub.write_text("#!/bin/sh\nexec sleep 60\n", encoding="utf-8")
            stub.chmod(0o755)

        # Distinct project + global starters → BOTH reconcile passes run.
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        (repo / ".attune").mkdir(parents=True)
        (repo / ".attune" / "next_session_starter.md").write_text(
            "Merged PR #1118 and #1121; branch claude/foo. Ship 9.0.0.\n",
            encoding="utf-8",
        )
        home = tmp_path / "home"
        (home / ".attune").mkdir(parents=True)
        (home / ".attune" / "next_session_starter.md").write_text(
            "Merged PR #1200 and #1201; branch claude/bar. Ship 9.1.0.\n",
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["PATH"] = f"{fakebin}{os.pathsep}{env.get('PATH', '')}"
        env["HOME"] = str(home)
        # Force the SDK gate off so the hook body always runs (benchmark
        # escape hatch), regardless of the test runner's own env.
        env["ATTUNE_SDK_GATE_OVERRIDE"] = "1"
        env.pop("ATTUNE_SDK_SUBPROCESS", None)

        registered = _registered_session_start_timeout()
        start = time.monotonic()
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=str(repo),
            env=env,
            capture_output=True,
            text=True,
            timeout=registered * 3,  # generous: catch a hang, not the SLA
        )
        elapsed = time.monotonic() - start

        assert proc.returncode == 0
        assert elapsed < registered, (
            f"hook took {elapsed:.1f}s ≥ registered {registered}s timeout "
            f"(stderr: {proc.stderr!r})"
        )


class TestSharedDeadlineSkipPaths:
    """The clamp helper and the budget-exhausted skip paths.

    These pin the *skip* half of the shared-deadline contract: once the
    global budget is spent, remaining work is not started at all (rather
    than started with a fresh per-call ceiling, which is what pushed the
    hook past its registered SessionStart timeout). The clamp/passthrough
    half of ``_remaining`` is covered by ``TestSharedDeadline`` above.
    """

    def test_remaining_is_zero_once_deadline_passed(self, hook_module, monkeypatch):
        monkeypatch.setattr(hook_module, "_DEADLINE", hook_module.time.monotonic() - 1)
        assert hook_module._remaining(4.0) == 0.0

    def test_pypi_lookup_skipped_when_budget_spent(self, hook_module, monkeypatch):
        """The PyPI call must be SKIPPED, not started, past the deadline."""
        opened: list[str] = []
        monkeypatch.setattr(
            hook_module.urllib.request,
            "urlopen",
            lambda *a, **k: opened.append("called"),
        )
        monkeypatch.setattr(hook_module, "_DEADLINE", hook_module.time.monotonic() - 1)

        assert hook_module.pypi_latest("attune-ai") is None
        assert opened == []

    def test_subprocess_skipped_when_budget_spent(self, hook_module, monkeypatch):
        """_run must not spawn a process once the budget is spent."""
        spawned: list[list[str]] = []
        monkeypatch.setattr(
            hook_module.subprocess,
            "run",
            lambda cmd, **k: spawned.append(cmd),
        )
        monkeypatch.setattr(hook_module, "_DEADLINE", hook_module.time.monotonic() - 1)

        assert hook_module._run(["git", "status"], None) is None
        assert spawned == []
