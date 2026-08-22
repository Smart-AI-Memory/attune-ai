"""The release-audit stage — release-audit-stage R3, steps 0-5.

Six steps, in order, inside the release path (D1)::

    0  baseline    merge-base diff vs the last release tag
    1  reconcile   CLOSED gates green in CI, bound to THIS head SHA
    2  diff sweep  rules over the changed package surface (D10)
    3  residual    the schema-v1 packet
    4  sitting     one round, three seats, no rebuttal
    5  chair       rules per item; manifest written

Two orderings are load-bearing rather than incidental:

* **Reconcile red aborts before any sitting** (R3). Seats must never
  deliberate on a residual whose baseline is already broken — the
  deliberation would be about the wrong tree.
* **The packet is built before the sitting and hashed**, so the manifest
  records which residual was actually sat on. A packet rebuilt after the
  fact would not hash the same.

``run_stage`` stops at step 4 and hands back everything the chair needs.
It does NOT rule: dispositions are the chair's, and a tool that picked
them would make the manifest a record of itself.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from attune.classes.baseline import Baseline, BaselineError, resolve_baseline
from attune.classes.packet import Packet, PacketOverCap, build_packet
from attune.classes.reconcile import ReconcileError, ReconcileReceipt, reconcile
from attune.classes.register import derive_register
from attune.classes.scan import scan_paths
from attune.classes.sitting import Sitting, hold_sitting

__all__ = ["StageAborted", "StageResult", "run_stage", "main"]


class StageAborted(RuntimeError):
    """The stage stopped before completing. Carries the step and reason."""

    def __init__(self, step: str, reason: str, detail: str = "") -> None:
        self.step = step
        self.reason = reason
        self.detail = detail
        super().__init__(f"step {step}: {reason}{f' — {detail}' if detail else ''}")


@dataclass(frozen=True)
class StageResult:
    """Everything the chair needs to rule, and nothing pre-ruled."""

    baseline: Baseline
    reconcile_receipt: ReconcileReceipt | None
    packet: Packet
    sitting: Sitting | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline": {
                "tag_range": self.baseline.tag_range,
                "baseline_sha": self.baseline.baseline_sha,
                "head_sha": self.baseline.head_sha,
                "source": self.baseline.source,
            },
            "reconcile": self.reconcile_receipt.as_dict() if self.reconcile_receipt else None,
            "packet": self.packet.as_dict(),
            "packet_hash": self.packet.packet_hash,
            "sitting": self.sitting.as_dict() if self.sitting else None,
            "blocking_by_default": [i.item_id for i in self.packet.blocking],
        }


def run_stage(
    repo_root: Path,
    repo_slug: str,
    *,
    baseline_override: str | None = None,
    skip_reconcile: bool = False,
    hold: bool = True,
    invoke_seat: Callable[[Sequence[str], str], tuple[int, str]] | None = None,
    runs_provider: Callable[[str, str], list[dict[str, Any]]] | None = None,
) -> StageResult:
    """Run steps 0-4 and return the chair's inputs.

    Args:
        repo_root: Repository being released.
        repo_slug: ``owner/name`` for the reconcile receipt.
        baseline_override: ``--baseline`` ref; skips the tag lookup.
        skip_reconcile: Dry-run escape for a commit with no CI run. The
            resulting packet records ``1_reconcile: null`` so the gap is
            visible rather than implied-green.
        hold: Run the sitting. False builds the packet and stops.
        invoke_seat: Injected seat runner (testing / offline).
        runs_provider: Injected CI reader (testing / offline).

    Returns:
        A :class:`StageResult`. Dispositions are NOT chosen here.

    Raises:
        StageAborted: A step failed in a way that must stop the release —
            an unresolvable baseline, a red or absent reconcile, or a
            residual that exceeds schema v1 and needs the chair to split.

    """
    try:
        baseline = resolve_baseline(repo_root, override=baseline_override)
    except BaselineError as exc:
        raise StageAborted("0-baseline", exc.reason, exc.detail) from exc

    receipt: ReconcileReceipt | None = None
    if not skip_reconcile:
        try:
            receipt = reconcile(repo_slug, baseline.head_sha, runs_provider=runs_provider)
        except ReconcileError as exc:
            # R3: red at step 1 aborts BEFORE any sitting.
            raise StageAborted("1-reconcile", exc.reason, exc.detail) from exc

    # D10: the sweep is package-scoped; the packet reports what it skipped.
    sweep = scan_paths([Path(p) for p in baseline.to_sweep], repo_root=repo_root)
    register = derive_register(repo_root=repo_root)

    try:
        packet = build_packet(
            baseline,
            sweep,
            register,
            repo_root=repo_root,
            reconcile=receipt.as_dict() if receipt else None,
        )
    except PacketOverCap as exc:
        raise StageAborted(
            "3-residual", "over-cap", json.dumps(exc.diagnostics["breaches"])
        ) from exc

    sitting = hold_sitting(packet, invoke=invoke_seat) if hold else None
    return StageResult(baseline=baseline, reconcile_receipt=receipt, packet=packet, sitting=sitting)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m attune.classes.stage``.

    Exit codes are the contract: 0 ready for the chair, 1 aborted, and
    2 reserved for an over-cap residual (R4) so a caller can tell "split
    the release" apart from every other failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--repo", default="Smart-AI-Memory/attune-ai")
    parser.add_argument("--baseline", default=None, help="explicit ref to diff from")
    parser.add_argument("--skip-reconcile", action="store_true")
    parser.add_argument("--no-sitting", action="store_true", help="build the packet only")
    args = parser.parse_args(argv)

    try:
        result = run_stage(
            args.repo_root,
            args.repo,
            baseline_override=args.baseline,
            skip_reconcile=args.skip_reconcile,
            hold=not args.no_sitting,
        )
    except StageAborted as exc:
        print(json.dumps({"aborted_at": exc.step, "reason": exc.reason, "detail": exc.detail}))
        return 2 if exc.reason == "over-cap" else 1

    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
