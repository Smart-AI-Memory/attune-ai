#!/usr/bin/env python3
"""Changelog-entry gate — a PR touching shipped code must DECLARE its
user-visibility, either by writing a CHANGELOG entry or by labelling the
PR ``no-changelog``.

Why this exists (2026-08-28): 10 of the last 14 ``src/``-touching PRs
merged with no changelog entry, and the omission stays invisible until
someone cuts a release. ``release.yml`` only EXTRACTS notes at tag time,
so it faithfully publishes whatever is there — a thin section reads as
"a small release" rather than "a broken record". v16.1.0 shipped three
changes (#2336, #2338, #2346) whose entries had to be reconstructed by
hand during release prep.

Why a DECLARATION and not an inference: keying the rule on the PR title
was tried and rejected. The title is an author declaration rather than a
property of the diff, and ``refactor:`` covers both user-visible config
renames (#2321, #2319) and invisible internals (#2314, #2303) — so a
title rule is imprecise in both directions and silently gameable. This
gate instead asks the author to decide at the one moment they actually
know, and records that decision as a label which, unlike an allowlist
entry, dies with the PR instead of becoming permanent review debt.

Exit 0 = satisfied, exit 1 = the PR must add an entry or the label.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

#: Path prefixes whose changes reach users through the published wheel.
#: ``tests/`` and ``docs/`` are deliberately absent — they ship nothing.
SHIPPED_PREFIXES: tuple[str, ...] = ("src/", "attune_redis/")

#: The file an entry must land in.
CHANGELOG = "CHANGELOG.md"

#: Applying this label IS the declaration that the change is not
#: user-visible. Per-PR and self-expiring by design.
OPT_OUT_LABEL = "no-changelog"


def touches_shipped_code(paths: list[str]) -> bool:
    """Return True when any path reaches users through the wheel."""
    return any(path.startswith(SHIPPED_PREFIXES) for path in paths)


def is_satisfied(paths: list[str], labels: list[str]) -> bool:
    """Return True when the PR has declared its user-visibility.

    Satisfied three ways: it ships nothing, it edits the changelog, or it
    carries the opt-out label.
    """
    if not touches_shipped_code(paths):
        return True
    if CHANGELOG in paths:
        return True
    return OPT_OUT_LABEL in labels


def changed_paths(base_ref: str) -> list[str]:
    """Paths changed against the merge base, or ``["src/"]`` on failure.

    Fail-CLOSED: a diff we cannot compute is treated as touching shipped
    code, so an infrastructure error asks for a declaration rather than
    waving the PR through. This mirrors tests.yml's "run more, never
    fewer required signals" fallback and contract principle 7 (a failed
    gatekeeper fails the gate). The opt-out label stays available, so a
    misfire costs one click rather than a blocked branch.
    """
    try:
        subprocess.run(
            ["git", "fetch", "--no-tags", "--quiet", "origin", base_ref],
            check=False,
            capture_output=True,
        )
        result = subprocess.run(
            ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"::warning::could not compute the diff ({exc}) - failing closed")
        return ["src/"]
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    """Run the gate against the current PR; return a process exit code."""
    parser = argparse.ArgumentParser(description="Changelog-entry gate")
    parser.add_argument("--base-ref", default=os.environ.get("BASE_REF", ""))
    parser.add_argument(
        "--labels",
        default=os.environ.get("PR_LABELS", ""),
        help="comma-separated PR labels",
    )
    args = parser.parse_args()

    if not args.base_ref:
        print("no base ref (not a pull request) - gate does not apply")
        return 0

    paths = changed_paths(args.base_ref)
    labels = [item.strip() for item in args.labels.split(",") if item.strip()]

    print("changed files:")
    for path in paths:
        print(f"  {path}")
    print(f"labels: {labels or '(none)'}")

    if is_satisfied(paths, labels):
        print("OK: user-visibility declared (entry present, label set, or nothing shipped)")
        return 0

    shipped = "\n  ".join(p for p in paths if p.startswith(SHIPPED_PREFIXES))
    print(
        f"::error::This PR changes shipped code but neither edits {CHANGELOG} "
        f"nor carries the '{OPT_OUT_LABEL}' label. "
        "Add an entry under [Unreleased] describing what a USER sees, or "
        f"apply '{OPT_OUT_LABEL}' if the change is internal-only (refactors, "
        "test-only fixes, import moves). "
        f"Shipped paths in this PR: {shipped}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
