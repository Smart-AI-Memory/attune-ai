"""PreToolUse hook: refuse branch switches and hard resets that carry uncommitted work.

Catches the wrong-branch-state bug class. Uncommitted changes follow you
across a ``git checkout <branch>``, so work written for branch A lands on
branch B; and ``git reset --hard`` discards uncommitted work outright,
including work that merely rode along from another task.

Origin (2026-08-25, one session, three fires):

1. A chair-ruled fix was committed onto a sibling branch after an
   unreturned switch. ``git push origin <name>`` then exited 0 having
   pushed the *unchanged* ref, and the PR was armed for auto-merge on a
   head that did not contain the fix.
2. ``git reset --hard HEAD~1``, run as cleanup for a verification
   experiment, destroyed ~40 minutes of finished, uncommitted work on a
   different feature that was riding in the working tree.
3. ``git checkout <branch> 2>/dev/null`` failed *because* of that
   uncommitted work; the suppressed stderr turned a loud refusal into a
   silent no-op, and the next command read the wrong branch's file.

Meets the promotion criteria in
[`docs/specs/enforcement-vs-documentation/`](../../../../docs/specs/enforcement-vs-documentation/):
recurrence (3 fires), cost (~40 min of lost work plus a defective
auto-merge arm), and a mechanical check (``git status --porcelain``).

What is NOT blocked, deliberately:

- ``git checkout -b`` / ``git switch -c`` — creating a branch carries the
  changes to the new branch by design, which is the normal "I started in
  the wrong place" recovery.
- ``git checkout -- <path>`` — a path-scoped restore, not a branch switch.
- ``git checkout --force`` / ``git switch --force`` — the operator has
  stated the intent explicitly.
- Anything at all when the tree is clean.

Escape hatch: set ``ATTUNE_ALLOW_DIRTY_SWITCH=1`` for a session that
genuinely needs to move a dirty tree around.

Claude Code Protocol:
    stdin: JSON with tool_name and tool_input
    exit 0: allow tool call
    exit 2: block tool call (stderr printed to user)

Metrics: appends one line to ~/.attune/enforcement-metrics.jsonl per
fire so the periodic retirement review can compute hit rate,
false-alarm rate, and days-since-last-hit.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENFORCEMENT_NAME = "dirty-switch-guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"
ALLOW_ENV = "ATTUNE_ALLOW_DIRTY_SWITCH"

#: Flags that mean "make a new branch" — carrying changes is intended.
_NEW_BRANCH_FLAGS = {"-b", "-B", "-c", "-C"}

#: Flags that state the destructive intent explicitly.
_FORCE_FLAGS = {"-f", "--force", "--discard-changes"}

#: Shell operators that separate one command from the next.
_SEPARATORS = {"&&", "||", ";", "|", "&"}


def _log_metric(outcome: str, detail: str | None = None) -> None:
    """Append one record to the enforcement metrics log.

    ``outcome`` is one of ``"fired"`` (blocked), ``"allowed"`` (ran and
    permitted), or ``"unknown"`` (could not determine state; never
    blocks).
    """
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


def _is_git(argv: list[str]) -> bool:
    """True if ``argv`` invokes git (bare, or behind an env/path prefix)."""
    for token in argv:
        if "=" in token and not token.startswith("-"):
            continue  # leading VAR=value assignment
        if token in ("env", "command", "sudo"):
            continue
        return Path(token).name == "git"
    return False


def _git_args(argv: list[str]) -> list[str]:
    """Return the arguments following the ``git`` token itself."""
    for idx, token in enumerate(argv):
        if Path(token).name == "git":
            return argv[idx + 1 :]
    return []


def git_invocations(command: str) -> list[list[str]]:
    """Return the git arg-lists in ``command``, one per invocation.

    A single Bash call may chain several commands, so each is inspected
    separately — a dangerous one must not hide behind a harmless leading
    command.
    """
    # punctuation_chars is required, not cosmetic: plain shlex.split
    # leaves "hi;" as one token, so `echo hi; git reset --hard` would
    # parse as a single harmless invocation and slip past the guard.
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []  # unbalanced quotes: cannot parse, so cannot judge

    invocations: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SEPARATORS:
            if current:
                invocations.append(current)
            current = []
            continue
        current.append(token)
    if current:
        invocations.append(current)

    return [_git_args(inv) for inv in invocations if _is_git(inv)]


def is_branch_switch(args: list[str]) -> bool:
    """True if ``args`` is a branch-changing checkout/switch.

    False for new-branch creation, path-scoped restores, and explicit
    ``--force`` — each a deliberate act whose effect the operator has
    already stated.
    """
    if not args or args[0] not in ("checkout", "switch"):
        return False

    rest = args[1:]
    if any(flag in _NEW_BRANCH_FLAGS for flag in rest):
        return False
    if any(flag in _FORCE_FLAGS for flag in rest):
        return False
    if "--" in rest:
        return False  # path-scoped restore

    # A bare `git checkout` / `git switch` with no target changes nothing.
    return any(not token.startswith("-") for token in rest)


def is_hard_reset(args: list[str]) -> bool:
    """True if ``args`` is a ``git reset --hard`` against any target."""
    return bool(args) and args[0] == "reset" and "--hard" in args[1:]


def dirty_paths(cwd: Path | None = None) -> list[str] | None:
    """Return uncommitted paths, or None if git state cannot be read."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return [line[3:] for line in result.stdout.splitlines() if line.strip()]


def block_message(action: str, paths: list[str]) -> str:
    """The refusal text, naming the work at risk and the ways forward."""
    shown = paths[:8]
    listing = "\n".join(f"    {p}" for p in shown)
    if len(paths) > len(shown):
        listing += f"\n    … and {len(paths) - len(shown)} more"
    consequence = (
        "those changes would follow you onto the other branch"
        if action == "switch"
        else "those changes would be DESTROYED"
    )
    return (
        f"[{ENFORCEMENT_NAME}] refusing: {len(paths)} uncommitted change(s) "
        f"in the working tree, and {consequence}.\n"
        f"{listing}\n\n"
        "Commit them, stash them (git stash -u), or state the intent "
        "explicitly (--force for a switch). To disable for this session: "
        f"{ALLOW_ENV}=1"
    )


def main(context: dict[str, Any]) -> int:
    """Block dirty-tree branch switches and hard resets.

    Returns the exit code: ``0`` for allow, ``2`` for block.
    """
    if context.get("tool_name") != "Bash":
        return 0

    command = context.get("tool_input", {}).get("command", "")
    if not command:
        return 0

    if os.environ.get(ALLOW_ENV) == "1":
        _log_metric("allowed", "escape hatch set")
        return 0

    action = None
    for args in git_invocations(command):
        if is_branch_switch(args):
            action = "switch"
            break
        if is_hard_reset(args):
            action = "reset"
            break
    if action is None:
        return 0

    paths = dirty_paths()
    if paths is None:
        # Not a git tree, or git unreadable — degrade to allow.
        _log_metric("unknown", action)
        return 0
    if not paths:
        _log_metric("allowed", f"{action} on a clean tree")
        return 0

    print(block_message(action, paths), file=sys.stderr)
    _log_metric("fired", f"{action} with {len(paths)} dirty path(s)")
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
