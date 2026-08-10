#!/usr/bin/env python3
"""Interactive verdict loop over curated memories (memory-status-integrity P2 task 5).

Presents the top-risk curated memories one at a time and records a
one-keystroke human verdict per D6 #3:

- ``k`` (keep) — the claim is still true: sets ``verified: <today>`` in
  the file's frontmatter and appends a digest-bound record to the
  corpus's append-only verdict log.
- ``w`` (wrong) — TOMBSTONES via the log, never deletes: the file (and
  every ``MEMORY.md`` pointer and ``[[link]]`` into it) stays intact,
  the audit renders it ``tombstoned``, and its derived Redis node is
  invalidated immediately.
- ``s`` (sharper) — edit + verify in one motion: opens ``$EDITOR``,
  then records the verdict against the POST-edit digest and sets
  ``verified: <today>``.
- Enter — skip; ``q`` — quit.

The queue is CAPPED (default 3 per triage, D6's binding constraint:
the scarce resource is one human's attention). Already-tombstoned
memories are not re-queued. Exits 0 always — a review session is not
a gate.

NOTE (task 3): the canonical linter for ``~/.claude`` corpora must be
amended to accept ``verified:`` before running ``keep`` there — until
then use this loop on corpora without that linter (e.g.
``~/.attune/memory``), or land the linter amendment first.

Usage:
    python scripts/review_curated_memory.py
    python scripts/review_curated_memory.py --root ~/.attune/memory --limit 3
    python scripts/review_curated_memory.py --dry-run   # queue only, no prompts
"""

from __future__ import annotations

import argparse
import os
import subprocess  # noqa: S404 — $EDITOR launch, list argv, shell=False
import sys
from datetime import date
from pathlib import Path


def default_roots() -> list[Path]:
    """The curated corpora present on this machine (mirrors the audit CLI)."""
    home = Path.home()
    candidates = [home / ".attune" / "memory", home / ".claude" / "memory"]
    projects = home / ".claude" / "projects"
    if projects.is_dir():
        candidates.extend(sorted(projects.glob("*/memory")))
    return [path for path in candidates if path.is_dir()]


def build_queue(report, limit: int, ref_reasons=None) -> list[tuple[object, str, int, list[str]]]:
    """Top-``limit`` reviewable rows: ``(memory, basis, age_days, reasons)``.

    Tombstoned memories are excluded — they already carry a verdict, and
    re-queueing them would spend the capped attention budget on files
    the loop has nothing left to ask about.

    P2 task 7 (ruling D7): when ``ref_reasons`` is supplied, project-type
    memories whose explicit typed refs trigger (``pr:`` closed, ``file:``
    gone, …) FLOAT to the queue front — promote-only atop the age
    baseline, checked for at most ``MAX_CHECKED_MEMORIES`` candidates.
    Rows are ``(memory, basis, age_days, reasons)``.
    """
    candidates = []
    for (mem, _score), (_stem, basis, days) in zip(report.ranked, report.age_bases, strict=False):
        if basis == "tombstoned":
            continue
        candidates.append((mem, basis, days))

    jumped, aged = [], []
    if ref_reasons is not None:
        from attune.memory.ref_triggers import MAX_CHECKED_MEMORIES

        checked = 0
        for row in candidates:
            mem = row[0]
            reasons: list[str] = []
            if mem.mem_type == "project" and checked < MAX_CHECKED_MEMORIES:
                checked += 1
                reasons = ref_reasons(mem)
            (jumped if reasons else aged).append((*row, reasons))
    else:
        aged = [(*row, []) for row in candidates]

    return (jumped + aged)[:limit]


