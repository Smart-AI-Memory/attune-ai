"""Tests for the changelog-entry guard PreToolUse hook (retro 2026-09-11, item 6).

A ``git push`` whose range changes shipped code without touching
``CHANGELOG.md`` is refused at push time, before the CI ``changelog-entry``
gate can fail the PR. Covers the push classification, the block decision
against a REAL repository with a bare origin, the escape hatch, the
fail-open paths, the script entrypoint, and drift against the CI gate.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "src" / "attune" / "hooks" / "scripts" / "changelog_entry_guard.py"
GATE_PATH = REPO_ROOT / ".github" / "scripts" / "changelog_gate.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load("_changelog_entry_guard", SCRIPT_PATH)


@pytest.fixture(scope="module")
def gate():
    return _load("_changelog_gate_for_drift", GATE_PATH)


def _ctx(command: str, tool: str = "Bash") -> dict:
    return {"tool_name": tool, "tool_input": {"command": command}}


def _git_env(home: Path) -> dict[str, str]:
    """A scratch HOME so no global gitconfig, signing key, or hook is consulted."""
    return {
        **os.environ,
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }


@dataclass
class Repo:
    path: Path
    home: Path

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(self.path), "-c", "commit.gpgsign=false", *args],
            check=True,
            capture_output=True,
            env=_git_env(self.home),
            timeout=30,
        )

    def commit(self, rel: str, text: str, message: str) -> None:
        target = self.path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)


@pytest.fixture
def metrics(mod, tmp_path, monkeypatch):
    log = tmp_path / "metrics.jsonl"
    monkeypatch.setattr(mod, "METRICS_LOG", log)
    monkeypatch.delenv(mod.ALLOW_ENV, raising=False)
    return log


@pytest.fixture
def repo(metrics, tmp_path, monkeypatch) -> Repo:
    """A clone-shaped repo: bare origin, origin/main known, feature branch out."""
    home = tmp_path / "home"
    home.mkdir()
    origin = tmp_path / "origin.git"
    r = Repo(tmp_path / "repo", home)
    r.path.mkdir()
    subprocess.run(
        ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
        check=True,
        capture_output=True,
        env=_git_env(home),
        timeout=30,
    )
    r.git("init", "-q", "-b", "main")
    r.git("remote", "add", "origin", str(origin))
    (r.path / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")
    r.commit("src/pkg/mod.py", "X = 1\n", "base")
    r.git("push", "-q", "origin", "main")
    r.git("checkout", "-q", "-b", "feat/x")
    monkeypatch.chdir(r.path)
    return r


class TestPushClassification:
    @pytest.mark.parametrize(
        "command",
        [
            "git push",
            "git push origin main",
            "git push -u origin feat/x",
            "git push --force-with-lease origin feat/x",
            "git -C /repo push origin feat/x",
            "git -c core.x=y --no-pager push",
            "echo hi; git push origin main",
            "set -e\ngit push origin HEAD",
        ],
    )
    def test_pushes_are_detected(self, mod, command):
        assert any(mod.is_push(args) for args in mod.git_invocations(command))

    @pytest.mark.parametrize(
        "command",
        [
            "git status",
            "git commit -m push",
            "git -C /repo commit -m 'push later'",
            "echo git push",
            "gh pr create --title push",
        ],
    )
    def test_non_pushes_are_not_detected(self, mod, command):
        assert not any(mod.is_push(args) for args in mod.git_invocations(command))


class TestDecision:
    def test_non_push_command_allows(self, mod, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git status")) == 0
        assert mod.main(_ctx("pytest tests")) == 0

    def test_docs_only_push_allows(self, mod, repo):
        repo.commit("docs/guide.md", "# guide\n", "docs")
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_tests_and_ci_paths_are_not_shipped(self, mod, repo):
        repo.commit("tests/unit/test_x.py", "def test_x(): pass\n", "tests")
        repo.commit(".github/workflows/x.yml", "name: x\n", "ci")
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_src_push_without_changelog_blocks(self, mod, repo, capsys):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin feat/x")) == 2
        err = capsys.readouterr().err
        assert "src/pkg/new.py" in err
        assert "[Unreleased]" in err
        assert mod.ALLOW_ENV in err
        assert mod.OPT_OUT_LABEL in err

    def test_attune_redis_prefix_is_shipped(self, mod, repo):
        repo.commit("attune_redis/x.py", "Z = 3\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin feat/x")) == 2

    def test_changelog_in_range_allows(self, mod, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped")
        repo.commit("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- new\n", "entry")
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_changelog_in_an_earlier_commit_of_the_range_allows(self, mod, repo):
        repo.commit("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- new\n", "entry")
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped")
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_nothing_to_push_allows(self, mod, repo):
        assert mod.pushed_paths() == []
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_escape_hatch_allows(self, mod, repo, metrics, monkeypatch):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        monkeypatch.setenv(mod.ALLOW_ENV, "1")
        assert mod.main(_ctx("git push origin feat/x")) == 0
        assert "escape hatch" in metrics.read_text(encoding="utf-8")

    def test_non_bash_tool_is_ignored(self, mod, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main({"tool_name": "Edit", "tool_input": {"file_path": "x"}}) == 0

    def test_fire_writes_a_metric_row(self, mod, repo, metrics):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin feat/x")) == 2
        rows = [json.loads(line) for line in metrics.read_text(encoding="utf-8").splitlines()]
        assert rows[-1]["enforcement"] == mod.ENFORCEMENT_NAME
        assert rows[-1]["outcome"] == "fired"

    def test_block_message_truncates_a_long_listing(self, mod):
        message = mod.block_message([f"src/attune/m{i}.py" for i in range(12)])
        assert "src/attune/m7.py" in message
        assert "src/attune/m8.py" not in message
        assert "and 4 more" in message


class TestPushSources:
    """Which local refs a push ships — the range is read per ref, not from HEAD."""

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["push"], ["HEAD"]),
            (["push", "origin"], ["HEAD"]),
            (["push", "origin", "HEAD"], ["HEAD"]),
            (["push", "origin", "HEAD:refs/heads/x"], ["HEAD"]),
            (["push", "-u", "origin", "feat/x"], ["feat/x"]),
            (["push", "origin", "feat/y:feat/y"], ["feat/y"]),
            (["push", "origin", "+feat/y"], ["feat/y"]),
            (["push", "origin", "main", "feat/y"], ["main", "feat/y"]),
            (["push", "origin", "feat/y", "feat/y"], ["feat/y"]),
            (["push", "-o", "ci.skip", "origin", "feat/y"], ["feat/y"]),
            (["push", "--force-with-lease=feat/y:abc", "origin", "feat/y"], ["feat/y"]),
            (["-C", "/repo", "push", "origin", "feat/y"], ["feat/y"]),
            (["push", "--tags", "origin"], ["HEAD"]),
            (["push", "--repo", "origin", "feat/y"], ["feat/y"]),
            (["push", "--repo=origin", "feat/y"], ["feat/y"]),
            (["push", "--repo", "origin"], ["HEAD"]),
            (["push", "origin", "--", "feat/y"], ["feat/y"]),
            (["push", "origin", ":feat/y"], []),
            (["push", "--delete", "origin", "feat/y"], []),
            (["push", "-d", "origin", "feat/y"], []),
        ],
    )
    def test_sources(self, mod, args, expected):
        assert mod.push_sources(args) == expected

    def test_push_of_another_branch_is_judged_on_that_branch(self, mod, repo, capsys):
        """2026-09-12 lane F1: HEAD on clean main, the pushed branch ships src."""
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        repo.git("checkout", "-q", "main")
        assert mod.main(_ctx("git push origin feat/x")) == 2
        err = capsys.readouterr().err
        assert "src/pkg/new.py" in err
        assert "(ref feat/x)" in err
        assert mod.main(_ctx("git push origin main")) == 0

    def test_push_of_a_compliant_branch_from_an_offending_head(self, mod, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        repo.git("checkout", "-q", "-b", "feat/ok", "main")
        repo.commit("docs/x.md", "# x\n", "docs only")
        assert mod.main(_ctx("git push origin feat/x")) == 2
        assert mod.main(_ctx("git push origin feat/ok")) == 0
        assert mod.main(_ctx("git push origin feat/ok feat/x")) == 2

    def test_deletion_push_allows(self, mod, repo, metrics):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin :feat/x")) == 0
        assert mod.main(_ctx("git push --delete origin feat/x")) == 0
        assert "deletion only" in metrics.read_text(encoding="utf-8")

    def test_unreadable_ref_does_not_suppress_a_readable_offender(self, mod, repo, metrics, capsys):
        """Second-lane F2: the judged refs decide; only the unknown one is skipped."""
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin feat/x nonexistent")) == 2
        err = capsys.readouterr().err
        assert "skipping" in err
        assert "src/pkg/new.py" in err
        assert mod.main(_ctx("git push origin nonexistent main")) == 0
        rows = [json.loads(line) for line in metrics.read_text(encoding="utf-8").splitlines()]
        assert [r["outcome"] for r in rows[-4:]] == ["unknown", "fired", "unknown", "allowed"]

    def test_unresolvable_ref_fails_open(self, mod, repo, metrics, capsys):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx("git push origin nonexistent")) == 0
        assert "skipping" in capsys.readouterr().err
        assert "unreadable for nonexistent" in metrics.read_text(encoding="utf-8")


class TestEscapeHatchInCommand:
    """2026-09-12 lane F2: the advertised ``VAR=1 git push`` form must work.

    The hook is a separate process, so a leading assignment on the push
    command never reaches ``os.environ`` here; it is read from the text.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "ATTUNE_ALLOW_NO_CHANGELOG=1 git push origin feat/x",
            "env ATTUNE_ALLOW_NO_CHANGELOG=1 git push origin feat/x",
            "ATTUNE_ALLOW_NO_CHANGELOG=1 git -C . push -u origin feat/x",
            "git status && ATTUNE_ALLOW_NO_CHANGELOG=1 git push origin feat/x",
        ],
    )
    def test_leading_assignment_on_the_push_allows(self, mod, repo, metrics, command):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx(command)) == 0
        assert "escape hatch" in metrics.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "command",
        [
            "ATTUNE_ALLOW_NO_CHANGELOG=1 git status; git push origin feat/x",
            "ATTUNE_ALLOW_NO_CHANGELOG=0 git push origin feat/x",
        ],
    )
    def test_assignment_elsewhere_does_not_cover_the_push(self, mod, repo, command):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx(command)) == 2

    def test_exported_variable_still_allows(self, mod, repo, monkeypatch):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        monkeypatch.setenv(mod.ALLOW_ENV, "1")
        assert mod.main(_ctx("git push origin feat/x")) == 0

    def test_script_round_trip_honors_the_advertised_exit(self, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        run = TestStdinAndEntrypoint._run
        blocked = run(repo, json.dumps(_ctx("git push origin feat/x")))
        assert blocked.returncode == 2
        advertised = "ATTUNE_ALLOW_NO_CHANGELOG=1 git push origin feat/x"
        assert (
            advertised.split(" git ")[0] + "=1" in blocked.stderr
            or "ATTUNE_ALLOW_NO_CHANGELOG=1" in blocked.stderr
        )
        assert run(repo, json.dumps(_ctx(advertised))).returncode == 0


class TestFailOpen:
    """Every path where the guard cannot know must ALLOW, and never raise."""

    def test_no_origin_main_allows(self, mod, metrics, tmp_path, monkeypatch, capsys):
        home = tmp_path / "home"
        home.mkdir()
        r = Repo(tmp_path / "lonely", home)
        r.path.mkdir()
        r.git("init", "-q", "-b", "main")
        r.commit("src/pkg/new.py", "Y = 2\n", "shipped, no remote at all")
        monkeypatch.chdir(r.path)
        assert mod.pushed_paths() is None
        assert mod.main(_ctx("git push origin main")) == 0
        assert "skipping" in capsys.readouterr().err

    def test_outside_a_git_tree_allows(self, mod, metrics, tmp_path, monkeypatch):
        plain = tmp_path / "plain"
        plain.mkdir()
        monkeypatch.chdir(plain)
        assert mod.pushed_paths() is None
        assert mod.main(_ctx("git push origin main")) == 0

    def test_git_unreadable_yields_none(self, mod, monkeypatch):
        def boom(*a, **k):
            raise OSError("no git")

        monkeypatch.setattr(mod.subprocess, "run", boom)
        assert mod.pushed_paths() is None

    def test_unparseable_command_allows(self, mod, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        assert mod.main(_ctx('git push "unbalanced')) == 0

    def test_empty_command_allows(self, mod, repo):
        assert mod.main(_ctx("")) == 0

    def test_metrics_log_unwritable_is_swallowed(self, mod, tmp_path, monkeypatch):
        blocker = tmp_path / "not-a-dir"
        blocker.write_text("file, not a directory", encoding="utf-8")
        monkeypatch.setattr(mod, "METRICS_LOG", blocker / "metrics.jsonl")
        mod._log_metric("fired", "x")  # OSError inside -> swallowed


class TestStdinAndEntrypoint:
    def test_read_stdin_context_shapes(self, mod, monkeypatch):
        for raw, expect in (
            ("", {}),
            ("   ", {}),
            ("not json", {}),
            ("[1,2]", {}),
            ('{"a": 1}', {"a": 1}),
        ):
            monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
            assert mod._read_stdin_context() == expect

    @staticmethod
    def _run(repo: Repo, payload: str) -> subprocess.CompletedProcess:
        """The real entrypoint, as Claude Code runs it; SDK-gate signals scrubbed."""
        env = _git_env(repo.home)  # HOME is scratch: metrics land there, not in ~
        for signal in (
            "ATTUNE_SDK_SUBPROCESS",
            "CLAUDE_CODE_ENTRYPOINT",
            "ATTUNE_ALLOW_NO_CHANGELOG",
        ):
            env.pop(signal, None)
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=repo.path,
            env=env,
            timeout=30,
        )

    def test_script_round_trip_blocks_shipped_code_without_entry(self, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        r = self._run(repo, json.dumps(_ctx("git push origin feat/x")))
        assert r.returncode == 2
        assert "src/pkg/new.py" in r.stderr
        assert "no-changelog" in r.stderr

    def test_script_round_trip_allows_with_entry(self, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped")
        repo.commit("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- new\n", "entry")
        r = self._run(repo, json.dumps(_ctx("git push origin feat/x")))
        assert r.returncode == 0

    def test_script_round_trip_empty_stdin_allows(self, repo):
        assert self._run(repo, "").returncode == 0

    def test_script_round_trip_malformed_stdin_allows(self, repo):
        assert self._run(repo, "{not json").returncode == 0


class TestDriftAgainstCiGate:
    """The guard front-runs .github/scripts/changelog_gate.py; the two must agree."""

    def test_shipped_prefixes_match_the_ci_gate(self, mod, gate):
        assert mod.SHIPPED_PREFIXES == gate.SHIPPED_PREFIXES

    def test_changelog_path_and_label_match_the_ci_gate(self, mod, gate):
        assert mod.CHANGELOG == gate.CHANGELOG
        assert mod.OPT_OUT_LABEL == gate.OPT_OUT_LABEL

    def test_verdict_agrees_with_the_gate_on_the_same_range(self, mod, gate, repo):
        repo.commit("src/pkg/new.py", "Y = 2\n", "shipped, no entry")
        paths = mod.pushed_paths()
        assert gate.is_satisfied(paths, []) is False
        assert mod.main(_ctx("git push origin feat/x")) == 2

        repo.commit("CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- new\n", "entry")
        paths = mod.pushed_paths()
        assert gate.is_satisfied(paths, []) is True
        assert mod.main(_ctx("git push origin feat/x")) == 0
