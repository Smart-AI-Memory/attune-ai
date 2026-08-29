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
    StructuredFixPreview,
    StructuredVerificationProbe,
    VerificationProbe,
    build_contract,
    build_structured_preview,
    cmd_fix,
)
from attune.cli_minimal import main

CANONICAL_PROBE = "pytest tests/fixtures/outcome_first_fix/pricing_suite.py"
CANONICAL_SCOPE = "tests/fixtures/outcome_first_fix/pricing.py"


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


def test_structured_preview_round_trips_and_binds_exact_future_argv() -> None:
    preview, error = build_structured_preview(
        _args(workflow="fix", scope=CANONICAL_SCOPE, run=False)
    )
    assert error is None
    assert preview is not None

    restored = StructuredFixPreview.from_dict(preview.to_dict())

    assert restored == preview
    assert restored.contract_hash() == preview.contract_hash()
    assert restored.scope == CANONICAL_SCOPE
    assert restored.command_argv[-1] == "--run"
    assert restored.command_argv[:2] == ("attune", "fix")


def test_structured_hash_is_independent_of_client_run_bit() -> None:
    preview, _ = build_structured_preview(_args(workflow="fix", scope=CANONICAL_SCOPE, run=False))
    run_preview, _ = build_structured_preview(
        _args(workflow="fix", scope=CANONICAL_SCOPE, run=True)
    )
    assert preview is not None and run_preview is not None
    assert preview.contract_hash() == run_preview.contract_hash()


@pytest.mark.parametrize(
    "args",
    [
        _args(request="", workflow="fix", scope=CANONICAL_SCOPE),
        _args(workflow="no-such-workflow", scope=CANONICAL_SCOPE),
        _args(workflow="fix", scope=None),
    ],
)
def test_structured_preview_abstains_when_contract_is_not_executable(args: Namespace) -> None:
    preview, error = build_structured_preview(args)
    assert preview is None
    assert error


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"argv": [], "description": "", "expected_exit": 0},
        {"argv": ["pytest"], "description": "", "expected_exit": True},
        {"argv": ["pytest"], "description": ""},
    ],
)
def test_structured_probe_rejects_invalid_documents(payload) -> None:
    with pytest.raises((TypeError, ValueError)):
        StructuredVerificationProbe.from_dict(payload)


def test_structured_preview_rejects_schema_drift() -> None:
    preview, _ = build_structured_preview(_args(workflow="fix", scope=CANONICAL_SCOPE))
    assert preview is not None
    raw = preview.to_dict()
    raw["unknown"] = True
    with pytest.raises(ValueError, match="missing or unknown"):
        StructuredFixPreview.from_dict(raw)


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
    assert "never guesses a route" in out
    # The abstention names the runnable next step, not just candidates.
    assert "--workflow fix" in out
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


TARGET_PROBE = (
    "pytest tests/fixtures/outcome_first_fix/pricing_suite.py::test_boundary_order_is_bulk"
)


def test_representative_preview_is_truthful(capsys: pytest.CaptureFixture[str]) -> None:
    """The CANONICAL scenario's full contract shape (D1): target
    probe + full-suite probe + source-confined scope — all three
    done conditions rendered."""
    workflow = _first_registered_workflow()
    assert (
        cmd_fix(
            _args(
                workflow=workflow,
                probe=[TARGET_PROBE, CANONICAL_PROBE],
                scope=CANONICAL_SCOPE,
            )
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "Goal: make the boundary order price as bulk" in out
    assert f"Selected workflow: {workflow}" in out
    assert "compatibility with the contract is checked at run time" in out
    assert "Probes (validated, not run):" in out
    assert _TRAILER in out
    # All three canonical done conditions, rendered.
    assert "test_boundary_order_is_bulk" in out
    assert "  3. diff confined to" in out
    # Truthfulness: no claim of anything Phase 1 cannot have done.
    for forbidden in ("executed successfully", "verification passed", "fix applied"):
        assert forbidden not in out.lower()


def test_missing_paths_flags_nonexistent_path_shaped_tokens(tmp_path: Path) -> None:
    (tmp_path / "real.py").write_text("X = 1\n")
    probe = VerificationProbe(
        argv=["pytest", "real.py", "gone/test_x.py", "gone/test_x.py::test_y", "-q", "bareword"]
    )
    assert probe.missing_paths(tmp_path) == ["gone/test_x.py", "gone/test_x.py"]
    assert VerificationProbe(argv=["pytest", "real.py"]).missing_paths(tmp_path) == []


def test_preview_warns_on_missing_probe_path_but_still_previews(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A probe naming a nonexistent test path warns (advisory — the
    fix run may create it) and the contract still previews exit 0."""
    workflow = _first_registered_workflow()
    assert (
        cmd_fix(_args(workflow=workflow, probe=["pytest tests/unit/does_not_exist_suite.py"])) == 0
    )
    out = capsys.readouterr().out
    assert "warning: path does not exist yet: tests/unit/does_not_exist_suite.py" in out
    assert _TRAILER in out


def test_preview_stays_silent_when_probe_paths_exist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    workflow = _first_registered_workflow()
    assert cmd_fix(_args(workflow=workflow)) == 0
    assert "warning: path does not exist yet" not in capsys.readouterr().out


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
            TARGET_PROBE,
            "--probe",
            CANONICAL_PROBE,
            "--scope",
            CANONICAL_SCOPE,
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert _TRAILER in out
    assert "  3. diff confined to" in out


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
    # Deliberate Phase 2 amendment: the Phase 1 notice claimed
    # execution "is not yet available" — now it exists behind --run,
    # so the truthful notice points there instead.
    workflow = _first_registered_workflow()
    assert cmd_fix(_args(explain=False, workflow=workflow)) == 0
    out = capsys.readouterr().out
    assert "pass --run to execute this contract" in out
    assert _TRAILER in out


# ---------------------------------------------------------------
# DTO stays internal (expansion gate 2)
# ---------------------------------------------------------------


def test_dto_is_documented_internal_only() -> None:
    import attune.cli_commands.fix_commands as module

    assert "INTERNAL ONLY" in (module.__doc__ or "")
    assert isinstance(FixContract("g"), FixContract)
    assert VerificationProbe(["true"]).render() == "true (expect exit 0)"
