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
import subprocess
import sys
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
        results = hook_module.reconcile("#42 v1.2.3", "pkg", None)
        # PR stays at its "unverified" seed; PyPI still resolves.
        assert results["prs"][42] == "unverified"
        assert results["pypi"] == "1.2.3"


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
