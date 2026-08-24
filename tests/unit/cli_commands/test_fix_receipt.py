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
    # This stub changes NOTHING, so Phase 3 (G1) stopped advising the
    # user to inspect a diff that does not exist. The H2 subject of this
    # test — exit 1 plus a truthful FAIL row — is unchanged.
    assert "no diff to inspect" in out


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


def test_untracked_scope_dir_edits_are_attributed(tmp_path: Path) -> None:
    """The 'scratch copy inside the repo' flow: scope is an UNTRACKED
    directory. Git porcelain collapses it to one `dir/` entry before
    AND after the run, so per-file expansion must carry attribution —
    without it the receipt falsely reads "this run changed no files;
    the done conditions were already satisfied before it ran".
    """
    repo = tmp_path / "repo"
    scratch = repo / "scratch"
    scratch.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name in ("pricing.py", "pricing_suite.py"):
        shutil.copy(FIXTURE_DIR / name, scratch / name)
    # Nested subdirectory: expansion must recurse through it (the dir
    # entry itself is skipped, its file is hashed).
    (scratch / "sub").mkdir()
    (scratch / "sub" / "helper.py").write_text("HELPER = 1\n")
    # Cache artifacts are excluded from expansion entirely.
    (scratch / "__pycache__").mkdir()
    (scratch / "__pycache__" / "pricing.cpython-312.pyc").write_text("junk")

    baseline = capture_baseline(repo, [Path("scratch")])
    # Directory expanded to per-file hashes; no unreadable dir entry.
    assert "scratch/pricing.py" in baseline.scope_hashes
    assert "scratch/sub/helper.py" in baseline.scope_hashes
    assert not any("__pycache__" in p for p in baseline.scope_hashes)
    assert not any(h == "<unreadable>" for h in baseline.scope_hashes.values())

    _apply_known_fix(scratch)
    (scratch / "created_by_run.py").write_text("# new file from the run\n")
    (scratch / "sub" / "helper.py").write_text("HELPER = 2\n")

    receipt = assemble_receipt(
        contract=SimpleNamespace(probes=[]),  # type: ignore[arg-type]
        baseline=baseline,
        scope_paths=[Path("scratch")],
        probe_outcomes=[ProbeOutcome(argv=["true"], status="PASS", returncode=0)],
    )
    assert "scratch/pricing.py" in receipt.attributed_changes
    assert "scratch/created_by_run.py" in receipt.attributed_changes
    assert "scratch/sub/helper.py" in receipt.attributed_changes
    assert not any("__pycache__" in p for p in receipt.attributed_changes)
    assert receipt.scope_violations == []
    assert receipt.next_action == "review the attributed diff and commit"


def test_unreadable_scope_file_reported_as_uncertainty(tmp_path: Path) -> None:
    """A scope FILE that cannot be read hashes as `<unreadable>` and
    the receipt names it in Remaining uncertainty instead of silently
    treating it as unchanged."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    baseline = capture_baseline(repo, [Path("ghost.py")])
    assert baseline.scope_hashes["ghost.py"] == "<unreadable>"

    receipt = assemble_receipt(
        contract=SimpleNamespace(probes=[]),  # type: ignore[arg-type]
        baseline=baseline,
        scope_paths=[Path("ghost.py")],
        probe_outcomes=[ProbeOutcome(argv=["true"], status="PASS", returncode=0)],
    )
    assert any("baseline hash unavailable" in u and "ghost.py" in u for u in receipt.uncertainty)


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
    assert "outside the allowed write scope" in (
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


def test_nested_scope_path_is_not_a_false_violation(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Regression: scope paths were compared as `str(Path(...))`, which
    is backslash-separated on Windows, while git porcelain always emits
    forward slashes — so any NESTED scope path read as an out-of-scope
    violation and forced exit 1 on a correct fix. The original fixture
    used a flat `pricing.py` (identical under both conventions), so the
    Windows lanes passed while the bug was live.
    """
    pkg = fix_repo / "pkg"
    pkg.mkdir()
    (pkg / "pricing.py").write_text((fix_repo / "pricing.py").read_text())
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."],
        cwd=fix_repo,
        check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "nested"],
        cwd=fix_repo,
        check=True,
    )

    class _StubFixesNested:
        async def execute(self, **kwargs):
            t = Path.cwd() / "pkg" / "pricing.py"
            t.write_text(
                t.read_text().replace("if units > BULK_THRESHOLD", "if units >= BULK_THRESHOLD")
            )
            return SimpleNamespace(success=True, metadata={})

    _install_stub(monkeypatch, _StubFixesNested)
    code = cmd_fix(
        _args(
            scope="pkg/pricing.py",
            probe=[f"{PY} -c 'raise SystemExit(0)'".replace("'", '"')],
        )
    )
    out = capsys.readouterr().out
    assert "SCOPE VIOLATIONS" not in out, out
    assert code == 0, out
    # Attribution is recorded in POSIX form, matching git's output.
    assert "pkg/pricing.py" in out


