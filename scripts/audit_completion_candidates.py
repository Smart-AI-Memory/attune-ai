#!/usr/bin/env python3
"""Audit the completion-candidates detector against the live spec corpus.

Spec: ``docs/specs/ops-specs-completion-candidates/`` (T6).

Read-only audit. Runs the detector's five signal checks against every
spec under the configured roots and prints a per-spec table + a final
summary. NO writes — does not touch the dismiss store, does not flip
any status. Safe to re-run.

Purpose: before enabling ``--specs-candidates`` on a real workspace,
verify the detector produces zero false positives on the current
corpus. False negatives are acceptable; surface them in the table for
sanity but they don't block enablement.

Usage::

    python scripts/audit_completion_candidates.py
    python scripts/audit_completion_candidates.py --project-root /path/to/repo

Prerequisites:

- ``gh auth login`` — PR-merged + open-issue checks shell out to gh.
- ``attune-ai[ops]`` extras installed (fastapi/etc. are NOT needed
  for this script — only the detector module).

Expect ~30s on a ~30-spec corpus (one gh API call per referenced PR
per qualifying spec). The detector's in-memory cache is not used
here — we want fresh results.

Exit code 0 always (audit, not a gate).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from attune.ops.completion_candidates import (
    _check_last_edit_age,
    _check_no_open_issues,
    _check_referenced_prs_merged,
    _check_status_is_approved,
    _check_tasks_all_done,
    _extract_pr_refs,
    _preferred_status,
    _resolve_host_repo,
    clear_cache,
)
from attune.ops.config import build_config
from attune.ops.routes.specs import _list_specs_in_root, _resolved_roots

# Status priority order for "first failed check" attribution in skip
# reasons. Mirrors the detector's short-circuit ordering so the
# attribution matches what production would have done.
_CHECK_ORDER: tuple[str, ...] = ("status", "age", "tasks", "prs", "issues")


def audit_one_spec(spec: Any, repo: str | None) -> dict[str, Any]:
    """Run all 5 checks against one spec; never short-circuit.

    Returns a dict with per-check pass/fail and the first failed
    check's name (or "none" if all passed). The candidate is
    surfaced iff first_failed == "none".
    """
    results: dict[str, Any] = {
        "slug": spec.slug,
        "status": _preferred_status(spec) or "(none)",
        "checks": {},
        "evidence": [],
        "first_failed": None,
    }

    # 1. Status
    ok_status = _check_status_is_approved(spec)
    results["checks"]["status"] = ok_status

    # 2. Edit age
    ok_age, ev_age = _check_last_edit_age(spec)
    results["checks"]["age"] = ok_age
    if ev_age:
        results["evidence"].append(ev_age)

    # 3. Tasks
    spec_path = Path(spec.path)
    ok_tasks, ev_tasks = _check_tasks_all_done(spec_path)
    results["checks"]["tasks"] = ok_tasks
    if ev_tasks:
        results["evidence"].append(ev_tasks)

    # 4. PRs (gated on host repo discovery + presence of refs)
    pr_numbers = _extract_pr_refs(spec_path)
    if repo is None and pr_numbers:
        results["checks"]["prs"] = False
    elif repo is None:
        results["checks"]["prs"] = True
    else:
        ok_prs, ev_prs = _check_referenced_prs_merged(pr_numbers, repo)
        results["checks"]["prs"] = ok_prs
        if ev_prs:
            results["evidence"].append(ev_prs)

    # 5. Issues (gated on host repo)
    if repo is None:
        results["checks"]["issues"] = True
    else:
        ok_iss, ev_iss = _check_no_open_issues(spec.slug, repo)
        results["checks"]["issues"] = ok_iss
        if ev_iss:
            results["evidence"].append(ev_iss)

    # First-failed attribution (priority order).
    for check_name in _CHECK_ORDER:
        if not results["checks"].get(check_name, True):
            results["first_failed"] = check_name
            break

    return results


STATUS_COL_MAX = 18


def _truncate(text: str, max_len: int) -> str:
    """Truncate ``text`` to ``max_len`` chars, appending ``…`` if cut."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def render_table(rows: list[dict[str, Any]]) -> str:
    """Pretty-print the per-spec audit table.

    Status strings in the corpus often carry annotations like
    ``approved (2026-05-09) — Phase A`` which would overflow the
    column. Truncated to ``STATUS_COL_MAX`` for the table view;
    the full value is preserved in each row's ``status`` field for
    the candidates section.
    """
    if not rows:
        return "  (no specs found in any configured root)\n"
    header_cols = ("slug", "status", "age", "tasks", "prs", "issues", "cand?")
    widths = [
        max(20, max(len(str(r["slug"])) for r in rows)),
        STATUS_COL_MAX,
        5,
        5,
        5,
        6,
        6,
    ]

    def fmt(row_cols: tuple[str, ...]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(row_cols, widths, strict=False))

    lines = [fmt(header_cols), fmt(tuple("-" * w for w in widths))]
    for r in rows:
        is_cand = r["first_failed"] is None
        cells = (
            str(r["slug"]),
            _truncate(str(r["status"]), STATUS_COL_MAX),
            "✓" if r["checks"].get("age") else "✗",
            "✓" if r["checks"].get("tasks") else "✗",
            "✓" if r["checks"].get("prs") else "✗",
            "✓" if r["checks"].get("issues") else "✗",
            "YES" if is_cand else r["first_failed"] or "",
        )
        lines.append(fmt(cells))
    return "\n".join(lines) + "\n"


