"""Phase 3 tests: robustness, compatibility, and measurement.

Closes the six gaps measured against the tree in tasks.md Task 3.
Every test here is keyless and deterministic — the stub workflows
replace ONLY the LLM edit step, exactly as in the Phase 2 suite.

G1 no-change honesty | G2 partial success | G3 prompt persistence
G5 compatibility measurement | G6 receipt completeness + honesty
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune.cli_commands.fix_commands import cmd_fix

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "outcome_first_fix"
PY = Path(sys.executable).as_posix()

TARGET_PROBE = f"{PY} -m pytest pricing_suite.py::test_boundary_order_is_bulk -q"
SUITE_PROBE = f"{PY} -m pytest pricing_suite.py -q"

#: A string that appears in NO source file, so finding it on disk can
#: only mean the run persisted the request text (G3).
GOAL_SENTINEL = "zqx-phase3-prompt-sentinel-boundary-order"


@pytest.fixture()
def fix_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repo containing a COPY of the canonical fixture."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("pricing.py", "pricing_suite.py"):
        shutil.copy(FIXTURE_DIR / name, repo / name)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed"],
        cwd=repo,
        check=True,
    )
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    return repo


def _apply_known_fix(repo: Path) -> None:
    target = repo / "pricing.py"
    target.write_text(
        target.read_text().replace("if units > BULK_THRESHOLD", "if units >= BULK_THRESHOLD")
    )


class _StubNoOp:
    """Claims success, changes nothing (the H2 liar)."""

    async def execute(self, **kwargs):
        return SimpleNamespace(success=True, metadata={})


class _StubEditsButDoesNotFix:
    """Edits in scope, but the probes still fail — partial success."""

    async def execute(self, **kwargs):
        target = Path.cwd() / "pricing.py"
        target.write_text(target.read_text() + "\n# touched, but not fixed\n")
        return SimpleNamespace(success=True, metadata={})


def _args(**overrides) -> Namespace:
    base = {
        "request": "boundary order must price as bulk",
        "explain": False,
        "workflow": "fix",
        "probe": [TARGET_PROBE, SUITE_PROBE],
        "scope": "pricing.py",
        "run": True,
    }
    base.update(overrides)
    return Namespace(**base)


def _install_stub(monkeypatch: pytest.MonkeyPatch, stub_cls) -> None:
    import attune.workflows as workflows_pkg

    workflows_pkg._ensure_registry_initialized()
    monkeypatch.setitem(workflows_pkg.WORKFLOW_REGISTRY, "fix", stub_cls)


def _next_action_line(out: str) -> str:
    return [ln for ln in out.splitlines() if "Safest next action" in ln][0]


# ---------------------------------------------------------------
# G1 — a run that changed nothing says so
# ---------------------------------------------------------------


def test_no_change_run_with_passing_probes_is_named_not_claimed(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Conditions already satisfied: probes pass, nothing changed.

    Exit stays 0 — the probes are the authority (H2) — but the receipt
    must not advise committing a diff that does not exist.
    """
    _apply_known_fix(fix_repo)  # satisfied BEFORE the run
    _install_stub(monkeypatch, _StubNoOp)

    exit_code = cmd_fix(_args())
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "(none — this run changed no files)" in out
    action = _next_action_line(out)
    assert "nothing to commit" in action
    assert "already satisfied" in action
    assert "review the attributed diff and commit" not in out


