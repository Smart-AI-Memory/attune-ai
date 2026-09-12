"""PreToolUse hook: refuse a ``git push`` of shipped code with no CHANGELOG entry.

The bug class (retro 2026-09-11, item 6): four ``src/``-touching PRs in
one evening each cost a red round-trip on the CI ``changelog-entry`` gate
(``.github/scripts/changelog_gate.py``) because the CHANGELOG entry was
written AFTER the PR was opened. The gate is right to fail them; this
guard asks the same question at push time, in the agent session, where
the fix is one more commit instead of a CI cycle.

The check is mechanical and mirrors the CI gate. The commits about to be
pushed are ``git merge-base origin/main HEAD`` .. ``HEAD``; if any path
changed in that range starts with a shipped prefix and ``CHANGELOG.md``
is not among the changed paths, the push is refused.

What is NOT blocked, deliberately:
- Any command that is not a ``git push``.
- A range that touches nothing under the shipped prefixes (docs, tests,
  tooling, CI).
- A range that already changes ``CHANGELOG.md``.
- Anything when ``origin/main`` is unknown, HEAD has no commits, or git
  cannot be read (fail open, one stderr line — a hook bug must never
  block work). The range is read from the session's cwd; a ``-C <dir>``
  on the push is not followed.

Escape hatch: ``ATTUNE_ALLOW_NO_CHANGELOG=1`` for an internal-only
change. Apply the ``no-changelog`` label after opening the PR — that
label is the declaration the CI gate accepts.

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

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dirty_switch_guard import git_invocations  # noqa: E402  (sibling hook script)

ENFORCEMENT_NAME = "changelog-entry-guard"
METRICS_LOG = Path.home() / ".attune" / "enforcement-metrics.jsonl"
ALLOW_ENV = "ATTUNE_ALLOW_NO_CHANGELOG"

#: Mirrors ``SHIPPED_PREFIXES`` in ``.github/scripts/changelog_gate.py``,
#: the CI ``changelog-entry`` gate this guard front-runs. A drift test in
#: tests/unit/hooks/test_changelog_entry_guard.py pins the two equal.
SHIPPED_PREFIXES: tuple[str, ...] = ("src/", "attune_redis/")

#: The file an entry must land in, and the label that declares "none needed".
CHANGELOG = "CHANGELOG.md"
OPT_OUT_LABEL = "no-changelog"

#: Git global options that consume the next token as their value.
_GLOBAL_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}


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


def is_push(args: list[str]) -> bool:
    """True if the git arg-list is ``[global opts] push ...``.

    Global options (``-C <dir>``, ``-c k=v``, ``--no-pager`` ...) are
    skipped so the subcommand is matched by position — ``git commit -m
    push`` is not a push.
    """
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in _GLOBAL_OPTS_WITH_VALUE else 1
    return args[i : i + 1] == ["push"]


def _git(args: list[str], cwd: Path | None = None) -> str | None:
    """Stdout of a git command, or None when it fails for any reason."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def pushed_paths(cwd: Path | None = None) -> list[str] | None:
    """Paths changed from the ``origin/main`` merge base to HEAD, or None if unknown."""
    base = _git(["merge-base", "origin/main", "HEAD"], cwd)
    if base is None:
        return None
    diff = _git(["diff", "--name-only", base.strip(), "HEAD"], cwd)
    if diff is None:
        return None
    return [line for line in diff.splitlines() if line]


def block_message(shipped: list[str]) -> str:
    """The refusal text: the shipped paths, and the two ways forward."""
    shown = shipped[:8]
    listing = "\n".join(f"    {p}" for p in shown)
    if len(shipped) > len(shown):
        listing += f"\n    ... and {len(shipped) - len(shown)} more"
    return (
        f"[{ENFORCEMENT_NAME}] refusing: this push ships code with no "
        f"{CHANGELOG} change in the pushed range, so the CI `changelog-entry` "
        "gate would fail the PR.\n"
        f"  Shipped paths:\n{listing}\n\n"
        "  Two exits:\n"
        f"    1. Add an entry under `## [Unreleased]` in {CHANGELOG}, inside the "
        "EXISTING `### Added` / `### Changed` / `### Fixed` section for its "
        "kind (never a second one), commit, and push again.\n"
        f"    2. Internal-only change: {ALLOW_ENV}=1 <push command> for this "
        f"push, then apply the `{OPT_OUT_LABEL}` label after opening the PR."
    )


def main(context: dict[str, Any]) -> int:
    """Block a push of shipped code with no CHANGELOG entry; 0 allow, 2 block."""
    if context.get("tool_name") != "Bash":
        return 0
    command = (context.get("tool_input") or {}).get("command", "")
    if not command or not any(is_push(args) for args in git_invocations(command)):
        return 0
    if os.environ.get(ALLOW_ENV) == "1":
        _log_metric("allowed", "escape hatch set")
        return 0

    paths = pushed_paths()
    if paths is None:
        print(
            f"[{ENFORCEMENT_NAME}] cannot read the push range "
            "(no origin/main, no commits, or not a git tree) — skipping",
            file=sys.stderr,
        )
        _log_metric("unknown", "push range unreadable")
        return 0
    shipped = [p for p in paths if p.startswith(SHIPPED_PREFIXES)]
    if not shipped or CHANGELOG in paths:
        _log_metric("allowed", f"{len(shipped)} shipped path(s)")
        return 0

    print(block_message(shipped), file=sys.stderr)
    _log_metric("fired", f"{len(shipped)} shipped path(s), no {CHANGELOG}")
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
