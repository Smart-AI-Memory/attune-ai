#!/usr/bin/env python3
"""Run read-only collaboration checks before work begins.

The preflight inspects the current branch and linked-worktree metadata,
compares local ``main`` with the cached ``origin/main``, checks both
single-source projections, confirms ``.codex/`` remains ignored, and
runs focused governance tests with the current Python interpreter.

It never fetches, pulls, switches branches, invokes ``uv``, or creates a
virtual environment. If pytest is unavailable, tests are skipped with an
explicit environment notice.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

Command = Sequence[str]
Runner = Callable[[Command, Path, dict[str, str] | None], subprocess.CompletedProcess[str]]

FOCUSED_TESTS = (
    "tests/unit/scripts/test_collaboration_preflight.py",
    "tests/unit/scripts/test_project_collaboration_contract.py",
    "tests/unit/plugins/test_sync_agents_skills.py",
)
MAIN_UPDATE_GUIDANCE = (
    "Inspect the existing main checkout first. Pull only when that checkout "
    "is on main and clean; otherwise fetch origin/main separately and leave "
    "the current task worktree untouched."
)


@dataclass(frozen=True)
class Worktree:
    """One entry from ``git worktree list --porcelain``."""

    path: Path
    head: str
    branch: str | None = None


@dataclass(frozen=True)
class Check:
    """One preflight finding."""

    status: str
    name: str
    detail: str


def run_command(
    command: Command,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a fixed preflight command without a shell."""
    return subprocess.run(  # noqa: S603
        list(command),
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def parse_worktrees(output: str) -> list[Worktree]:
    """Parse Git's stable porcelain worktree format."""
    entries: list[Worktree] = []
    fields: dict[str, str] = {}

    def append_entry() -> None:
        if "worktree" not in fields or "HEAD" not in fields:
            return
        entries.append(
            Worktree(
                path=Path(fields["worktree"]),
                head=fields["HEAD"],
                branch=fields.get("branch"),
            )
        )

    for line in output.splitlines():
        if not line:
            append_entry()
            fields = {}
            continue
        key, _, value = line.partition(" ")
        fields[key] = value
    append_entry()
    return entries


def _git(
    runner: Runner,
    root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    """Run Git within the repository root."""
    return runner(("git", *args), root, None)


def inspect_git_state(root: Path, runner: Runner = run_command) -> tuple[list[Check], str]:
    """Inspect branch, worktree, main, and dirty-tree state."""
    checks: list[Check] = []
    status_result = _git(runner, root, "status", "--porcelain=v1", "--branch")
    if status_result.returncode != 0:
        detail = status_result.stderr.strip() or "git status failed"
        return [Check("FAIL", "git-status", detail)], ""

    status_snapshot = status_result.stdout
    dirty_lines = [
        line for line in status_snapshot.splitlines() if line and not line.startswith("## ")
    ]
    if dirty_lines:
        checks.append(
            Check(
                "WARN",
                "working-tree",
                f"{len(dirty_lines)} existing change(s); preflight will preserve them",
            )
        )
    else:
        checks.append(Check("PASS", "working-tree", "clean"))

    listing = _git(runner, root, "worktree", "list", "--porcelain")
    if listing.returncode != 0:
        detail = listing.stderr.strip() or "git worktree list failed"
        checks.append(Check("FAIL", "worktree-metadata", detail))
        return checks, status_snapshot

    worktrees = parse_worktrees(listing.stdout)
    resolved_root = root.resolve()
    current = next((item for item in worktrees if item.path.resolve() == resolved_root), None)
    if current is None:
        checks.append(Check("FAIL", "worktree-metadata", "current path is not registered"))
        return checks, status_snapshot

    symbolic = _git(runner, root, "symbolic-ref", "--quiet", "HEAD")
    if symbolic.returncode == 0:
        branch_ref = symbolic.stdout.strip()
        if current.branch != branch_ref:
            checks.append(
                Check(
                    "FAIL",
                    "branch-consistency",
                    f"HEAD names {branch_ref}, worktree metadata names {current.branch or 'detached'}",
                )
            )
        else:
            branch_exists = _git(
                runner,
                root,
                "show-ref",
                "--verify",
                "--quiet",
                branch_ref,
            )
            if branch_exists.returncode != 0:
                checks.append(
                    Check(
                        "FAIL",
                        "branch-consistency",
                        f"HEAD points to missing branch ref {branch_ref}",
                    )
                )
            else:
                checks.append(Check("PASS", "branch-consistency", branch_ref))
    elif current.branch is not None:
        checks.append(
            Check(
                "FAIL",
                "branch-consistency",
                f"HEAD appears detached but worktree metadata names {current.branch}",
            )
        )
    else:
        checks.append(Check("WARN", "branch-consistency", f"detached at {current.head[:10]}"))

    main_worktree = next((item for item in worktrees if item.branch == "refs/heads/main"), None)
    if main_worktree is None:
        checks.append(Check("WARN", "main-checkout", "no linked worktree has main checked out"))
    else:
        main_status = runner(
            ("git", "-C", str(main_worktree.path), "status", "--porcelain=v1", "--branch"),
            root,
            None,
        )
        if main_status.returncode != 0:
            detail = main_status.stderr.strip() or "could not inspect main checkout"
            checks.append(Check("FAIL", "main-checkout", detail))
        else:
            main_dirty = [
                line
                for line in main_status.stdout.splitlines()
                if line and not line.startswith("## ")
            ]
            if main_dirty:
                checks.append(
                    Check(
                        "WARN",
                        "main-checkout",
                        f"{main_worktree.path} is dirty; do not pull automatically",
                    )
                )
            else:
                checks.append(Check("PASS", "main-checkout", f"{main_worktree.path} is clean"))

    local_main = _git(runner, root, "rev-parse", "--verify", "refs/heads/main")
    cached_main = _git(
        runner,
        root,
        "rev-parse",
        "--verify",
        "refs/remotes/origin/main",
    )
    if local_main.returncode != 0 or cached_main.returncode != 0:
        checks.append(
            Check(
                "WARN",
                "main-freshness",
                "local main or cached origin/main is unavailable; no network check attempted",
            )
        )
    elif local_main.stdout.strip() == cached_main.stdout.strip():
        checks.append(
            Check(
                "PASS",
                "main-freshness",
                "local main matches cached origin/main (network freshness not checked)",
            )
        )
    else:
        divergence = _git(
            runner,
            root,
            "rev-list",
            "--left-right",
            "--count",
            "refs/heads/main...refs/remotes/origin/main",
        )
        detail = "local main differs from cached origin/main"
        if divergence.returncode == 0:
            parts = divergence.stdout.split()
            if len(parts) == 2:
                detail += f" ({parts[0]} ahead, {parts[1]} behind)"
        checks.append(Check("WARN", "main-freshness", detail))

    ignored = _git(runner, root, "check-ignore", "--quiet", ".codex/preflight-probe")
    if ignored.returncode == 0:
        checks.append(Check("PASS", "codex-ignore", ".codex/ is ignored"))
    else:
        checks.append(Check("FAIL", "codex-ignore", ".codex/ is not ignored"))

    return checks, status_snapshot


def check_projection_commands(root: Path, runner: Runner = run_command) -> list[Check]:
    """Run both projector drift gates without authorizing writes."""
    commands = (
        (
            "collaboration-projection",
            (sys.executable, "scripts/project_collaboration_contract.py", "--check"),
        ),
        (
            "skills-projection",
            (sys.executable, "scripts/sync_agents_skills.py", "--check"),
        ),
    )
    checks: list[Check] = []
    for name, command in commands:
        result = runner(command, root, None)
        if result.returncode == 0:
            checks.append(Check("PASS", name, "in sync"))
        else:
            detail = result.stdout.strip() or result.stderr.strip() or "check failed"
            checks.append(Check("FAIL", name, detail))
    return checks


def run_governance_tests(root: Path, runner: Runner = run_command) -> Check:
    """Run focused tests without provisioning or changing an environment."""
    if importlib.util.find_spec("pytest") is None:
        return Check(
            "SKIP",
            "governance-tests",
            "pytest is unavailable in the current interpreter; no environment or .venv was created",
        )

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="attune-collaboration-preflight-") as temp_dir:
        command = (
            sys.executable,
            "-m",
            "pytest",
            *FOCUSED_TESTS,
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            temp_dir,
        )
        result = runner(command, root, env)
    if result.returncode == 0:
        summary = next(
            (line.strip() for line in reversed(result.stdout.splitlines()) if "passed" in line),
            "focused tests passed",
        )
        return Check(
            "PASS",
            "governance-tests",
            f"{summary}; used existing interpreter {sys.executable}",
        )
    detail = result.stdout.strip() or result.stderr.strip() or "focused tests failed"
    return Check("FAIL", "governance-tests", detail)


def run_preflight(
    root: Path,
    *,
    runner: Runner = run_command,
    skip_tests: bool = False,
) -> list[Check]:
    """Run all collaboration checks and verify repository status is unchanged."""
    checks, before_status = inspect_git_state(root, runner)
    checks.extend(check_projection_commands(root, runner))
    if skip_tests:
        checks.append(Check("SKIP", "governance-tests", "skipped by --skip-tests"))
    else:
        checks.append(run_governance_tests(root, runner))

    after_status = _git(runner, root, "status", "--porcelain=v1", "--branch")
    if after_status.returncode != 0:
        detail = after_status.stderr.strip() or "final git status failed"
        checks.append(Check("FAIL", "read-only-receipt", detail))
    elif after_status.stdout == before_status:
        checks.append(Check("PASS", "read-only-receipt", "repository status unchanged"))
    else:
        checks.append(Check("FAIL", "read-only-receipt", "repository status changed"))
    return checks


def main(argv: list[str] | None = None) -> int:
    """Run the collaboration preflight and print a concise receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="skip focused governance tests",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent

    print(f"Main update policy: {MAIN_UPDATE_GUIDANCE}\n")
    checks = run_preflight(root, skip_tests=args.skip_tests)
    for check in checks:
        print(f"[{check.status}] {check.name}: {check.detail}")

    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    print(f"\nPreflight: {failures} failed, {warnings} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
