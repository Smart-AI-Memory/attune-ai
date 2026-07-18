"""Behavioral tests for the read-only collaboration preflight."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import collaboration_preflight as preflight

REPO_ROOT = Path(__file__).resolve().parents[3]


def _result(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Build a completed process for a fake command."""
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class GitFixture:
    """Return deterministic results for preflight subprocesses."""

    def __init__(
        self,
        root: Path,
        *,
        missing_branch: bool = False,
        dirty_main: bool = False,
    ) -> None:
        self.root = root
        self.missing_branch = missing_branch
        self.dirty_main = dirty_main
        self.calls: list[tuple[tuple[str, ...], Path, dict[str, str] | None]] = []

    def __call__(
        self,
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        """Return the fixture result for ``command``."""
        cmd = tuple(command)
        self.calls.append((cmd, cwd, env))
        branch_ref = "refs/heads/codex/task"
        worktrees = (
            f"worktree {self.root}\n"
            "HEAD abcdef1234567890\n"
            f"branch {branch_ref}\n\n"
            f"worktree {self.root.parent / 'main'}\n"
            "HEAD abcdef1234567890\n"
            "branch refs/heads/main\n"
        )
        results = {
            ("git", "status", "--porcelain=v1", "--branch"): _result(stdout="## codex/task\n"),
            ("git", "worktree", "list", "--porcelain"): _result(stdout=worktrees),
            ("git", "symbolic-ref", "--quiet", "HEAD"): _result(stdout=f"{branch_ref}\n"),
            (
                "git",
                "show-ref",
                "--verify",
                "--quiet",
                branch_ref,
            ): _result(returncode=1 if self.missing_branch else 0),
            (
                "git",
                "-C",
                str(self.root.parent / "main"),
                "status",
                "--porcelain=v1",
                "--branch",
            ): _result(
                stdout="## main...origin/main\n" + (" M preserved.txt\n" if self.dirty_main else "")
            ),
            (
                "git",
                "rev-parse",
                "--verify",
                "refs/heads/main",
            ): _result(stdout="abcdef1234567890\n"),
            (
                "git",
                "rev-parse",
                "--verify",
                "refs/remotes/origin/main",
            ): _result(stdout="abcdef1234567890\n"),
            (
                "git",
                "check-ignore",
                "--quiet",
                ".codex/preflight-probe",
            ): _result(),
        }
        if cmd in results:
            return results[cmd]
        if (
            len(cmd) >= 2
            and Path(cmd[-2]).name == "project_collaboration_contract.py"
            and cmd[-1] == "--check"
        ):
            return _result(stdout="unchanged AGENTS.md\n")
        if len(cmd) >= 2 and Path(cmd[-2]).name == "sync_agents_skills.py" and cmd[-1] == "--check":
            return _result(stdout="Checked: 41 ok, 0 failed\n")
        raise AssertionError(f"unexpected command: {cmd}")


def _overriding(
    runner: GitFixture,
    overrides: dict[tuple[str, ...], subprocess.CompletedProcess[str]],
):
    """Wrap a Git fixture with command-specific results."""

    def call(
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        cmd = tuple(command)
        if cmd in overrides:
            runner.calls.append((cmd, cwd, env))
            return overrides[cmd]
        return runner(command, cwd, env)

    return call


def test_run_command_uses_requested_cwd(tmp_path: Path) -> None:
    result = preflight.run_command(
        (sys.executable, "-c", "from pathlib import Path; print(Path.cwd().name)"),
        tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == tmp_path.name


def test_parse_worktrees_preserves_branch_and_detached_entries(tmp_path: Path) -> None:
    output = (
        f"worktree {tmp_path / 'one'}\n"
        "HEAD abc\n"
        "branch refs/heads/main\n\n"
        f"worktree {tmp_path / 'two'}\n"
        "HEAD def\n"
        "detached\n"
    )

    entries = preflight.parse_worktrees(output)

    assert entries == [
        preflight.Worktree(tmp_path / "one", "abc", "refs/heads/main"),
        preflight.Worktree(tmp_path / "two", "def", None),
    ]


def test_git_status_failure_short_circuits(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    wrapped = _overriding(
        runner,
        {
            ("git", "status", "--porcelain=v1", "--branch"): _result(
                returncode=1,
                stderr="not a repository",
            )
        },
    )

    checks, snapshot = preflight.inspect_git_state(tmp_path, wrapped)

    assert checks == [preflight.Check("FAIL", "git-status", "not a repository")]
    assert snapshot == ""


def test_worktree_listing_failure_is_reported(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    wrapped = _overriding(
        runner,
        {
            ("git", "worktree", "list", "--porcelain"): _result(
                returncode=1,
                stderr="worktree metadata unavailable",
            )
        },
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    assert (
        preflight.Check(
            "FAIL",
            "worktree-metadata",
            "worktree metadata unavailable",
        )
        in checks
    )


def test_unregistered_current_path_is_reported(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    other = tmp_path.parent / "other"
    listing = f"worktree {other}\nHEAD abc\nbranch refs/heads/main\n"
    wrapped = _overriding(
        runner,
        {("git", "worktree", "list", "--porcelain"): _result(stdout=listing)},
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    assert (
        preflight.Check(
            "FAIL",
            "worktree-metadata",
            "current path is not registered",
        )
        in checks
    )


def test_symbolic_and_worktree_branch_mismatch_is_reported(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    wrapped = _overriding(
        runner,
        {("git", "symbolic-ref", "--quiet", "HEAD"): _result(stdout="refs/heads/other\n")},
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    branch_check = next(check for check in checks if check.name == "branch-consistency")
    assert branch_check.status == "FAIL"
    assert "worktree metadata names refs/heads/codex/task" in branch_check.detail


def test_missing_symbolic_branch_ref_fails_consistency_check(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path, missing_branch=True)

    checks, _ = preflight.inspect_git_state(tmp_path, runner)

    branch_check = next(check for check in checks if check.name == "branch-consistency")
    assert branch_check.status == "FAIL"
    assert "missing branch ref" in branch_check.detail


@pytest.mark.parametrize(
    ("worktree_branch", "expected_status", "expected_detail"),
    [
        ("branch refs/heads/codex/task\n", "FAIL", "HEAD appears detached"),
        ("detached\n", "WARN", "detached at abcdef1234"),
    ],
)
def test_detached_head_is_compared_with_worktree_metadata(
    tmp_path: Path,
    worktree_branch: str,
    expected_status: str,
    expected_detail: str,
) -> None:
    runner = GitFixture(tmp_path)
    listing = (
        f"worktree {tmp_path}\n"
        "HEAD abcdef1234567890\n"
        f"{worktree_branch}\n"
        f"worktree {tmp_path.parent / 'main'}\n"
        "HEAD abcdef1234567890\n"
        "branch refs/heads/main\n"
    )
    wrapped = _overriding(
        runner,
        {
            ("git", "worktree", "list", "--porcelain"): _result(stdout=listing),
            ("git", "symbolic-ref", "--quiet", "HEAD"): _result(returncode=1),
        },
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    branch_check = next(check for check in checks if check.name == "branch-consistency")
    assert branch_check.status == expected_status
    assert expected_detail in branch_check.detail


def test_dirty_main_is_reported_without_running_pull(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path, dirty_main=True)

    checks, _ = preflight.inspect_git_state(tmp_path, runner)

    main_check = next(check for check in checks if check.name == "main-checkout")
    assert main_check.status == "WARN"
    assert "do not pull automatically" in main_check.detail
    assert all("pull" not in command for command, _cwd, _env in runner.calls)


def test_missing_main_checkout_and_refs_are_warnings(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    listing = f"worktree {tmp_path}\n" "HEAD abcdef1234567890\n" "branch refs/heads/codex/task\n"
    wrapped = _overriding(
        runner,
        {
            ("git", "worktree", "list", "--porcelain"): _result(stdout=listing),
            ("git", "rev-parse", "--verify", "refs/heads/main"): _result(returncode=1),
            (
                "git",
                "rev-parse",
                "--verify",
                "refs/remotes/origin/main",
            ): _result(returncode=1),
        },
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    assert (
        preflight.Check(
            "WARN",
            "main-checkout",
            "no linked worktree has main checked out",
        )
        in checks
    )
    freshness = next(check for check in checks if check.name == "main-freshness")
    assert freshness.status == "WARN"
    assert "no network check attempted" in freshness.detail


def test_main_status_failure_and_ref_divergence_are_reported(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    main_status_command = (
        "git",
        "-C",
        str(tmp_path.parent / "main"),
        "status",
        "--porcelain=v1",
        "--branch",
    )
    wrapped = _overriding(
        runner,
        {
            main_status_command: _result(returncode=1, stderr="main unavailable"),
            (
                "git",
                "rev-parse",
                "--verify",
                "refs/remotes/origin/main",
            ): _result(stdout="different\n"),
            (
                "git",
                "rev-list",
                "--left-right",
                "--count",
                "refs/heads/main...refs/remotes/origin/main",
            ): _result(stdout="2 3\n"),
        },
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    assert preflight.Check("FAIL", "main-checkout", "main unavailable") in checks
    freshness = next(check for check in checks if check.name == "main-freshness")
    assert freshness.status == "WARN"
    assert "(2 ahead, 3 behind)" in freshness.detail


def test_codex_ignore_failure_is_reported(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    wrapped = _overriding(
        runner,
        {
            (
                "git",
                "check-ignore",
                "--quiet",
                ".codex/preflight-probe",
            ): _result(returncode=1)
        },
    )

    checks, _ = preflight.inspect_git_state(tmp_path, wrapped)

    assert preflight.Check("FAIL", "codex-ignore", ".codex/ is not ignored") in checks


def test_default_checks_do_not_fetch_pull_switch_or_invoke_uv(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)

    checks = preflight.run_preflight(tmp_path, runner=runner, skip_tests=True)

    forbidden = {"fetch", "pull", "switch", "checkout", "uv"}
    words = {word for command, _cwd, _env in runner.calls for word in command}
    assert forbidden.isdisjoint(words)
    receipt = next(check for check in checks if check.name == "read-only-receipt")
    assert receipt == preflight.Check("PASS", "read-only-receipt", "repository status unchanged")


def test_projection_failure_includes_command_output(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    command = (
        sys.executable,
        "scripts/project_collaboration_contract.py",
        "--check",
    )
    wrapped = _overriding(
        runner,
        {command: _result(returncode=1, stdout="projection drift")},
    )

    checks = preflight.check_projection_commands(tmp_path, wrapped)

    assert (
        preflight.Check(
            "FAIL",
            "collaboration-projection",
            "projection drift",
        )
        in checks
    )


def test_missing_pytest_skips_without_creating_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda name: None)

    check = preflight.run_governance_tests(tmp_path)

    assert check.status == "SKIP"
    assert "no environment or .venv was created" in check.detail


def test_governance_tests_use_current_interpreter_without_uv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, str] | None]] = []

    def runner(
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((tuple(command), env))
        return _result(stdout="53 passed in 1.00s\n")

    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda name: object())

    check = preflight.run_governance_tests(tmp_path, runner)

    assert check.status == "PASS"
    command, env = calls[0]
    assert command[:3] == (sys.executable, "-m", "pytest")
    assert "uv" not in command
    assert env is not None and env["PYTHONDONTWRITEBYTECODE"] == "1"


def test_governance_test_failure_is_reported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda name: object())

    def runner(
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        return _result(returncode=1, stderr="focused failure")

    check = preflight.run_governance_tests(tmp_path, runner)

    assert check == preflight.Check("FAIL", "governance-tests", "focused failure")


def test_status_change_fails_read_only_receipt(tmp_path: Path) -> None:
    runner = GitFixture(tmp_path)
    status_calls = 0

    def changing_runner(
        command: Sequence[str],
        cwd: Path,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal status_calls
        if tuple(command) == ("git", "status", "--porcelain=v1", "--branch"):
            status_calls += 1
            if status_calls == 2:
                return _result(stdout="## codex/task\n?? changed.txt\n")
        return runner(command, cwd, env)

    checks = preflight.run_preflight(tmp_path, runner=changing_runner, skip_tests=True)

    receipt = next(check for check in checks if check.name == "read-only-receipt")
    assert receipt == preflight.Check("FAIL", "read-only-receipt", "repository status changed")


def test_main_prints_summary_and_returns_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        preflight,
        "run_preflight",
        lambda root, skip_tests: [
            preflight.Check("FAIL", "branch", "broken"),
            preflight.Check("WARN", "main", "dirty"),
        ],
    )

    assert preflight.main(["--skip-tests"]) == 1

    output = capsys.readouterr().out
    assert preflight.MAIN_UPDATE_GUIDANCE in output
    assert "[FAIL] branch: broken" in output
    assert "Preflight: 1 failed, 1 warning(s)" in output


def test_main_update_guidance_protects_task_worktree() -> None:
    assert "existing main checkout" in preflight.MAIN_UPDATE_GUIDANCE
    assert "leave the current task worktree untouched" in preflight.MAIN_UPDATE_GUIDANCE