def test_baseline_hash_keys_are_posix_form(fix_repo: Path) -> None:
    """Baseline keys must match git porcelain's forward-slash form."""
    pkg = fix_repo / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("x = 1\n")
    baseline = capture_baseline(fix_repo, [Path("pkg") / "mod.py"])
    assert "pkg/mod.py" in baseline.scope_hashes
    assert not any("\\" in k for k in baseline.scope_hashes)


# ---------------------------------------------------------------
# Error paths (codecov gap review) — each is reachable and each
# asserts BEHAVIOR, not merely that the line executed.
# ---------------------------------------------------------------


def test_whitespace_only_probe_is_rejected() -> None:
    """`--probe "   "` shlex-splits to [] — must abstain, not crash."""
    from attune.cli_commands.fix_commands import build_contract

    contract, error = build_contract(_args(probe=["   "], run=False))
    assert contract is None
    assert error is not None and "empty" in error


def test_cmd_fix_reports_contract_failure_through_the_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The contract-rejection branch inside cmd_fix (not build_contract)."""
    assert cmd_fix(_args(probe=[], run=False)) == 3
    out = capsys.readouterr().out
    assert "cannot preview:" in out
    assert "--probe" in out


def test_git_binary_missing_degrades_not_raises(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No git on PATH -> git_available False, never an exception."""
    import attune.cli_commands.fix_receipt as module

    def _boom(*a, **k):
        raise OSError("git not found")

    monkeypatch.setattr(module.subprocess, "run", _boom)
    baseline = capture_baseline(fix_repo, [Path("pricing.py")])
    assert baseline.git_available is False
    assert baseline.dirty_paths == set()


def test_git_nonzero_exit_degrades(tmp_path: Path) -> None:
    """`git status` failing (not a repo) degrades to hash-only."""
    from attune.cli_commands.fix_receipt import _git_dirty_paths

    paths, ok = _git_dirty_paths(tmp_path)
    assert ok is False
    assert paths == set()


