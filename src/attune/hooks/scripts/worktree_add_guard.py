"""PreToolUse hook: refuse ``git worktree add`` from inside a worktree session.

Origin (retro 2026-09-06, R8): a session running in
``.claude/worktrees/<slug>/`` created a sibling worktree for a second
branch, and every Edit/Write into it was then refused by
``worktree_path_guard`` — the guard that exists precisely so a session
cannot write into a tree it is not running in. The new worktree had to
be removed and the branch switched in place. Two guards disagreed about
one act; this one settles it at the moment of creation, before the
~460 MB venv and the wasted round trip.

Rule: a session whose cwd (or ``CLAUDE_PROJECT_DIR``) is inside
``.claude/worktrees/`` does not spawn worktrees. Switch branches in
place — ``dirty_switch_guard`` keeps that safe — or start the new lane
from the main checkout, which is where worktrees come from.

What is NOT blocked, deliberately:

- ``git worktree list`` / ``remove`` / ``prune`` — reads and reaps.
- ``git worktree add`` from the main checkout.
- Anything when ``ATTUNE_ALLOW_NESTED_WORKTREE=1`` is set.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (stderr printed to user)

Metrics: appends one line to ~/.attune/enforcement-metrics.jsonl per
fire, like the sibling guards.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirty_switch_guard import git_invocations  # noqa: E402  (sibling hook script)

ENFORCEMENT_NAME = "worktree-add-guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"
ALLOW_ENV = "ATTUNE_ALLOW_NESTED_WORKTREE"
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"


def _log_metric(outcome: str, detail: str | None = None) -> None:
    """Append one best-effort record to the enforcement metrics log."""
    try:
        METRICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "enforcement": ENFORCEMENT_NAME,
            "outcome": outcome,
            "detail": detail,
        }
        with METRICS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        # INTENTIONAL: metrics are best-effort; never block on them.
        pass


def is_worktree_add(args: list[str]) -> bool:
    """True if the git arg-list is ``[global opts] worktree add ...``."""
    if "worktree" not in args:
        return False
    idx = args.index("worktree")
    return len(args) > idx + 1 and args[idx + 1] == "add"


def session_worktree_root(path: Path) -> Path | None:
    """The ``.claude/worktrees/<slug>`` root containing ``path``, or None."""
    parts = path.parts
    for i in range(len(parts) - 2):
        if parts[i] == ".claude" and parts[i + 1] == "worktrees":
            return Path(*parts[: i + 3])
    return None


def block_message(root: Path) -> str:
    """The refusal text: why, and the two ways forward."""
    return (
        f"[{ENFORCEMENT_NAME}] refusing `git worktree add`: this session runs "
        f"inside a worktree\n    {root}\n"
        "and a sibling worktree would be unwritable from here "
        "(worktree_path_guard refuses Edit/Write into any tree but this one).\n\n"
        "Switch branches in place instead — commit or stash first, then "
        "`git checkout -b <branch> origin/main` (dirty_switch_guard keeps that "
        "safe). Worktrees are created from the main checkout. "
        f"To disable for this session: {ALLOW_ENV}=1"
    )


def main(context: dict[str, Any]) -> int:
    """Block ``git worktree add`` inside a worktree session; 0 allow, 2 block."""
    if context.get("tool_name") != "Bash":
        return 0
    command = context.get("tool_input", {}).get("command", "")
    if not command or not any(is_worktree_add(args) for args in git_invocations(command)):
        return 0
    if os.environ.get(ALLOW_ENV) == "1":
        _log_metric("allowed", "escape hatch set")
        return 0

    root = session_worktree_root(Path.cwd())
    project_dir = os.environ.get(PROJECT_DIR_ENV, "")
    if root is None and project_dir:
        root = session_worktree_root(Path(project_dir))
    if root is None:
        _log_metric("allowed", "worktree add from a non-worktree checkout")
        return 0

    print(block_message(root), file=sys.stderr)
    _log_metric("fired", str(root))
    return 2


def _read_stdin_context() -> dict[str, Any]:
    """Parse the hook context from stdin; empty dict when unavailable."""
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        return {}
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


if __name__ == "__main__":
    from _bootstrap import ensure_utf8_stdio

    ensure_utf8_stdio()
    from _sdk_gate import exit_if_sdk_subprocess

    exit_if_sdk_subprocess()
    ctx = _read_stdin_context()
    if not ctx:
        sys.exit(0)
    try:
        sys.exit(main(ctx))
    except Exception as exc:  # noqa: BLE001
        # INTENTIONAL: a hook bug must never block real work.
        print(
            f"[{ENFORCEMENT_NAME}] hook error (allowing): {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(0)