def _resolve_who(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        out = subprocess.run(  # noqa: S603 — fixed argv, shell=False
            ["git", "config", "user.name"], capture_output=True, text=True, timeout=5
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.environ.get("USER", "unknown")


def _corpus_root_for(mem, roots: list[Path]) -> Path:
    """The scanned root this memory lives under (its verdict-log home)."""
    for root in roots:
        if root in mem.path.parents:
            return root
    return mem.path.parent


def _review_one(
    mem, basis: str, days: int, root: Path, who: str, reasons: list[str] | None = None
) -> str:
    """Prompt for and apply one verdict. Returns the action taken."""
    from attune.memory.curated_audit import load_memory
    from attune.memory.verdict_log import (
        VerdictRecord,
        append_verdict,
        propagate_verdict,
        set_verified,
    )

    print(f"\n[{mem.mem_type or '?'}] {mem.stem}  ({basis}, {days}d)")
    for reason in reasons or []:
        print(f"  ⚑ ref trigger: {reason}")
    print(f"  {mem.description or '(no description)'}")
    print(f"  {mem.path}")
    answer = input("  [k]eep / [w]rong / [s]harper / Enter=skip / [q]uit > ").strip().lower()

    if answer == "q":
        return "quit"
    if answer == "k":
        # Log record FIRST, stamp second (codex D11 finding): if the append
        # fails, the safe leftover is a record-less UNSTAMPED file, never a
        # `verified:` stamp with no audit record behind it.
        append_verdict(root, VerdictRecord.create(mem.stem, "keep", mem.digest, who))
        set_verified(mem.path, date.today())
        propagate_verdict(mem.stem)
        return "keep"
    if answer == "w":
        append_verdict(root, VerdictRecord.create(mem.stem, "wrong", mem.digest, who))
        invalidated = propagate_verdict(mem.stem)
        print(f"  tombstoned (redis node {'invalidated' if invalidated else 'not present'})")
        return "wrong"
    if answer == "s":
        # A failed or missing editor means NO edit happened — recording a
        # `sharper` verdict anyway would verify content the reviewer never
        # sharpened (codex D11 finding). Degrade to skip.
        editor = os.environ.get("EDITOR", "vi")
        try:
            result = subprocess.run([editor, str(mem.path)], check=False)  # noqa: S603
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"  editor failed to launch ({exc}) — skipped, no verdict recorded")
            return "skip"
        if result.returncode != 0:
            print(f"  editor exited {result.returncode} — skipped, no verdict recorded")
            return "skip"
        edited = load_memory(mem.path)
        append_verdict(root, VerdictRecord.create(mem.stem, "sharper", edited.digest, who))
        set_verified(mem.path, date.today())
        propagate_verdict(mem.stem)
        return "sharper"
    return "skip"


def main(argv: list[str] | None = None) -> int:
    """Run one bounded triage. Always returns 0 — a review is not a gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", type=Path, dest="roots")
    parser.add_argument("--limit", type=int, default=3, help="Queue cap per triage (D6).")
    parser.add_argument("--who", help="Reviewer identity; defaults to git user.name.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the queue and exit — no prompts, no writes."
    )
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    src = repo / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from attune.memory.curated_audit import sweep
    from attune.memory.serve_telemetry import serve_counts

    roots = args.roots or default_roots()
    if not roots:
        print("No curated memory corpora found.")
        return 0

    report = sweep(roots, serves=serve_counts() or None)
    from functools import partial

    from attune.memory.ref_triggers import queue_jump_reasons

    queue = build_queue(
        report, args.limit, ref_reasons=partial(queue_jump_reasons, repo_root=Path.cwd())
    )
    if not queue:
        print("Nothing to review — queue is empty.")
        return 0

    if args.dry_run or not sys.stdin.isatty():
        print(f"Review queue (top {args.limit}, tombstoned excluded):")
        for mem, basis, days, reasons in queue:
            jump = f"  ⚑ {'; '.join(reasons)}" if reasons else ""
            print(f"  [{mem.mem_type or '?'}] {mem.stem}  ({basis}, {days}d){jump}")
        if not args.dry_run:
            print("stdin is not a TTY — run interactively to record verdicts.")
        return 0

    who = _resolve_who(args.who)
    counts: dict[str, int] = {}
    for mem, basis, days, reasons in queue:
        root = _corpus_root_for(mem, [Path(r) for r in report.roots])
        if reasons:
            counts["queue-jumped"] = counts.get("queue-jumped", 0) + 1
        try:
            action = _review_one(mem, basis, days, root, who, reasons=reasons)
        except (OSError, ValueError) as exc:
            # One unwritable file/log must not abort the triage or break
            # the always-exit-zero contract; the item simply records no
            # verdict this round.
            print(f"  ERROR on {mem.stem}: {exc} — no verdict recorded")
            counts["error"] = counts.get("error", 0) + 1
            continue
        if action == "quit":
            break
        counts[action] = counts.get(action, 0) + 1

    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "no verdicts"
    print(f"\nTriage done: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