def test_no_change_run_with_failing_probes_does_not_advise_a_diff(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The agent did nothing and the probes still fail."""
    _install_stub(monkeypatch, _StubNoOp)

    exit_code = cmd_fix(_args())
    out = capsys.readouterr().out

    assert exit_code == 1
    action = _next_action_line(out)
    assert "no diff to inspect" in action
    assert "inspect the diff, then re-run" not in action


# ---------------------------------------------------------------
# G2 — partial success names EVERY failing probe
# ---------------------------------------------------------------


def test_partial_success_names_every_failing_probe(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Two probes fail after a real in-scope edit: both are named."""
    _install_stub(monkeypatch, _StubEditsButDoesNotFix)

    exit_code = cmd_fix(_args())
    out = capsys.readouterr().out
    action = _next_action_line(out)

    assert exit_code == 1
    assert "all 2 failing probes" in action
    assert "test_boundary_order_is_bulk" in action  # the target probe
    assert action.count(" -m pytest ") == 2  # BOTH, not just failed[0]
    assert "inspect the diff" in action  # a real diff exists here


def test_single_failing_probe_keeps_the_singular_wording(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """One failure still reads naturally (no 'all 1 failing probes')."""
    _install_stub(monkeypatch, _StubEditsButDoesNotFix)

    exit_code = cmd_fix(_args(probe=[TARGET_PROBE]))
    action = _next_action_line(capsys.readouterr().out)

    assert exit_code == 1
    assert "re-run probe:" in action
    assert "all 1" not in action


# ---------------------------------------------------------------
# G3 — where the request text does and does not go
# ---------------------------------------------------------------


def test_fix_run_persists_no_file_containing_the_request_text(
    fix_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Evidence-chain: walk every file the run could have written.

    Asserted over REAL files on disk (repo tree + an isolated HOME),
    not over a mock of a persistence call — the claim is "nothing was
    written", and only a filesystem walk can back it.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows equivalent
    _install_stub(monkeypatch, _StubNoOp)

    cmd_fix(_args(request=GOAL_SENTINEL))
    assert GOAL_SENTINEL in capsys.readouterr().out  # it DID reach stdout

    searched = 0
    for root in (fix_repo, home):
        for path in root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            searched += 1
            content = path.read_text(encoding="utf-8", errors="replace")
            assert GOAL_SENTINEL not in content, f"request text persisted to {path}"
    assert searched > 0  # the walk actually looked at something


def test_ops_run_record_would_carry_goal_text_generic_surface(tmp_path: Path) -> None:
    """CHARACTERIZATION, not an endorsement (Phase 3 G3 finding).

    The `attune fix` surface persists nothing. Persistence enters only
    if the `fix` WORKFLOW is driven through the ops daemon, whose
    generic run-record writer stores every workflow's command line —
    including anything passed via `--input`. This pins that boundary so
    a future change routing Fix through ops inherits it knowingly
    rather than silently. Recorded in decisions.md D7; the fix belongs
    to the ops/run-record surface, not to this spec.
    """
    from attune.ops.runner import Run, _persist_run

    run = Run(id="abc123def456", workflow="fix")  # _RUN_ID_RE: hex only
    run.extra_args = ["--input", json.dumps({"goal": GOAL_SENTINEL})]
    run.command = ["attune", "workflow", "run", "fix", *run.extra_args]
    run.append_line(f"$ {' '.join(run.command)}")

    dest = _persist_run(run, tmp_path)

    assert dest is not None
    assert GOAL_SENTINEL in dest.read_text(encoding="utf-8")


# ---------------------------------------------------------------
# G5 — the compatibility measurement has a named source
# ---------------------------------------------------------------


def test_compatibility_pins_module_still_exists_and_is_named() -> None:
    """The Task 0 characterization module IS the compatibility metric.

    Deleting or renaming it would leave the reported
    "compatibility regressions: 0" unmeasured, which is the failure
    mode a metric with no source has.
    """
    pins = REPO_ROOT / "tests" / "unit" / "characterization" / "test_outcome_first_phase0.py"
    assert pins.is_file()
    body = pins.read_text(encoding="utf-8")
    for pinned in (
        "test_success_true_exits_zero_intentional",
        "test_success_false_exits_one_intentional",
        "test_uncaught_exception_exits_two_intentional",
        "test_legacy_result_without_success_attr_exits_zero_intentional",
    ):
        assert pinned in body


# ---------------------------------------------------------------
# G6 — receipt completeness + verification-failure honesty
# ---------------------------------------------------------------

#: Sections every receipt must carry for the D3 "evidence-valid
#: receipt completeness" metric to read 100%.
_REQUIRED_SECTIONS = (
    "🧾 Fix receipt",
    "Changes made (attributed to this run):",
    "Probes (evaluated independently):",
    "Safest next action:",
    "receipt reflects independently evaluated probes",
)


@pytest.mark.parametrize(
    ("stub", "pre_fix"),
    [
        (_StubNoOp, True),  # no-change, probes pass
        (_StubNoOp, False),  # no-change, probes fail
        (_StubEditsButDoesNotFix, False),  # changed, probes fail
    ],
)
def test_every_receipt_carries_every_required_section(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys, stub, pre_fix: bool
) -> None:
    """Receipt completeness measured across the outcome space."""
    if pre_fix:
        _apply_known_fix(fix_repo)
    _install_stub(monkeypatch, stub)

    cmd_fix(_args())
    out = capsys.readouterr().out

    for section in _REQUIRED_SECTIONS:
        assert section in out, f"receipt missing {section!r}"


def test_verification_failure_is_reported_not_omitted(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """Honesty metric: a failure produces a row, never silence."""
    _install_stub(monkeypatch, _StubNoOp)

    exit_code = cmd_fix(_args())
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL]" in out
    assert "[PASS]" not in out.split("Probes (evaluated independently):")[1]


def test_unrunnable_probe_is_reported_as_skipped_with_a_reason(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """A probe that cannot run is uncertainty, not a silent pass."""
    _install_stub(monkeypatch, _StubNoOp)

    exit_code = cmd_fix(_args(probe=["definitely-not-a-real-binary --check"]))
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[SKIPPED]" in out
    assert "Remaining uncertainty:" in out
    assert "command not found" in out
