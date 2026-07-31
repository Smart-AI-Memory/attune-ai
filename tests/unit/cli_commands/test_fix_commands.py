"""Phase 1 tests for the dry ``attune fix`` contract preview.

Acceptance (outcome-first-fix Task 1): representative, ambiguous,
and risky inputs produce truthful previews or abstention. All
keyless-deterministic; Phase 1 executes NOTHING.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from attune.cli_commands.fix_commands import (
    _TRAILER,
    FixContract,
    VerificationProbe,
    build_contract,
    cmd_fix,
)
from attune.cli_minimal import main

CANONICAL_PROBE = "pytest tests/fixtures/outcome_first_fix/pricing_suite.py"


def _args(**overrides) -> Namespace:
    base = {
        "request": "make the boundary order price as bulk",
        "explain": True,
        "workflow": None,
        "probe": [CANONICAL_PROBE],
        "scope": None,
    }
    base.update(overrides)
    return Namespace(**base)


# ---------------------------------------------------------------
# Contract building
# ---------------------------------------------------------------


def test_goal_is_request_verbatim_no_inference() -> None:
    contract, error = build_contract(_args(request="  exactly these words  "))
    assert error is None
    assert contract is not None
    assert contract.goal == "exactly these words"


def test_probe_parsed_to_argv_list_never_shell() -> None:
    contract, _ = build_contract(_args())
    assert contract is not None
    assert contract.probes[0].argv[0] == "pytest"
    assert contract.probes[0].expected_exit == 0


def test_done_conditions_derive_one_per_probe() -> None:
    contract, _ = build_contract(_args(probe=[CANONICAL_PROBE, "python -c pass"]))
    assert contract is not None
    assert len(contract.done_conditions) == 2
    assert all(c.startswith("probe passes:") for c in contract.done_conditions)


def test_scope_inside_repo_becomes_constraint_and_done_condition(tmp_path: Path) -> None:
    contract, error = build_contract(_args(scope="tests/fixtures/outcome_first_fix/pricing.py"))
    assert error is None
    assert contract is not None
    assert any("diff confined to" in c for c in contract.done_conditions)


def test_empty_request_rejected() -> None:
    contract, error = build_contract(_args(request="   "))
    assert contract is None
    assert error is not None and "empty" in error


def test_no_probes_is_abstention_reason_naming_probe_flag() -> None:
    contract, error = build_contract(_args(probe=[]))
    assert contract is None
    assert error is not None and "--probe" in error


@pytest.mark.parametrize("raw", ["pytest x; rm -rf /", "a | b", "echo `id`", "a && b", "$(boom)"])
def test_shell_metacharacters_rejected_never_interpreted(raw: str) -> None:
    contract, error = build_contract(_args(probe=[raw]))
    assert contract is None
    assert error is not None and "shell metacharacters" in error


def test_scope_escaping_repo_rejected() -> None:
    contract, error = build_contract(_args(scope="../../outside.py"))
    assert contract is None
    assert error is not None and "--scope" in error


# ---------------------------------------------------------------
# Selection: --workflow or abstain (never guess)
# ---------------------------------------------------------------


def test_unknown_workflow_exits_cli_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_fix(_args(workflow="no-such-workflow-phase1")) == 3
    out = capsys.readouterr().out
    assert "unknown workflow" in out
    assert _TRAILER in out


def test_missing_workflow_abstains_listing_candidates(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cmd_fix(_args(workflow=None)) == 3
    out = capsys.readouterr().out
    assert "abstains" in out
    assert "Registered candidates:" in out
    assert _TRAILER in out


# ---------------------------------------------------------------
# Preview truthfulness (through cmd_fix and the REAL CLI entry)
# ---------------------------------------------------------------


def _first_registered_workflow() -> str:
    from attune.workflows import list_workflows

    names = sorted(wf["name"] for wf in list_workflows())
    assert names, "registry unexpectedly empty"
    return names[0]


def test_representative_preview_is_truthful(capsys: pytest.CaptureFixture[str]) -> None:
    workflow = _first_registered_workflow()
    assert cmd_fix(_args(workflow=workflow)) == 0
    out = capsys.readouterr().out
    assert "Goal: make the boundary order price as bulk" in out
    assert f"Selected workflow: {workflow}" in out
    assert "Probes (validated, not run):" in out
    assert _TRAILER in out
    # Truthfulness: no claim of anything Phase 1 cannot have done.
    for forbidden in ("executed successfully", "verification passed", "fix applied"):
        assert forbidden not in out.lower()


def test_real_cli_entry_representative_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    workflow = _first_registered_workflow()
    code = main(
        [
            "fix",
            "make the boundary order price as bulk",
            "--explain",
            "--workflow",
            workflow,
            "--probe",
            CANONICAL_PROBE,
        ]
    )
    assert code == 0
    assert _TRAILER in capsys.readouterr().out


def test_real_cli_entry_ambiguous_abstains_exit_three(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["fix", "fix something", "--explain", "--probe", CANONICAL_PROBE])
    assert code == 3
    assert "Registered candidates:" in capsys.readouterr().out


def test_real_cli_entry_risky_unknown_workflow_exit_three(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["fix", "x", "--explain", "--workflow", "nope", "--probe", CANONICAL_PROBE])
    assert code == 3


def test_bare_form_matches_explain_plus_notice(capsys: pytest.CaptureFixture[str]) -> None:
    workflow = _first_registered_workflow()
    assert cmd_fix(_args(explain=False, workflow=workflow)) == 0
    out = capsys.readouterr().out
    assert "execution is not yet available (Phase 2)" in out
    assert _TRAILER in out


# ---------------------------------------------------------------
# DTO stays internal (expansion gate 2)
# ---------------------------------------------------------------


def test_dto_is_documented_internal_only() -> None:
    import attune.cli_commands.fix_commands as module

    assert "INTERNAL ONLY" in (module.__doc__ or "")
    assert isinstance(FixContract("g"), FixContract)
    assert VerificationProbe(["true"]).render() == "true (expect exit 0)"
