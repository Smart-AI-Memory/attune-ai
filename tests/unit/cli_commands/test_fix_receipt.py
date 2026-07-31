"""Phase 2 tests: executable Fix proof through real boundaries.

The stub workflows replace ONLY the LLM edit step; registration,
translation, baseline capture, probe subprocesses, receipt assembly,
and exit codes are all real. The live LLM path is proven once by the
spend-gated dogfood run recorded in decisions.md.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune.cli_commands.fix_commands import cmd_fix
from attune.cli_commands.fix_receipt import (
    ProbeOutcome,
    assemble_receipt,
    capture_baseline,
    run_probes,
)
from attune.workflows.fix_workflow import FixWorkflow, make_edit_scope_guard

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "outcome_first_fix"
PY = Path(sys.executable).as_posix()


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


class _StubApplies:
    """Stub fix workflow: performs the known one-character fix."""

    async def execute(self, **kwargs):
        _apply_known_fix(Path.cwd())
        return SimpleNamespace(success=True, metadata={})


class _StubNoOp:
    """Claims success, changes nothing (the H2 liar)."""

    async def execute(self, **kwargs):
        return SimpleNamespace(success=True, metadata={})


class _StubOutOfScope:
    """Fixes in scope but ALSO edits an out-of-scope file."""

    async def execute(self, **kwargs):
        _apply_known_fix(Path.cwd())
        (Path.cwd() / "pricing_suite.py").write_text(
            (Path.cwd() / "pricing_suite.py").read_text() + "\n# tampered\n"
        )
        return SimpleNamespace(success=True, metadata={})


class _StubCrashes:
    async def execute(self, **kwargs):
        raise RuntimeError("agent exploded")


TARGET_PROBE = f"{PY} -m pytest pricing_suite.py::test_boundary_order_is_bulk -q"
SUITE_PROBE = f"{PY} -m pytest pricing_suite.py -q"


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


# ---------------------------------------------------------------
# The ruling's Phase 2 acceptance: initially failing probe passes
# through a real CLI/subprocess/file boundary
# ---------------------------------------------------------------


def test_round_trip_failing_probe_passes_after_fix(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Before: the target probe genuinely fails (real subprocess).
    before = subprocess.run(
        [sys.executable, "-m", "pytest", "pricing_suite.py::test_boundary_order_is_bulk", "-q"],
        cwd=fix_repo,
        capture_output=True,
    )
    assert before.returncode == 1

    _install_stub(monkeypatch, _StubApplies)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 0
    assert "pricing.py" in out  # attributed change from the baseline diff
    assert "[PASS]" in out
    assert "review the attributed diff and commit" in out


def test_workflow_success_with_failing_probes_exits_one_h2(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """H2: workflow exit alone NEVER marks success."""
    _install_stub(monkeypatch, _StubNoOp)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 1
    assert "[FAIL]" in out
    assert "inspect the diff" in out


def test_out_of_scope_edit_reported_and_fails(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_stub(monkeypatch, _StubOutOfScope)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 1
    assert "SCOPE VIOLATIONS" in out
    assert "pricing_suite.py" in out
    assert "revert the out-of-scope paths" in out


def test_workflow_crash_exits_two(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_stub(monkeypatch, _StubCrashes)
    assert cmd_fix(_args()) == 2


def test_missing_probe_binary_records_skipped_and_fails(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_stub(monkeypatch, _StubApplies)
    code = cmd_fix(_args(probe=["definitely-not-a-real-binary-xyz --version"]))
    out = capsys.readouterr().out
    assert code == 1
    assert "[SKIPPED]" in out
    assert "probe not executed" in out
    assert "make the skipped probe runnable" in out


def test_run_requires_scope_and_fix_workflow(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_stub(monkeypatch, _StubApplies)
    assert cmd_fix(_args(scope=None)) == 3
    assert "--run requires --scope" in capsys.readouterr().out
    assert cmd_fix(_args(workflow="code-review")) == 3
    assert "--workflow fix" in capsys.readouterr().out


# ---------------------------------------------------------------
# Baseline attribution (codex lane finding)
# ---------------------------------------------------------------


def test_pre_existing_dirty_file_not_attributed_or_revert_advised(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    user_file = fix_repo / "users_own_work.py"
    user_file.write_text("# the user's in-flight change\n")

    _install_stub(monkeypatch, _StubApplies)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 0
    assert "Pre-existing changes (not attributed" in out
    assert "users_own_work.py" in out
    # Never named in the next action.
    next_action_line = [ln for ln in out.splitlines() if "Safest next action" in ln][0]
    assert "users_own_work.py" not in next_action_line


def test_baseline_without_git_degrades_to_hash_attribution(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "mod.py").write_text("x = 1\n")
    baseline = capture_baseline(plain, [Path("mod.py")])
    assert baseline.git_available is False
    (plain / "mod.py").write_text("x = 2\n")
    receipt = assemble_receipt(
        contract=SimpleNamespace(probes=[]),  # type: ignore[arg-type]
        baseline=baseline,
        scope_paths=[Path("mod.py")],
        probe_outcomes=[ProbeOutcome(argv=["true"], status="PASS", returncode=0)],
    )
    assert "mod.py" in receipt.attributed_changes
    assert any("git unavailable" in u for u in receipt.uncertainty)


# ---------------------------------------------------------------
# Prevention layer: the Edit scope guard denies at tool-call time
# ---------------------------------------------------------------


def test_edit_scope_guard_denies_outside_and_allows_inside(tmp_path: Path) -> None:
    scope_file = tmp_path / "inside.py"
    scope_file.write_text("pass\n")
    guard = make_edit_scope_guard([scope_file])

    allowed = asyncio.run(guard({"tool_input": {"file_path": str(scope_file)}}, None, None))
    assert allowed == {}

    denied = asyncio.run(
        guard({"tool_input": {"file_path": str(tmp_path / "outside.py")}}, None, None)
    )
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "outside the fix contract's scope" in (
        denied["hookSpecificOutput"]["permissionDecisionReason"]
    )

    # Missing path: nothing to judge, allow (other guards still apply).
    assert asyncio.run(guard({"tool_input": {}}, None, None)) == {}


# ---------------------------------------------------------------
# FixWorkflow surface (SDK loop stubbed at iter_agent_messages —
# the real LLM path is the spend-gated live-fire receipt)
# ---------------------------------------------------------------


def test_fix_workflow_validates_inputs() -> None:
    workflow = FixWorkflow()
    result = asyncio.run(workflow.execute(goal="", scope_paths=["x.py"]))
    assert result.success is False
    result = asyncio.run(workflow.execute(goal="g", scope_paths=[]))
    assert result.success is False
    assert "scope_paths" in (result.error or "")


def test_fix_workflow_runs_through_stubbed_sdk_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def _empty_stream(_query):
        return
        yield  # pragma: no cover — makes this an async generator

    import attune.workflows.fix_workflow as module

    monkeypatch.setattr(module, "iter_agent_messages", _empty_stream)
    target = tmp_path / "scoped.py"
    target.write_text("pass\n")

    workflow = FixWorkflow()
    result = asyncio.run(
        workflow.execute(goal="g", scope_paths=[str(target)], done_conditions=["c"])
    )
    assert result.metadata["scope_paths"] == [str(target)]
    assert "agent_reported_changes" in result.metadata


def test_run_probes_reports_provenance(fix_repo: Path) -> None:
    from attune.cli_commands.fix_commands import VerificationProbe

    outcomes = run_probes(
        [VerificationProbe(argv=[sys.executable, "-c", "raise SystemExit(0)"])],
        cwd=fix_repo,
    )
    assert outcomes[0].status == "PASS"
    assert outcomes[0].returncode == 0
    assert outcomes[0].duration_ms >= 0


def test_fix_workflow_sdk_error_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import attune.workflows.fix_workflow as module

    target = tmp_path / "scoped.py"
    target.write_text("pass\n")

    def _raise_import(_query):
        raise ImportError("no sdk")

    monkeypatch.setattr(module, "iter_agent_messages", _raise_import)
    result = asyncio.run(FixWorkflow().execute(goal="g", scope_paths=[str(target)]))
    assert result.success is False
    assert "Agent SDK unavailable" in (result.error or "")

    def _raise_conn(_query):
        raise ConnectionError("net down")

    monkeypatch.setattr(module, "iter_agent_messages", _raise_conn)
    result = asyncio.run(FixWorkflow().execute(goal="g", scope_paths=[str(target)]))
    assert result.success is False
    assert "connection failed" in (result.error or "")


def test_fix_workflow_collects_stream_messages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import attune.workflows.fix_workflow as module

    sentinel = module.AgentRunResult(result_text="agent summary")

    async def _one_message_stream(_query):
        yield "fake-message"

    def _collect(message, assistant_parts, result_parts):
        assistant_parts.append("edited pricing.py")
        return sentinel

    monkeypatch.setattr(module, "iter_agent_messages", _one_message_stream)
    monkeypatch.setattr(module, "collect_agent_output", _collect)
    target = tmp_path / "scoped.py"
    target.write_text("pass\n")

    result = asyncio.run(
        FixWorkflow().execute(goal="g", scope_paths=[str(target)], done_conditions=["c"])
    )
    assert "edited pricing.py" in result.metadata["agent_reported_changes"]


# ---------------------------------------------------------------
# Codex lane regression pins (Phase 2 execution review)
# ---------------------------------------------------------------


def test_absolute_scope_spelling_is_not_a_false_violation(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--scope /abs/path/pricing.py` must attribute cleanly, not
    read as out-of-scope (raw-spelling vs repo-relative mismatch)."""
    _install_stub(monkeypatch, _StubApplies)
    code = cmd_fix(_args(scope=str(fix_repo / "pricing.py")))
    out = capsys.readouterr().out
    assert code == 0
    assert "SCOPE VIOLATIONS" not in out


