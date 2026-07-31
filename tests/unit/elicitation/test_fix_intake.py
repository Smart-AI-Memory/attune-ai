"""Fix intake (outcome-first-fix Task 4): derived candidates, form
validity, and command composition — real tmp git repos, no mocks."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from attune.elicitation.fix_intake import (
    OTHER,
    build_fix_intake_form,
    compose_fix_command,
    list_subdirectories,
    probe_candidates,
    scope_candidates,
)


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def _commit_all(repo: Path, message: str = "x") -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            message,
        ],
        cwd=repo,
        check=True,
    )


def test_scope_candidates_changed_files_first(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    pkg = repo / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("X = 1\n")
    scopes = scope_candidates(repo)
    assert scopes[0] == "src/pkg/mod.py"
    assert "src/pkg" in scopes


def test_scope_candidates_skip_cache_and_degrade_without_git(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    cache = repo / "src" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "junk.pyc").write_text("junk")
    assert scope_candidates(repo) == []
    plain = tmp_path / "plain"
    plain.mkdir()
    assert scope_candidates(plain) == []


def test_scope_candidates_fall_back_to_recent_history_on_clean_tree(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    pkg = repo / "src" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("X = 1\n")
    docs = repo / "docs"
    docs.mkdir()
    (docs / "note.md").write_text("note\n")
    _commit_all(repo, "first")
    (pkg / "mod.py").write_text("X = 2\n")
    _commit_all(repo, "second")
    scopes = scope_candidates(repo)
    assert scopes, "clean tree with history must still derive candidates"
    assert scopes[0] == "src/pkg", "most-touched directory ranks first"
    assert "docs" in scopes


def test_fallback_skips_deleted_paths_and_degrades_without_commits(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    (repo / "gone.py").write_text("X = 1\n")
    _commit_all(repo)
    (repo / "gone.py").unlink()
    _commit_all(repo, "remove")
    assert scope_candidates(repo) == []
    sub = tmp_path / "sub"
    sub.mkdir()
    empty = _git_repo(sub)
    assert scope_candidates(empty) == []


def test_probe_candidates_map_scope_dir_to_mirror_test_dir(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    pkg = repo / "src" / "pkg" / "billing"
    pkg.mkdir(parents=True)
    (pkg / "mod.py").write_text("X = 1\n")
    mirror = repo / "tests" / "unit" / "billing"
    mirror.mkdir(parents=True)
    (mirror / "test_mod.py").write_text("def test_x(): pass\n")
    probes = probe_candidates(repo, ["src/pkg/billing"])
    assert "pytest tests/unit/billing/" in probes


def test_list_subdirectories_lists_validates_and_filters(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    (repo / "src").mkdir()
    (repo / "docs").mkdir()
    (repo / ".hidden").mkdir()
    (repo / "__pycache__").mkdir()
    (repo / "file.txt").write_text("x\n")
    top = list_subdirectories(repo, ".")
    assert top["dirs"] == ["docs", "src"]
    assert "error" not in top
    escape = list_subdirectories(repo, "../outside")
    assert escape["error"] == "path escapes the repository"
    assert escape["dirs"] == []
    not_dir = list_subdirectories(repo, "file.txt")
    assert not_dir["error"] == "not a directory"


def test_probe_candidates_from_scope_dir_and_tests_tree(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    scope = repo / "scratch"
    scope.mkdir()
    (scope / "pricing.py").write_text("X = 1\n")
    (scope / "pricing_suite.py").write_text("def test_x(): pass\n")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_pricing.py").write_text("def test_y(): pass\n")
    probes = probe_candidates(repo, ["scratch", "scratch/pricing.py"])
    assert "pytest scratch/pricing_suite.py" in probes
    assert "pytest tests/test_pricing.py" in probes


def test_form_builds_with_candidates_and_offers_other(tmp_path: Path) -> None:
    form = build_fix_intake_form(["src/pkg"], ["pytest tests/test_x.py"])
    ids = [q.id for q in form.questions]
    assert ids == ["request", "scope", "probes", "mode"]
    scope_q = form.questions[1]
    assert scope_q.type.value == "single_select"
    assert scope_q.options[-1] == OTHER
    assert form.questions[2].type.value == "multi_select"


def test_form_degrades_to_free_text_without_candidates() -> None:
    form = build_fix_intake_form([], [])
    scope_q, probes_q = form.questions[1], form.questions[2]
    assert scope_q.type.value == "text_input"
    assert probes_q.type.value == "text_input"
    assert scope_q.required and probes_q.required


def test_compose_full_run_command_quotes_everything() -> None:
    cmd = compose_fix_command(
        {
            "request": "boundary must be 'bulk' at 100",
            "scope": "src/pkg",
            "probes": ["pytest tests/test_x.py -q", "pytest tests/test_y.py"],
            "mode": "preview then run",
        }
    )
    argv = shlex.split(cmd)
    assert argv[:2] == ["attune", "fix"]
    assert argv[2] == "boundary must be 'bulk' at 100"
    assert argv.count("--probe") == 2
    assert ["--scope", "src/pkg"] == argv[argv.index("--scope") : argv.index("--scope") + 2]
    assert argv[-1] == "--run"


def test_compose_preview_mode_omits_run_and_other_scope() -> None:
    cmd = compose_fix_command(
        {
            "request": "fix it",
            "scope": OTHER,
            "probes": "pytest tests/test_x.py",
            "mode": "preview only",
        }
    )
    assert "--run" not in cmd
    assert "--scope" not in cmd
    assert cmd.count("--probe") == 1


def test_composed_command_round_trips_through_real_preview(tmp_path: Path) -> None:
    """The composed argv (minus the `attune` entry) satisfies the real
    CLI preview contract — exit 0 with --workflow fix, nothing run."""
    import os

    from attune.cli_minimal import main

    repo = _git_repo(tmp_path)
    (repo / "mod.py").write_text("X = 1\n")
    cmd = compose_fix_command(
        {
            "request": "make X be 2",
            "scope": "mod.py",
            "probes": ["pytest tests/test_mod.py"],
            "mode": "preview only",
        }
    )
    argv = shlex.split(cmd)[1:]
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        assert main(argv) == 0
    finally:
        os.chdir(cwd)
