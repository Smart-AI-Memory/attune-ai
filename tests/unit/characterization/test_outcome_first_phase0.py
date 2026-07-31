"""Phase 0 characterization pins for the outcome-first Fix spec.

docs/specs/outcome-first-fix/ Task 0: pin CURRENT behavior of the
seams the Fix facade will sit on, so later phases change behavior
deliberately or not at all.

Every pin is tagged:

- INTENTIONAL — contract behavior (spec'd or docstring-promised);
  a failure here means a real compatibility break.
- INCIDENTAL — current-but-accidental behavior we pin only to
  make drift VISIBLE; update the pin deliberately when the
  behavior changes on purpose (e.g. Phase 4 routing work).
"""

from __future__ import annotations

import asyncio
import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "outcome_first_fix"


# ---------------------------------------------------------------
# A. Exit-code contract (INTENTIONAL — spec'd in
#    docs/specs/workflow-failure-exit-propagation/)
# ---------------------------------------------------------------


def _run(workflow_cls: type) -> int:
    from attune.cli_commands._exit_codes import run_workflow_with_exit_code

    return run_workflow_with_exit_code(
        workflow_cls,
        {},
        name="characterization-stub",
        json_mode=False,
        print_result=lambda result: None,
    )


class _Succeeds:
    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(success=True)


class _FailsPlanned:
    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(success=False)


class _Raises:
    def execute(self) -> SimpleNamespace:
        raise RuntimeError("boom")


class _LegacyDict:
    def execute(self) -> dict:
        return {"status": "who knows"}


def test_exit_code_constants_intentional() -> None:
    """INTENTIONAL: the 0/1/2/3 contract constants."""
    from attune.cli_commands import _exit_codes as ec

    assert (
        ec.EXIT_SUCCESS,
        ec.EXIT_PLANNED_FAILURE,
        ec.EXIT_UNPLANNED_FAILURE,
        ec.EXIT_CLI_ERROR,
    ) == (0, 1, 2, 3)


def test_success_true_exits_zero_intentional() -> None:
    assert _run(_Succeeds) == 0


def test_success_false_exits_one_intentional() -> None:
    """INTENTIONAL: WorkflowResult.success is False -> exit 1.

    The historical exit-0-on-failure divergence recorded in the
    lessons corpus was FIXED by the exit-propagation spec; this
    pin keeps it fixed.
    """
    assert _run(_FailsPlanned) == 1


