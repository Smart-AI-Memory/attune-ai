"""Reconcile receipt — release-audit-stage R3 step 1.

Before anyone sits, the stage proves the classes already marked CLOSED
are still green **on the commit being released**. That proof is a bound
receipt, not a glance at a dashboard.

The binding is the whole point (Codex#6): the receipt names an
**allowlisted workflow**, the **repository**, the **HEAD SHA**, and a
**successful conclusion**. A green run for an earlier commit does not
authorize — that is exactly how a regression introduced in the last
push slips through a reconcile that "looked green".

Reconcile red aborts the stage before any sitting (R3): seats should
never deliberate on a residual whose baseline is already broken.

Network access is injected, never assumed. ``runs_provider`` lets the
caller supply runs from anywhere; the default shells out to ``gh``.
That keeps the binding logic — the part with the security-relevant
refusals — testable without a network at all.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "ALLOWED_WORKFLOWS",
    "ReconcileError",
    "ReconcileReceipt",
    "gh_runs_provider",
    "reconcile",
]

#: Workflows whose success means "the gate suite ran". ``Tests`` carries
#: ``tests/unit/gates`` on this repo. Kept explicit rather than accepting
#: any green run: a docs-only workflow going green says nothing about a
#: CLOSED class still being closed.
ALLOWED_WORKFLOWS = ("Tests",)

#: The only conclusion that authorizes. ``skipped``/``cancelled`` are
#: NOT success — a cancelled required lane is the documented way a gate
#: silently stops guarding.
_GREEN = "success"


class ReconcileError(RuntimeError):
    """Reconcile failed — the stage aborts before the sitting (R3)."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


@dataclass(frozen=True)
class ReconcileReceipt:
    """One CI run, bound to one commit — the packet's §1."""

    run_id: str
    workflow: str
    repo: str
    head_sha: str
    conclusion: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "repo": self.repo,
            "head_sha": self.head_sha,
            "conclusion": self.conclusion,
        }


def gh_runs_provider(repo: str, head_sha: str) -> list[dict[str, Any]]:
    """Default provider: workflow runs for ``head_sha`` via the ``gh`` CLI.

    Returns an empty list when ``gh`` is unavailable or errors — the
    caller then fails closed with ``no-run`` rather than this function
    inventing a green result.
    """
    try:
        result = subprocess.run(  # noqa: S603 — fixed argv, no shell
            [
                "gh",
                "run",
                "list",
                "--repo",
                repo,
                "--commit",
                head_sha,
                "--json",
                "databaseId,name,conclusion,status,headSha",
                "--limit",
                "50",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout or "[]")
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def _runs_for_sha(runs: list[dict[str, Any]], head_sha: str) -> list[dict[str, Any]]:
    """Keep only runs for ``head_sha``. The binding is ours to enforce."""
    for_this_sha = [r for r in runs if str(r.get("headSha", head_sha)) == head_sha]
    if for_this_sha:
        return for_this_sha
    others = sorted({str(r.get("headSha", ""))[:9] for r in runs if r.get("headSha")})
    raise ReconcileError(
        "sha-mismatch",
        f"runs exist for {others} but none for {head_sha[:9]} — "
        "a green run for an earlier commit does not authorize",
    )


def _allowlisted_runs(
    runs: list[dict[str, Any]], allowed_workflows: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Keep only runs whose success means the gate suite actually ran."""
    allowed = [r for r in runs if str(r.get("name", "")) in allowed_workflows]
    if allowed:
        return allowed
    seen = sorted({str(r.get("name", "?")) for r in runs})
    raise ReconcileError(
        "workflow-not-allowlisted",
        f"no run from {list(allowed_workflows)}; saw {seen}",
    )


def _first_green(runs: list[dict[str, Any]], head_sha: str) -> dict[str, Any]:
    """The authorizing run, or a refusal naming why none qualifies."""
    green = [r for r in runs if str(r.get("conclusion", "")) == _GREEN]
    if green:
        return green[0]
    in_flight = [r for r in runs if str(r.get("status", "")) != "completed"]
    if in_flight:
        raise ReconcileError(
            "still-running",
            f"{len(in_flight)} allowlisted run(s) not yet complete for {head_sha[:9]}",
        )
    conclusions = sorted({str(r.get("conclusion", "?")) for r in runs})
    raise ReconcileError(
        "not-green",
        f"allowlisted run(s) concluded {conclusions}; only {_GREEN!r} authorizes",
    )


def reconcile(
    repo: str,
    head_sha: str,
    *,
    runs_provider: Callable[[str, str], list[dict[str, Any]]] | None = None,
    allowed_workflows: tuple[str, ...] = ALLOWED_WORKFLOWS,
) -> ReconcileReceipt:
    """Prove an allowlisted workflow succeeded for exactly ``head_sha``.

    A short pipeline of refusals: each helper either narrows the candidate
    runs or raises with the reason. Every path fails CLOSED — an
    unprovable reconcile is never treated as green.

    Args:
        repo: ``owner/name`` of the repository being released.
        head_sha: The full commit SHA being audited.
        runs_provider: Returns candidate runs; defaults to :func:`gh_runs_provider`.
        allowed_workflows: Workflow names whose success counts.

    Returns:
        A :class:`ReconcileReceipt` naming the run that authorizes.

    Raises:
        ReconcileError: Bad SHA, no run, a run only for another commit,
            none from an allowlisted workflow, none complete, or none
            successful.

    """
    if not head_sha or len(head_sha) < 40:
        raise ReconcileError("bad-head-sha", f"{head_sha!r} is not a full 40-char SHA")

    runs = (runs_provider or gh_runs_provider)(repo, head_sha)
    if not runs:
        raise ReconcileError("no-run", f"no workflow run found for {head_sha[:9]} in {repo}")

    candidates = _allowlisted_runs(_runs_for_sha(runs, head_sha), allowed_workflows)
    run = _first_green(candidates, head_sha)

    return ReconcileReceipt(
        run_id=str(run.get("databaseId", "")),
        workflow=str(run.get("name", "")),
        repo=repo,
        head_sha=head_sha,
        conclusion=_GREEN,
    )
