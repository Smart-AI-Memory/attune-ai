"""Dry explicit Fix contract — ``attune fix`` (Phase 1).

docs/specs/outcome-first-fix/ Task 1: the smallest internal
boundary DTO plus a preview-only CLI surface. Phase 1 NEVER
executes anything: no workflow run, no probe subprocess, no file
writes, no LLM call. Every path renders a truthful preview or
abstains with ``EXIT_CLI_ERROR``.

INTERNAL ONLY: ``FixContract`` and ``VerificationProbe`` are a
boundary DTO between the CLI and existing workflow inputs. They
are NOT a public schema — no JSON schema is emitted, and no
import stability is promised outside ``attune.*`` (spec expansion
gate 2).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import Namespace

from attune.cli_commands._exit_codes import EXIT_CLI_ERROR, EXIT_SUCCESS

#: Characters that would only matter under a shell. Probes are argv
#: lists and are never shell-interpreted; input containing these is
#: rejected outright rather than silently treated as literals.
_SHELL_METACHARACTERS = set(";|&<>`$")

_TRAILER = "dry preview — nothing was executed"


@dataclass
class VerificationProbe:
    """One verification command: argv list, never a shell string."""

    argv: list[str]
    description: str = ""
    expected_exit: int = 0

    def render(self) -> str:
        """Human-readable one-liner for the preview."""
        label = self.description or " ".join(self.argv)
        return f"{label} (expect exit {self.expected_exit})"


@dataclass
class FixContract:
    """Internal boundary DTO: goal, done conditions, constraints,
    verification probes (spec H2). Translated ONCE into existing
    workflow inputs at execution time (Phase 2)."""

    goal: str
    done_conditions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    probes: list[VerificationProbe] = field(default_factory=list)


def _repo_root() -> Path:
    """Nearest ancestor (including cwd) containing a ``.git`` entry.

    Anchors ``--scope`` validation to the repository the user is
    working in, regardless of which subdirectory they invoke from
    (a ``.git`` FILE counts — worktrees have one). Outside any
    repository it falls back to the cwd; the rendered constraint
    line shows the resolved path either way, so the anchor is
    always visible in the preview.
    """
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return cwd


def _parse_probe(raw: str) -> VerificationProbe:
    """Parse one ``--probe`` value into a validated probe.

    Raises:
        ValueError: empty command or shell metacharacters present.
    """
    bad = _SHELL_METACHARACTERS.intersection(raw)
    if bad:
        raise ValueError(
            f"probe contains shell metacharacters ({''.join(sorted(bad))!r}); "
            "probes are argv lists and are never run through a shell"
        )
    argv = shlex.split(raw)
    if not argv:
        raise ValueError("probe command is empty")
    return VerificationProbe(argv=argv)


def build_contract(args: Namespace) -> tuple[FixContract | None, str | None]:
    """Map CLI flags to a validated ``FixContract``.

    The goal is the request text VERBATIM — no inference. Probes
    come only from explicit ``--probe`` flags; ``--scope`` must
    resolve inside the current working tree.

    Returns:
        ``(contract, None)`` on success, ``(None, reason)`` when the
        input cannot yield a truthful contract.
    """
    goal = (args.request or "").strip()
    if not goal:
        return None, "request text is empty — nothing to fix"

    probes: list[VerificationProbe] = []
    for raw in args.probe or []:
        try:
            probes.append(_parse_probe(raw))
        except ValueError as exc:
            return None, f"invalid --probe {raw!r}: {exc}"
    if not probes:
        return None, (
            "no verification probes given — cannot verify a fix; "
            'provide at least one --probe "<command>"'
        )

    if getattr(args, "run", False):
        constraints = ["execution authorized: scoped workflow run + independent probe verification"]
    else:
        constraints = ["preview only: no execution, no file writes"]
    done_conditions = [f"probe passes: {probe.render()}" for probe in probes]

    scope = getattr(args, "scope", None)
    if scope:
        from attune.security.path_validation import _validate_file_path

        try:
            validated = _validate_file_path(scope, allowed_dir=str(_repo_root()))
        except ValueError as exc:
            return None, f"invalid --scope {scope!r}: {exc}"
        constraints.append(f"scope: diff confined to {validated}")
        done_conditions.append(f"diff confined to {validated}")

    return FixContract(goal, done_conditions, constraints, probes), None


def _select_workflow(args: Namespace) -> tuple[str | None, str]:
    """Resolve ``--workflow`` against the real registry, or abstain.

    A false confident route is worse than abstention (ruling):
    with no ``--workflow`` we NEVER guess — we list candidates.

    Returns:
        ``(name, detail)`` when selected; ``(None, abstention)``
        otherwise.
    """
    from attune.workflows import get_workflow, list_workflows

    requested = getattr(args, "workflow", None)
    if requested:
        try:
            workflow_cls = get_workflow(requested)
        except KeyError:
            return None, f"unknown workflow {requested!r} — see `attune workflow list`"
        schema = "declared" if hasattr(workflow_cls, "input_schema") else "none"
        return requested, f"input schema: {schema}"

    names = sorted(wf["name"] for wf in list_workflows())
    return None, (
        "no --workflow given — selection abstains rather than guess.\n"
        "Registered candidates: " + (", ".join(names) if names else "(none registered)")
    )


def cmd_fix(args: Namespace) -> int:
    """Render the dry Fix preview, execute with --run, or abstain (exit 3)."""
    contract, error = build_contract(args)
    if contract is None:
        print(f"cannot preview: {error}")
        print(_TRAILER)
        return EXIT_CLI_ERROR

    selected, detail = _select_workflow(args)

    print("🔍 Fix preview\n")
    print(f"Goal: {contract.goal}\n")
    print("Done when:")
    for index, condition in enumerate(contract.done_conditions, 1):
        print(f"  {index}. {condition}")
    print("\nConstraints:")
    for constraint in contract.constraints:
        print(f"  - {constraint}")
    print("\nProbes (validated, not run):")
    for probe in contract.probes:
        print(f"  - {probe.render()}")

    if selected is None:
        print(f"\n{detail}")
        print(_TRAILER)
        return EXIT_CLI_ERROR

    print(f"\nSelected workflow: {selected} [{detail}]")
    print("  (user-specified; contract-to-workflow compatibility is verified in Phase 2)")

    if getattr(args, "run", False):
        return _run_fix(args, contract, selected)

    if not getattr(args, "explain", False):
        print("note: execution not requested — pass --run to execute this contract")
    print(_TRAILER)
    return EXIT_SUCCESS


def _run_fix(args: Namespace, contract: FixContract, selected: str) -> int:
    """Execute the contract through the existing machinery (Phase 2).

    One translation of the DTO into workflow inputs; probes evaluated
    independently by the receipt layer afterward — the workflow's own
    result never decides the 0/1 exit (H2).
    """
    import asyncio
    import traceback

    from attune.cli_commands.fix_receipt import (
        assemble_receipt,
        capture_baseline,
        run_probes,
    )
    from attune.workflows import get_workflow

    if selected != "fix":
        print(
            f"cannot run: --run executes only the 'fix' workflow "
            f"(got {selected!r}); pass --workflow fix"
        )
        return EXIT_CLI_ERROR

    scope = getattr(args, "scope", None)
    if not scope:
        print("cannot run: --run requires --scope so the edit surface is bounded")
        return EXIT_CLI_ERROR

    repo_root = _repo_root()
    # Normalize the (already-validated) scope to its REPO-RELATIVE
    # form so baseline hashing and violation matching compare like
    # with like — a `./pricing.py` or absolute spelling must never
    # read as an out-of-scope violation (codex D11 lane finding).
    resolved_scope = Path(scope).resolve()
    # `build_contract` already rejected any scope outside the repo via
    # `_validate_file_path`, so `relative_to` cannot raise here — no
    # second guard (it would be unreachable, and an unreachable guard
    # is worse than none: it reads as protection that never fires).
    scope_paths = [resolved_scope.relative_to(repo_root)]
    baseline = capture_baseline(repo_root, scope_paths)

    workflow_cls = get_workflow(selected)
    try:
        workflow = workflow_cls()
        result = asyncio.run(
            workflow.execute(
                goal=contract.goal,
                scope_paths=[str(resolved_scope)],
                done_conditions=contract.done_conditions,
            )
        )
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: uncaught workflow crash is the exit-2 branch of
        # the pinned contract; traceback to stderr for operators.
        traceback.print_exc()
        print(f"fix workflow crashed: {exc}")
        # A crash is exactly when the user most needs to know what was
        # left behind: assemble the receipt anyway (probes NOT run — the
        # run did not complete) so partial edits and scope violations are
        # still reported. Exit stays 2.
        partial = assemble_receipt(contract, baseline, scope_paths, [])
        print()
        print("partial receipt (workflow crashed — probes not run):")
        print(partial.render())
        return 2

    workflow_success = getattr(result, "success", None)
    print(f"\nworkflow finished (success={workflow_success}) — verifying independently...")

    probe_outcomes = run_probes(contract.probes, cwd=repo_root)
    receipt = assemble_receipt(contract, baseline, scope_paths, probe_outcomes)
    print()
    print(receipt.render())
    return receipt.exit_code()
