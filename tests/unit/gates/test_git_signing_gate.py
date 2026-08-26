"""Gate: git commits made from inside the test suite must never sign.

A global ``commit.gpgsign = true`` on the developer's machine makes every
throwaway-repo fixture invoke GPG -> pinentry. Under pytest there is no TTY
to answer the prompt, so the commit blocks forever at 0% CPU and pytest
prints NOTHING — a full run was observed wedged 3.5h on a single
``git commit -qm seed`` (2026-08-26).

The suite-wide fix is the ``_isolate_git_config`` autouse fixture in
``tests/conftest.py``. These tests are its receipt: they fail if it is
deleted, weakened, or ordered away — on a signing developer machine AND on
a keyless CI runner, which reach the failure by different routes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# A hang is the failure mode under test, so every git call is bounded.
_TIMEOUT = 60


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def test_effective_commit_gpgsign_is_false() -> None:
    """The suite's effective git config must resolve signing to off.

    Portable in both directions: without the fixture a signing developer
    machine reports ``true``, and a CI runner with no global config reports
    nothing at all (exit 1). Only the fixture produces ``false``.
    """
    result = subprocess.run(
        ["git", "config", "--get", "commit.gpgsign"],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )

    assert result.stdout.strip() == "false", (
        "commit.gpgsign does not resolve to 'false' inside the suite — the "
        "_isolate_git_config fixture in tests/conftest.py is not in effect. "
        "Test fixtures that commit will invoke GPG and can hang forever."
    )


def test_a_commit_from_the_suite_is_unsigned(tmp_path: Path) -> None:
    """Behavioral receipt: a real commit completes and carries no signature.

    ``gpg.program`` is pointed at a path that does not exist, so an attempt
    to sign fails INSTANTLY instead of hanging on pinentry — a regression
    here is a fast red test, never another silent 3.5h wedge.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-q").returncode == 0
    (repo / "f.py").write_text("x = 1\n", encoding="utf-8")
    assert _git(repo, "add", ".").returncode == 0

    never = tmp_path / "gpg-must-not-run"
    result = _git(repo, "-c", f"gpg.program={never}", "commit", "-qm", "seed")

    assert (
        result.returncode == 0
    ), f"commit failed, so signing was attempted: {result.stderr.strip()}"
    signature = _git(repo, "log", "-1", "--format=%G?").stdout.strip()
    assert signature == "N", f"expected an unsigned commit, got %G? = {signature!r}"


def test_fixture_supplies_an_identity_a_fixture_can_override(tmp_path: Path) -> None:
    """Identity comes from config, so a fixture's own ``user.email`` wins.

    Pinning identity via ``GIT_AUTHOR_*``/``GIT_COMMITTER_*`` env vars would
    silently OUTRANK every fixture that sets ``user.email`` locally, changing
    what those tests observe. This pins the weaker, correct mechanism.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-q").returncode == 0
    assert _git(repo, "config", "user.email", "fixture@example.invalid").returncode == 0
    (repo / "f.py").write_text("x = 1\n", encoding="utf-8")
    assert _git(repo, "add", ".").returncode == 0
    assert _git(repo, "commit", "-qm", "seed").returncode == 0

    assert _git(repo, "log", "-1", "--format=%ae").stdout.strip() == ("fixture@example.invalid")
