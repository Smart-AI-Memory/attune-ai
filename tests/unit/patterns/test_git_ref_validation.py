"""Option-like git refs and config keys are refused at every boundary.

``git`` parses a leading ``-`` as an OPTION, not as data: a ref of
``--help`` makes ``git log`` print usage instead of a commit, and the
same holds for any value a caller can shape.

``_get_commit_info`` carried this guard inline, with a comment saying it
lived there "so a future caller inherits it" — but the rule was not
shared, so ``_get_commit_diff`` (flagged by the 14.0.0 post-release
review) and ``_get_git_config`` (found by sweeping the file rather than
fixing only what was reported) both went without it. One definition now,
applied at each boundary; these tests pin all three.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import subprocess

import pytest

from attune.patterns.git_extractor import GitPatternExtractor, _is_option_like


@pytest.fixture
def extractor(tmp_path):
    return GitPatternExtractor(patterns_dir=str(tmp_path))


@pytest.fixture
def argv_spy(monkeypatch):
    """Capture argv and prove git is never actually invoked when refused."""
    seen: list[list[str]] = []

    def fake_run(argv, *a, **k):
        seen.append(list(argv))
        return subprocess.CompletedProcess(args=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


class TestTheRuleItself:
    @pytest.mark.parametrize("value", ["-x", "--help", "--upload-pack=evil", "-"])
    def test_leading_dash_is_option_like(self, value):
        assert _is_option_like(value)

    @pytest.mark.parametrize("value", ["HEAD", "main", "v14.0.0", "abc123", "user.name"])
    def test_ordinary_values_are_not(self, value):
        assert not _is_option_like(value)


class TestEveryBoundaryRefuses:
    """Refused means git is NOT invoked — not merely that output is dropped."""

    def test_commit_info_refuses_and_does_not_run_git(self, extractor, argv_spy):
        assert extractor._get_commit_info("--help") is None
        assert argv_spy == [], "git must not be invoked with an option-like ref"

    @pytest.mark.parametrize("bad", [("--help", "HEAD"), ("HEAD", "--upload-pack=x")])
    def test_commit_diff_refuses_either_ref(self, extractor, argv_spy, bad):
        assert extractor._get_commit_diff(*bad) == ""
        assert argv_spy == [], "either position must refuse"

    def test_git_config_refuses_an_option_like_key(self, extractor, argv_spy):
        assert extractor._get_git_config("--global") is None
        assert argv_spy == []


class TestOrdinaryInputStillWorks:
    """A guard that breaks the happy path gets reverted, so pin it."""

    def test_commit_diff_runs_for_real_refs(self, extractor, argv_spy):
        extractor._get_commit_diff("HEAD~1", "HEAD")

        assert len(argv_spy) == 1
        assert argv_spy[0][:2] == ["git", "diff"]

    def test_commit_diff_pins_the_argument_list_with_a_terminator(self, extractor, argv_spy):
        """`--` stops a ref that also names a file being read as a path."""
        extractor._get_commit_diff("HEAD~1", "HEAD")

        assert argv_spy[0][-1] == "--"

    def test_commit_info_still_carries_its_terminator(self, extractor, argv_spy):
        extractor._get_commit_info("HEAD")

        assert argv_spy[0][-1] == "--"

    def test_git_config_runs_for_a_real_key(self, extractor, argv_spy):
        extractor._get_git_config("user.name")

        assert argv_spy[0] == ["git", "config", "user.name"]


class TestNoBoundaryWasMissed:
    """Sweep the module, not just the sites someone reported.

    The reported finding was _get_commit_diff alone; _get_git_config came
    out of walking every subprocess call in the file. This keeps that
    sweep honest as the module grows.
    """

    def test_every_dynamic_git_argv_is_guarded(self):
        import ast
        import inspect

        import attune.patterns.git_extractor as mod

        tree = ast.parse(inspect.getsource(mod))
        # _get_recent_commits_with_diffs' only dynamic argv element is
        # str(int(num_commits)) behind a >= 1 short-circuit, so an
        # option-like value is impossible by construction — behavioral
        # pins live in TestRecentCommitsBatchBoundary.
        guarded = {
            "_get_commit_info",
            "_get_commit_diff",
            "_get_git_config",
            "_get_recent_commits_with_diffs",
        }
        offenders = []
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef) or fn.name in guarded:
                continue
            for node in ast.walk(fn):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "run"
                    and node.args
                    and isinstance(node.args[0], ast.List | ast.Tuple)
                ):
                    continue
                if any(not isinstance(e, ast.Constant) for e in node.args[0].elts):
                    offenders.append(f"{fn.name}:{node.lineno}")

        assert not offenders, (
            f"unguarded dynamic git argv: {offenders} — route the value through "
            "_is_option_like or add the function to the guarded set"
        )


class TestRecentCommitsBatchBoundary:
    """Behavioral pins for the batched log path's argv discipline (#2241)."""

    def test_nonpositive_count_never_spawns_git(self, extractor, argv_spy):
        """num_commits < 1 short-circuits before any subprocess."""
        assert extractor._get_recent_commits_with_diffs(0) == []
        assert extractor._get_recent_commits_with_diffs(-3) == []
        assert argv_spy == []

    def test_batch_argv_is_static_except_forced_int_count(self, extractor, argv_spy):
        """The only dynamic argv element is the int-forced count, and the
        argv ends with `--` so nothing can be read as a pathspec."""
        extractor._get_recent_commits_with_diffs(7)

        assert argv_spy == [
            [
                "git",
                "log",
                "--first-parent",
                "-n",
                "7",
                "--pretty=format:%x1e%H%x1f%s%x1f%an%x1f%aI%x1f%P",
                "-p",
                "--",
            ],
        ]
