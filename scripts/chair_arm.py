#!/usr/bin/env python3
"""Chair-arm paved path — label + arm-verify + SHA-bound receipt, one command.

Usage:
    python scripts/chair_arm.py <pr-number> [--dry-run] [--repo OWNER/NAME]

Operationalizes the D11d CHAIR-ARMS guard (feature-lead-governance,
adopted 2026-07-30). The chair's label application is the read-receipt,
bound to the head SHA the chair armed. This script makes the mechanical
part of that act safe and one-command; it does NOT replace the read —
run it only after reading the diff.

Steps:
 1. Read the PR: state, head SHA, diffstat, changed paths, merge state.
 2. Preflight blockers: open, not draft, base=main, same-repo, not
    DIRTY (a conflicted PR arms silently and never merges), and no
    ``.github/`` paths (the when-green carve-out would disarm + strip
    the label).
 3. Name any governance/enforcement surfaces in the diff, so the chair
    knows CHAIR-ARMS class applies (advisory — the read is the control).
 4. Apply the ``auto-merge-when-green`` label (the chair's act).
 5. VERIFY the arm: poll until GitHub native auto-merge is armed
    (``autoMergeRequest`` non-null) or the PR merges (the already-green
    plain-merge path). "Labeled" is a claim; an armed autoMergeRequest
    is the receipt. A stripped label (guard disarm) fails loudly.
 6. Post the SHA-bound read-receipt comment (``chair-armed at <sha>``)
    unless one already exists for that SHA. A later push moves the head
    and visibly invalidates the receipt.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

LABEL = "auto-merge-when-green"

# Advisory CHAIR-ARMS surface map: paths whose presence in a diff means
# the chair is arming a governance/enforcement change (D11b risk
# classes). Exact-match entries and prefix entries, checked in order.
GOVERNANCE_EXACT = {
    ".claude/CLAUDE.md",
    "CLAUDE.md",
    "AGENTS.md",
    "scripts/project_collaboration_contract.py",
    "docs/specs/cross-review/receipts.md",
    "src/attune/hooks/scripts/security_guard.py",
}
GOVERNANCE_PREFIXES = (
    ".claude/rules/",
    ".agents/",
    ".github/",
    "content/collaboration/",
    "tests/unit/gates/",
)

VERIFY_TIMEOUT_S = 120
VERIFY_INTERVAL_S = 6

VIEW_FIELDS = (
    "state,isDraft,baseRefName,headRefOid,mergeStateStatus,labels,"
    "autoMergeRequest,title,url,additions,deletions,files,isCrossRepository"
)


def run_gh(args: list[str], repo: str | None = None) -> str:
    """Run a gh command and return stdout (raises on failure)."""
    cmd = ["gh", *args]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def governance_paths(paths: list[str]) -> list[str]:
    """Return the subset of ``paths`` on CHAIR-ARMS-class surfaces."""
    hits = []
    for p in paths:
        if p in GOVERNANCE_EXACT or p.startswith(GOVERNANCE_PREFIXES):
            hits.append(p)
        elif p.startswith("docs/specs/") and p.endswith("/decisions.md"):
            hits.append(p)
    return hits


def find_blockers(view: dict, paths: list[str]) -> list[str]:
    """Return human-readable reasons this PR must not be armed."""
    blockers = []
    if view["state"] != "OPEN":
        blockers.append(f"PR state is {view['state']}, not OPEN")
    if view["isDraft"]:
        blockers.append("PR is a draft")
    if view["baseRefName"] != "main":
        blockers.append(f"base is {view['baseRefName']}, not main")
    if view["isCrossRepository"]:
        blockers.append("fork PR (head repo != base repo)")
    if view["mergeStateStatus"] == "DIRTY":
        blockers.append("merge state DIRTY (conflict) — arming would hang silently")
    github_paths = [p for p in paths if p.startswith(".github/")]
    if github_paths:
        blockers.append(
            ".github/ paths in diff (when-green carve-out disarms + strips "
            f"the label): {', '.join(github_paths)}"
        )
    return blockers


def evaluate_arm_state(view: dict) -> str:
    """Classify a polled PR view: armed | merged | label-stripped | pending."""
    if view["state"] == "MERGED":
        return "merged"
    # Label check BEFORE the arm check (codex round-2 finding): a
    # stripped label with a lingering autoMergeRequest (guard disarm
    # half-failed, or hand-unlabeled) must never count as armed — the
    # receipt asserts the label is the chair's act.
    if not any(lbl["name"] == LABEL for lbl in view.get("labels", [])):
        return "label-stripped"
    if view.get("autoMergeRequest"):
        return "armed"
    return "pending"


def receipt_body(sha: str, merged: bool = False) -> str:
    """The SHA-bound read-receipt comment body.

    Asserts the chair's endorsement via THIS run (the script is
    chair-run by definition), not the historical label event — the
    label may have pre-existed (codex round-3 wording finding).
    """
    suffix = " (merged immediately — already green)" if merged else ""
    return (
        f"chair-armed at {sha}{suffix}\n\n"
        "Read-receipt (D11d CHAIR-ARMS): the chair ran "
        f"scripts/chair_arm.py at head {sha} with `{LABEL}` in place. "
        "A subsequent push invalidates this receipt — disarm and "
        "re-arm after re-reading."
    )


def chair_login() -> str:
    """The authenticated gh login — the identity receipts belong to."""
    return run_gh(["api", "user", "--jq", ".login"]).strip()


def receipt_exists(pr: int, sha: str, repo: str | None, login: str) -> bool:
    """True if the CHAIR already posted a receipt comment for ``sha``.

    Dedup only among comments authored by ``login`` — an arbitrary
    commenter pre-seeding the receipt string must not suppress the
    real receipt (codex round-3 finding).
    """
    repo_arg = repo or "{owner}/{repo}"
    out = run_gh(
        [
            "api",
            "--paginate",
            f"repos/{repo_arg}/issues/{pr}/comments",
            "--jq",
            f'.[] | select(.user.login == "{login}") | .body',
        ]
    )
    return f"chair-armed at {sha}" in out


def fetch_view(pr: int, repo: str | None, fields: str = VIEW_FIELDS) -> dict:
    """Fetch the PR view JSON."""
    return json.loads(run_gh(["pr", "view", str(pr), "--json", fields], repo))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pr", type=int, help="PR number to chair-arm")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="preflight + report only; no label, no comment",
    )
    parser.add_argument("--repo", help="OWNER/NAME (default: current repo)")
    args = parser.parse_args(argv)

    view = fetch_view(args.pr, args.repo)
    paths = [f["path"] for f in view.get("files", [])]
    sha = view["headRefOid"]

    print(f"PR #{args.pr}: {view['title']}")
    print(f"  {view['url']}")
    print(f"  head {sha}")
    print(
        f"  {len(paths)} file(s), +{view['additions']}/-{view['deletions']}, "
        f"merge state {view['mergeStateStatus']}"
    )

    gov = governance_paths(paths)
    if gov:
        print("  CHAIR-ARMS class — governance/enforcement surfaces in diff:")
        for p in gov:
            print(f"    - {p}")
    else:
        print("  no governance-class surfaces detected (advisory check)")

    blockers = find_blockers(view, paths)
    if blockers:
        print("BLOCKED — not arming:")
        for b in blockers:
            print(f"  ✗ {b}")
        return 1

    already_armed = bool(view.get("autoMergeRequest"))
    has_label = any(lbl["name"] == LABEL for lbl in view.get("labels", []))
    if args.dry_run:
        state = "already armed" if already_armed else "would arm"
        has_receipt = receipt_exists(args.pr, sha, args.repo, chair_login())
        print(
            f"DRY RUN: {state}; receipt for {sha[:12]} " f"{'exists' if has_receipt else 'missing'}"
        )
        return 0

    # An arm that exists WITHOUT the label came from outside the
    # chair-arm flow (e.g. `gh pr merge --auto` directly). Posting the
    # receipt would launder that arm into a CHAIR-ARMS read-receipt
    # (codex finding, 2026-07-30) — refuse, name the actor, and let the
    # chair disarm + re-run if they intend to chair-arm.
    if already_armed and not has_label:
        req = view["autoMergeRequest"]
        by = (req.get("enabledBy") or {}).get("login", "unknown")
        print(
            f"  ✗ auto-merge already armed OUTSIDE the chair-arm flow "
            f"(enabled by {by} at {req.get('enabledAt', '?')}) with no "
            f"{LABEL} label. Receipt NOT posted. To chair-arm: disarm "
            f"(gh pr merge {args.pr} --disable-auto) and re-run."
        )
        return 2

    if not already_armed:
        if has_label:
            print(f"  label {LABEL} already present (pre-existing) — this run re-endorses the head")
        run_gh(["pr", "edit", str(args.pr), "--add-label", LABEL], args.repo)
        print(f"  label {LABEL} applied — verifying arm…")

    merged = False
    deadline = time.monotonic() + VERIFY_TIMEOUT_S
    while True:
        polled = fetch_view(args.pr, args.repo, "state,autoMergeRequest,labels,headRefOid")
        outcome = evaluate_arm_state(polled)
        if outcome == "armed":
            print("  ✓ native auto-merge ARMED (autoMergeRequest non-null)")
            break
        if outcome == "merged":
            print("  ✓ PR MERGED (already-green plain-merge path)")
            merged = True
            break
        if outcome == "label-stripped":
            print(
                "  ✗ label was STRIPPED — the when-green guard disarmed "
                "(out-of-class path or gate failure). Not armed."
            )
            return 2
        if time.monotonic() >= deadline:
            print(
                f"  ✗ verify timeout after {VERIFY_TIMEOUT_S}s — label is on "
                "but autoMergeRequest is still null. Check the "
                "auto-merge-safe workflow run, then re-run this script."
            )
            return 2
        time.sleep(VERIFY_INTERVAL_S)

    if polled["headRefOid"] != sha:
        # Fail CLOSED (codex round-3 finding): the arm must not stay
        # live on a head the chair has not read. Disarm + strip the
        # label, then hand back to the chair.
        if not merged:
            run_gh(["pr", "merge", str(args.pr), "--disable-auto"], args.repo)
            run_gh(
                ["pr", "edit", str(args.pr), "--remove-label", LABEL],
                args.repo,
            )
        print(
            f"  ⚠ head moved during verify ({sha[:12]} → "
            f"{polled['headRefOid'][:12]}) — DISARMED and unlabeled; "
            "receipt NOT posted. Re-read the new diff and re-run."
        )
        return 2

    if receipt_exists(args.pr, sha, args.repo, chair_login()):
        print(f"  receipt for {sha[:12]} already posted — done")
        return 0
    run_gh(
        ["pr", "comment", str(args.pr), "--body", receipt_body(sha, merged)],
        args.repo,
    )
    print(f"  ✓ read-receipt posted: chair-armed at {sha[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