def render_summary(rows: list[dict[str, Any]]) -> str:
    """One-line-per-bucket skip summary."""
    total = len(rows)
    candidates = [r for r in rows if r["first_failed"] is None]
    skipped_buckets: dict[str, int] = dict.fromkeys(_CHECK_ORDER, 0)
    for r in rows:
        if r["first_failed"]:
            skipped_buckets[r["first_failed"]] += 1

    parts = [
        f"{total} spec{'' if total == 1 else 's'} scanned",
        f"{len(candidates)} candidate{'' if len(candidates) == 1 else 's'} surfaced",
    ]
    if total - len(candidates) > 0:
        parts.append(f"{total - len(candidates)} skipped:")
        for check, count in skipped_buckets.items():
            if count > 0:
                parts.append(f"  {count:>3} {check}")
    return "\n".join(parts) + "\n"


def render_candidates(rows: list[dict[str, Any]]) -> str:
    """Detailed view of the candidates that would be surfaced."""
    candidates = [r for r in rows if r["first_failed"] is None]
    if not candidates:
        return "\nNo candidates would be surfaced.\n"
    lines = ["", f"Candidates ({len(candidates)}):", ""]
    for r in candidates:
        lines.append(f"  {r['slug']}  (status: {r['status']})")
        for e in r["evidence"]:
            lines.append(f"    {e}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the completion-candidates detector against the live "
            "spec corpus. Read-only; safe to re-run."
        )
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root (default: cwd).",
    )
    parser.add_argument(
        "--specs-root",
        type=Path,
        action="append",
        default=None,
        metavar="DIR",
        help="Spec root (repeatable). Default: <project-root>/docs/specs/",
    )
    args = parser.parse_args(argv)

    config = build_config(
        project_root=args.project_root,
        specs_roots=tuple(args.specs_root) if args.specs_root else None,
    )
    roots = _resolved_roots(config)

    # Reset detector caches so we get fresh numbers on every audit run.
    clear_cache()

    print(f"Auditing {len(roots)} spec root{'' if len(roots) == 1 else 's'}:")
    for root in roots:
        print(f"  {root}")
    print()

    rows: list[dict[str, Any]] = []
    for root in roots:
        repo = _resolve_host_repo(root)
        for spec in _list_specs_in_root(root):
            rows.append(audit_one_spec(spec, repo))

    print(render_table(rows))
    print(render_summary(rows))
    print(render_candidates(rows))

    # Always exit 0 — this is an audit, not a gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