def test_uncaught_exception_exits_two_intentional(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert _run(_Raises) == 2


def test_legacy_result_without_success_attr_exits_zero_intentional() -> None:
    """INTENTIONAL (documented backwards-compat): a legacy result
    with NO ``success`` attribute maps to exit 0. This is the one
    residual spot where "exited 0" cannot prove success — the Fix
    receipt must therefore never trust exit code alone (spec H2).
    """
    assert _run(_LegacyDict) == 0


def test_unknown_workflow_raises_keyerror_intentional() -> None:
    """INTENTIONAL: registry lookup failure is a KeyError, which
    cmd_workflow_run maps to EXIT_CLI_ERROR (3)."""
    from attune.workflows import get_workflow

    with pytest.raises(KeyError):
        get_workflow("no-such-workflow-outcome-first-phase0")


# ---------------------------------------------------------------
# B. Router behavior for fix-adjacent input, through the REAL
#    algorithm, keyless (ANTHROPIC_API_KEY="" per CI convention)
# ---------------------------------------------------------------


@pytest.fixture()
def keyless_router(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from attune.cli_router import HybridRouter

    return HybridRouter(preferences_path=str(tmp_path / "prefs.yaml"))


def test_slash_command_routes_to_skill_intentional(keyless_router) -> None:
    result = asyncio.run(keyless_router.route("/dev commit"))
    assert result["type"] == "skill"
    assert result["skill"] == "dev"
    assert result["args"] == "commit"


def test_keyword_commit_routes_to_dev_intentional(keyless_router) -> None:
    result = asyncio.run(keyless_router.route("commit"))
    assert result["skill"] == "dev"
    assert result["args"] == "commit"
    assert result["source"] == "builtin"


def test_fix_keyword_absent_from_builtin_map_incidental(keyless_router) -> None:
    """INCIDENTAL: there is no 'fix' entry in the builtin keyword
    map today — 'fix ...' input always falls through to
    natural-language classification. The Fix facade (explicit
    ``attune fix``) bypasses this path entirely; if a 'fix'
    keyword is ever added, revisit the facade's routing notes.
    """
    assert "fix" not in keyless_router._keyword_to_skill


def test_nl_fix_phrase_routes_confidently_despite_low_confidence_incidental(
    keyless_router,
) -> None:
    """INCIDENTAL: keyless NL routing of a fix request returns a
    concrete workflow (currently bug-predict) at LOW confidence,
    with no abstention path. This IS the false-confident-route
    gap the ruling's Phase 4 exists to close — pinned so the gap's
    closure is a visible, deliberate change.
    """
    phrase = "fix the failing test in my project"
    first = asyncio.run(keyless_router.route(phrase))
    second = asyncio.run(keyless_router.route(phrase))

    assert first["type"] == "skill"
    assert first["source"] == "natural_language"
    assert first["workflow"] == "bug-predict"
    assert first["confidence"] < 0.5  # low confidence...
    assert "abstain" not in str(first).lower()  # ...yet no abstention
    # Deterministic: same input, same decision, byte-for-byte.
    assert first == second


# ---------------------------------------------------------------
# C. Dry-trace introspection: every seam-map interface in
#    phase0-inventory.md must import with its documented
#    signature. A prose-only mapping fails here.
# ---------------------------------------------------------------

DRY_TRACE = [
    ("attune.cli_router", "HybridRouter.route", ["user_input", "context"]),
    ("attune.cli_router", "workflow_to_slash_command", ["workflow"]),
    ("attune.routing", "SmartRouter.route_sync", ["request", "context"]),
    ("attune.workflows", "get_workflow", ["name"]),
    ("attune.workflows", "list_workflows", []),
    (
        "attune.cli_commands._exit_codes",
        "run_workflow_with_exit_code",
        ["workflow_cls", "input_data", "name", "json_mode", "print_result", "on_result"],
    ),
    ("attune.cli_commands.workflow_commands", "cmd_workflow_run", ["args"]),
    ("attune.cli_commands.diagnosis_commands", "cmd_diagnose", ["args"]),
    ("attune.diagnosis.engine", "diagnose", ["run_id", "origin"]),
    ("attune.telemetry.usage_tracker", "UsageTracker", None),
    ("attune.workflows.data_classes", "WorkflowResult", None),
]


@pytest.mark.parametrize("module_name,symbol,params", DRY_TRACE)
def test_dry_trace_seam_interface_resolves(
    module_name: str, symbol: str, params: list[str] | None
) -> None:
    import importlib

    module = importlib.import_module(module_name)
    target = module
    for part in symbol.split("."):
        target = getattr(target, part)

    if params is not None:
        actual = [
            p for p in inspect.signature(target).parameters if p not in ("self", "args", "kwargs")
        ]
        for expected in params:
            assert expected in actual or expected == "args", (
                f"{module_name}.{symbol}: expected param {expected!r} " f"not in {actual!r}"
            )


def test_workflow_result_carries_receipt_evidence_fields_intentional() -> None:
    """INTENTIONAL: the receipt (spec H2) projects these existing
    WorkflowResult fields — if one disappears, the receipt design
    must be revisited, not silently degraded."""
    from attune.workflows.data_classes import WorkflowResult

    field_names = set(WorkflowResult.__dataclass_fields__)
    assert {
        "success",
        "stages",
        "final_output",
        "cost_report",
        "metadata",
        "summary",
        "suggestions",
        "error",
        "error_type",
        "transient",
    } <= field_names


# ---------------------------------------------------------------
# D. Canonical fixture, through the REAL pytest subprocess
#    boundary (non-mocked)
# ---------------------------------------------------------------


def _pytest_subprocess(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-o", "addopts=", "-q"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


def test_fixture_target_fails_and_siblings_pass_live_boundary() -> None:
    """The hardened scenario's starting state, proven through a
    real subprocess: exactly the target test fails; every sibling
    passes."""
    proc = _pytest_subprocess(str(FIXTURE_DIR / "pricing_suite.py"))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "1 failed, 5 passed" in proc.stdout
    assert "test_boundary_order_is_bulk" in proc.stdout


def test_fixture_evades_main_suite_collection_live_boundary() -> None:
    """The seeded failure must never leak into the main suite:
    directory-level discovery collects nothing (pytest exit 5)."""
    proc = _pytest_subprocess(str(FIXTURE_DIR), "--collect-only")
    assert proc.returncode == 5, proc.stdout + proc.stderr
    assert "no tests collected" in proc.stdout + proc.stderr
