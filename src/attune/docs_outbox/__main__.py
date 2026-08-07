# Licensed under the Apache License, Version 2.0
# Copyright 2026 Smart AI Memory, LLC
"""CLI for the docs outbox: write, list, status, sweep, apply.

``python -m attune.docs_outbox write --kind lesson --slug my-slug --file body.md``
``python -m attune.docs_outbox sweep``   (launchd EOD job + on-demand)
``python -m attune.docs_outbox apply``   (the approve session, post-chip)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from attune.docs_outbox.store import list_artifacts, outbox_status, write_artifact
from attune.docs_outbox.sweep import apply_sweep, run_sweep


def _cmd_write(args: argparse.Namespace) -> int:
    body = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        path = write_artifact(args.kind, args.slug, body, target=args.target)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


def _cmd_list(_args: argparse.Namespace) -> int:
    for artifact in list_artifacts():
        issues = f"  [{'; '.join(artifact.issues)}]" if artifact.issues else ""
        print(f"{artifact.path.name}  -> {artifact.target}{issues}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    status = outbox_status()
    if args.json:
        print(
            json.dumps(
                {"count": status.count, "oldest_days": status.oldest_days, "stale": status.stale}
            )
        )
    elif status.count == 0:
        print("outbox empty")
    else:
        stale = "  STALE — sweep overdue" if status.stale else ""
        print(f"{status.count} pending, oldest {status.oldest_days}d{stale}")
    return 0


def _repo_root(raw: str) -> Path | None:
    """Resolve --repo-root, refusing anything that isn't a git repo.

    Guards the biggest foot-gun: ``apply`` run from the wrong cwd would
    happily create ``~/.claude/lessons.md`` and archive every artifact
    as swept, leaving the real repo empty-handed.
    """
    root = Path(raw).resolve()
    if not (root / ".git").exists():
        print(f"error: {root} is not a git repository — pass --repo-root", file=sys.stderr)
        return None
    return root


def _cmd_sweep(args: argparse.Namespace) -> int:
    root = _repo_root(args.repo_root)
    if root is None:
        return 1
    result = run_sweep(root)
    if not args.quiet:
        print(result.digest)
    if result.status and result.status.stale:
        print("warning: outbox is stale (2+ days) — approve the digest", file=sys.stderr)
    return 0


def _cmd_apply(args: argparse.Namespace) -> int:
    repo_root = _repo_root(args.repo_root)
    if repo_root is None:
        return 1
    result = run_sweep(repo_root)
    changed = apply_sweep(repo_root, result=result)
    for path in changed:
        print(path)
    for name, issues in result.lint_issues.items():
        print(f"skipped {name}: {'; '.join(issues)}", file=sys.stderr)
    for name, reason in result.apply_failures.items():
        print(f"FAILED {name}: {reason} (left pending)", file=sys.stderr)
    if result.apply_failures:
        return 1
    if not changed and not result.lint_issues:
        print("outbox empty — nothing applied")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch one subcommand; return its exit code."""
    parser = argparse.ArgumentParser(prog="python -m attune.docs_outbox", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    write_p = sub.add_parser("write", help="outbox one artifact")
    write_p.add_argument("--kind", required=True)
    write_p.add_argument("--slug", required=True)
    write_p.add_argument("--target", default=None, help="repo-relative target path")
    write_p.add_argument("--file", default=None, help="body file (default: stdin)")
    write_p.set_defaults(func=_cmd_write)

    list_p = sub.add_parser("list", help="list pending artifacts")
    list_p.set_defaults(func=_cmd_list)

    status_p = sub.add_parser("status", help="pending count + stale flag")
    status_p.add_argument("--json", action="store_true")
    status_p.set_defaults(func=_cmd_status)

    sweep_p = sub.add_parser("sweep", help="compose the digest (no writes to the repo)")
    sweep_p.add_argument("--repo-root", default=".")
    sweep_p.add_argument("--quiet", action="store_true")
    sweep_p.set_defaults(func=_cmd_sweep)

    apply_p = sub.add_parser("apply", help="apply clean artifacts into the repo")
    apply_p.add_argument("--repo-root", default=".")
    apply_p.set_defaults(func=_cmd_apply)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
