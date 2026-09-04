"""PreToolUse hook: refuse ``git push`` while HEAD is detached.

The bug class (2026-09-04, retro item 4): a concurrent session ran
``git checkout --detach`` in this worktree between two of my commits (the
corpus itself recommends that to free a branch). The next commit landed on
the detached HEAD, and ``git push`` then printed ``Everything up-to-date``
— a true statement about the BRANCH ref, which had not moved — while the
remote was one commit behind. The PR was reviewed on stale content until
``git ls-remote`` was compared with ``git rev-parse HEAD`` by hand.

The check is mechanical: ``git symbolic-ref -q HEAD`` fails exactly when
HEAD is detached. When it does, the push is refused with the recovery
that re-attaches by fast-forward.

What is NOT blocked, deliberately:
- Any command that is not a ``git push``.
- Pushes with an explicit ``HEAD:<ref>`` refspec — the operator is
  pushing the detached commit on purpose.
- Pushing tags (``--tags`` / ``refs/tags/...``) — unaffected by HEAD.
- Anything when git state cannot be read (fail open — a hook bug must
  never block work).

Escape hatch: ``ATTUNE_ALLOW_DETACHED_PUSH=1``.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (stderr printed to user)

Metrics: one line per fire in ~/.attune/enforcement-metrics.jsonl, the
same ledger the other guards use.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENFORCEMENT_NAME = "detached-head-push-guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"
ALLOW_ENV = "ATTUNE_ALLOW_DETACHED_PUSH"

_HERE = Path(__file__).resolve().parent


def _load_git_invocations():
    """Reuse the sibling guard's shell-aware git tokenizer."""
    spec = importlib.util.spec_from_file_location("_dsg", _HERE / "dirty_switch_guard.py")
    if spec is None or spec.loader is None:  # pragma: no cover - packaging fault
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.git_invocations


def _log_metric(outcome: str, detail: str | None = None) -> None:
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


def is_branch_push(args: list[str]) -> bool:
    """True if ``args`` is a ``git push`` whose target depends on HEAD.

    Explicit ``HEAD:<ref>`` refspecs and tag pushes are the operator
    stating intent that does not need an attached HEAD.
    """
    if not args or args[0] != "push":
        return False
    rest = args[1:]
    if "--tags" in rest:
        return False
    for token in rest:
        if token.startswith("HEAD:") or token.startswith("refs/tags/"):
            return False
    return True


def detached_head(cwd: Path | None = None) -> bool | None:
    """True if HEAD is detached, False if on a branch, None if unreadable."""
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "-q", "HEAD"],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 0:
        return False
    if result.returncode == 1 and not result.stderr.strip():
        return True  # detached: symbolic-ref -q exits 1 silently
    return None  # not a git repo, or some other failure


def block_message(cwd: Path | None = None) -> str:
    head = "?"
    try:
        head = (
            subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            ).stdout.strip()
            or "?"
        )
    except (OSError, subprocess.SubprocessError):
        pass
    return (
        f"BLOCKED: HEAD is detached at {head} — a `git push` here pushes the BRANCH ref, "
        "not this commit, and reports 'Everything up-to-date' while the remote stays behind.\n"
        "  Something moved HEAD off the branch (another session's `checkout --detach`, "
        "a rebase, a hook). Re-attach by fast-forward, then push:\n"
        "    git branch --show-current            # prints nothing when detached\n"
        "    git merge-base --is-ancestor <branch> HEAD && git checkout -B <branch> HEAD\n"
        "  Or push the commit explicitly: git push origin HEAD:<branch>\n"
        f"  Escape hatch for a deliberate detached push: {ALLOW_ENV}=1"
    )


def main(ctx: dict[str, Any]) -> int:
    if os.environ.get(ALLOW_ENV) == "1":
        return 0
    if ctx.get("tool_name") != "Bash":
        return 0
    command = (ctx.get("tool_input") or {}).get("command", "")
    if "push" not in command:
        return 0
    git_invocations = _load_git_invocations()
    if git_invocations is None:
        return 0
    if not any(is_branch_push(args) for args in git_invocations(command)):
        return 0
    state = detached_head()
    if state is None:
        _log_metric("unknown", "git state unreadable")
        return 0
    if not state:
        _log_metric("allowed")
        return 0
    _log_metric("fired", command[:200])
    print(block_message(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (OSError, ValueError):
        payload = {}
    raise SystemExit(main(payload))