def test_baseline_dirty_out_of_scope_file_modified_further_is_violation(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A file dirty BEFORE the run that the workflow modifies
    FURTHER must be attributed and flagged — the dirty-set
    subtraction alone would let it escape."""
    dirty = fix_repo / "already_dirty.py"
    dirty.write_text("# user WIP\n")

    class _StubTouchesDirty:
        async def execute(self, **kwargs):
            _apply_known_fix(Path.cwd())
            dirty.write_text("# user WIP\n# AGENT TAMPERED\n")
            return SimpleNamespace(success=True, metadata={})

    _install_stub(monkeypatch, _StubTouchesDirty)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 1
    assert "SCOPE VIOLATIONS" in out
    assert "already_dirty.py" in out


def test_porcelain_rename_records_parse_as_paths(fix_repo: Path) -> None:
    from attune.cli_commands.fix_receipt import _git_dirty_paths

    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "mv", "pricing.py", "renamed.py"],
        cwd=fix_repo,
        check=True,
    )
    paths, ok = _git_dirty_paths(fix_repo)
    assert ok
    assert "pricing.py" in paths
    assert "renamed.py" in paths
    assert not any(" -> " in p for p in paths)


def test_run_mode_constraint_text_is_truthful(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_stub(monkeypatch, _StubApplies)
    assert cmd_fix(_args()) == 0
    out = capsys.readouterr().out
    assert "execution authorized" in out
    assert "preview only: no execution" not in out


def test_scope_paths_accepts_bare_string_from_ops_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """PATH_ARG_REGISTRY rewrites --path into scope_paths as a STRING;
    iterating it as a sequence would yield one Path per character."""
    import attune.workflows.fix_workflow as module

    async def _empty_stream(_query):
        return
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(module, "iter_agent_messages", _empty_stream)
    target = tmp_path / "scoped.py"
    target.write_text("pass\n")

    result = asyncio.run(FixWorkflow().execute(goal="g", scope_paths=str(target)))
    assert result.metadata["scope_paths"] == [str(target)]