def test_probe_oserror_records_skipped_with_reason(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A probe that dies mid-spawn is SKIPPED with the reason, not lost."""
    import attune.cli_commands.fix_receipt as module
    from attune.cli_commands.fix_commands import VerificationProbe

    def _boom(*a, **k):
        raise OSError("spawn failed")

    monkeypatch.setattr(module.subprocess, "run", _boom)
    outcomes = run_probes([VerificationProbe(argv=["anything"])], cwd=fix_repo)
    assert outcomes[0].status == "SKIPPED"
    assert "spawn failed" in outcomes[0].reason


def test_scope_guard_denies_when_path_cannot_resolve(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unresolvable path must DENY (fail closed), never allow."""
    import attune.workflows.fix_workflow as module

    guard = make_edit_scope_guard([tmp_path])

    def _boom(self):
        raise OSError("cannot resolve")

    monkeypatch.setattr(module.Path, "resolve", _boom)
    decision = asyncio.run(guard({"tool_input": {"file_path": "whatever.py"}}, None, None))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_porcelain_parser_handles_short_and_rename_lines(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parser contract against crafted porcelain: degenerate short
    lines are skipped, renames yield BOTH paths, normal lines pass."""
    import attune.cli_commands.fix_receipt as module
    from attune.cli_commands.fix_receipt import _git_dirty_paths

    crafted = " M src/real.py\n??\n\nR  old.py -> new.py\n"
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=crafted, stderr=""),
    )
    paths, ok = _git_dirty_paths(fix_repo)
    assert ok is True
    assert paths == {"src/real.py", "old.py", "new.py"}


# ---------------------------------------------------------------
# Scoped re-review findings (codex, staged lane 9 sent / 0 omitted)
# ---------------------------------------------------------------


def test_unverified_scope_never_reports_success(tmp_path: Path) -> None:
    """F1: with no git, out-of-scope edits are UNDETECTABLE — passing
    probes prove the goal but not the scope constraint, so exit 0
    would be a claim the run cannot back (H2)."""
    plain = tmp_path / "nogit"
    plain.mkdir()
    (plain / "mod.py").write_text("x = 1\n")
    baseline = capture_baseline(plain, [Path("mod.py")])
    assert baseline.git_available is False

    receipt = assemble_receipt(
        contract=SimpleNamespace(probes=[]),  # type: ignore[arg-type]
        baseline=baseline,
        scope_paths=[Path("mod.py")],
        probe_outcomes=[ProbeOutcome(argv=["true"], status="PASS", returncode=0)],
    )
    assert receipt.scope_verified is False
    assert receipt.exit_code() == 1  # NOT 0, despite every probe passing
    assert "SCOPE NOT VERIFIED" in receipt.render()
    assert "by hand" in receipt.next_action


def test_directory_scope_allows_descendants(fix_repo: Path) -> None:
    """F2: the workflow guard permits edits under a scope DIRECTORY
    (`allowed in target.parents`), so the receipt must not flag them
    as violations via exact-path matching."""
    from attune.cli_commands.fix_receipt import _in_scope

    scope = {"src/pkg"}
    assert _in_scope("src/pkg", scope)
    assert _in_scope("src/pkg/mod.py", scope)
    assert _in_scope("src/pkg/deep/nested.py", scope)
    # Must NOT match a sibling that merely shares a prefix string.
    assert not _in_scope("src/pkgother.py", scope)
    assert not _in_scope("src/other.py", scope)


def test_crash_still_emits_a_receipt(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """F3: a workflow that edits then crashes must still report what it
    left behind — a crash is when that matters most."""

    class _StubEditsThenCrashes:
        async def execute(self, **kwargs):
            _apply_known_fix(Path.cwd())
            raise RuntimeError("exploded after editing")

    _install_stub(monkeypatch, _StubEditsThenCrashes)
    code = cmd_fix(_args())
    out = capsys.readouterr().out
    assert code == 2
    assert "partial receipt" in out
    assert "pricing.py" in out  # the edit it made before dying is reported


def test_probe_env_preserves_user_pytest_addopts(
    fix_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4: extend PYTEST_ADDOPTS, never clobber it."""
    import attune.cli_commands.fix_receipt as module
    from attune.cli_commands.fix_commands import VerificationProbe

    monkeypatch.setenv("PYTEST_ADDOPTS", "-x --strict-markers")
    captured = {}

    def _capture(*a, **k):
        captured.update(k.get("env") or {})
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", _capture)
    run_probes([VerificationProbe(argv=["true"])], cwd=fix_repo)
    addopts = captured.get("PYTEST_ADDOPTS", "")
    assert "-x --strict-markers" in addopts
    assert "-p no:cacheprovider" in addopts
